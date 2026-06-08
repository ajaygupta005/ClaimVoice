#!/usr/bin/env python3
"""
NPI Ingestion: Download CMS NPPES V2 dump, parse, filter by geography, load into PostGIS.

Downloads monthly from https://download.cms.gov/nppes/npi_data.zip
Parses CSV, filters by state + lat/lon bounds (NY metro by default)
Loads into `providers` table with spatial indexing.

Usage:
    python data/ingest/npi_ingest.py  # Uses data/ingest/configs/npi_ingest.yaml
    python data/ingest/npi_ingest.py npi.geo_filter.states=[NY,PA]  # Override
"""

import csv
import hashlib
import logging
import os
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg
from hydra import compose, initialize_config_dir
from hydra.core.config_store import ConfigStore
from omegaconf import DictConfig, OmegaConf


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def download_nppes(download_url: str, extract_dir: str) -> Path:
    """Download and extract NPPES V2 CSV dump."""
    extract_path = Path(extract_dir)
    extract_path.mkdir(parents=True, exist_ok=True)

    csv_file = extract_path / "npidata_20260507.csv"
    if csv_file.exists():
        logger.info(f"NPPES CSV already exists at {csv_file}, skipping download")
        return csv_file

    logger.info(f"Downloading NPPES V2 from {download_url}")
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "nppes.zip"
        try:
            urllib.request.urlretrieve(download_url, zip_path)
            logger.info(f"Downloaded to {zip_path}")
        except Exception as e:
            logger.error(f"Failed to download: {e}")
            raise

        logger.info(f"Extracting ZIP to {extract_path}")
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_path)
        except Exception as e:
            logger.error(f"Failed to extract ZIP: {e}")
            raise

    # Find the CSV file
    csv_files = list(extract_path.glob("npidata_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No npidata_*.csv found in {extract_path}")

    csv_file = csv_files[0]
    logger.info(f"Found NPI CSV: {csv_file}")
    return csv_file


def parse_npi_record(row: dict, config: DictConfig) -> Optional[dict]:
    """Parse a single NPI CSV row. Return None if filtered out."""
    
    # Filter: active only
    if not config.npi.include_deactivated:
        if row.get("NPI Deactivation Reason Code") and row["NPI Deactivation Reason Code"].strip():
            return None
    
    # Filter: entity type
    entity_type = row.get("Entity Type Code", "").strip()
    if entity_type and int(entity_type) not in config.npi.entity_types:
        return None
    
    # Extract lat/lon
    latitude_str = row.get("First Line Business Practice Location Address Latitude", "").strip()
    longitude_str = row.get("First Line Business Practice Location Address Longitude", "").strip()
    
    if not latitude_str or not longitude_str:
        return None
    
    try:
        latitude = float(latitude_str)
        longitude = float(longitude_str)
    except ValueError:
        return None
    
    # Filter: geography (lat/lon bounds)
    geo = config.npi.geo_filter
    if not (geo.min_latitude <= latitude <= geo.max_latitude and
            geo.min_longitude <= longitude <= geo.max_longitude):
        return None
    
    # Filter: state
    state = row.get("First Line Business Practice Location Address State Name", "").strip()
    if state and state not in geo.states:
        return None
    
    # Build provider record
    npi = row.get("NPI", "").strip()
    if not npi:
        return None
    
    entity_type_code = row.get("Entity Type Code", "").strip()
    
    if entity_type_code == "1":  # Individual
        first_name = row.get("Provider First Name", "").strip()
        last_name = row.get("Provider Last Name (Legal Name)", "").strip()
        organization_name = None
    else:  # Organization
        first_name = None
        last_name = None
        organization_name = row.get("Provider Organization Name (Legal Business Name)", "").strip()
    
    credential = row.get("Provider Credential Text (Legal Auth. forGrad. Med. Edu.)", "").strip()
    taxonomy_code = row.get("Provider Primary Taxonomy Switch", "").strip()
    taxonomy_desc = row.get("Provider Primary Taxonomy Code", "").strip()
    
    address_1 = row.get("First Line Business Practice Location Address", "").strip()
    city = row.get("First Line Business Practice Location Address City Name", "").strip()
    state_code = row.get("First Line Business Practice Location Address State Code", "").strip()
    zip_code = row.get("First Line Business Practice Location Address Postal Code", "").strip()
    phone = row.get("First Line Business Practice Location Address Telephone Number", "").strip()
    
    return {
        "npi": npi,
        "first_name": first_name if first_name else None,
        "last_name": last_name if last_name else None,
        "organization_name": organization_name,
        "credential_text": credential if credential else None,
        "taxonomy_code": taxonomy_code if taxonomy_code else None,
        "taxonomy_description": taxonomy_desc if taxonomy_desc else None,
        "practice_location_address_line_1": address_1 if address_1 else None,
        "practice_location_city": city if city else None,
        "practice_location_state": state_code if state_code else None,
        "practice_location_zip": zip_code if zip_code else None,
        "practice_location_phone": phone if phone else None,
        "latitude": latitude,
        "longitude": longitude,
        "accepting_new_patients": None,  # Not in NPPES; populated by Care Compare later
        "quality_rating": None,
        "hospital_name": None,
        "specialty_codes": [taxonomy_code] if taxonomy_code else None,
        "audit_source": "nppes_v2_may2026",
    }


def load_providers_to_db(csv_file: Path, config: DictConfig) -> None:
    """Stream-parse NPI CSV and bulk-insert into Postgres."""
    
    conn_string = config.npi.database.connection_string
    batch_size = config.npi.database.batch_size
    
    logger.info(f"Connecting to {conn_string}")
    with psycopg.connect(conn_string, autocommit=True) as conn:
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'providers')"
        )
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            logger.error("Table 'providers' does not exist. Run Alembic migrations first.")
            raise RuntimeError("Schema not initialized")
        
        batch = []
        total_parsed = 0
        total_loaded = 0
        
        logger.info(f"Parsing {csv_file}")
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1=header)
                try:
                    provider = parse_npi_record(row, config)
                    if provider:
                        batch.append(provider)
                        total_parsed += 1
                except Exception as e:
                    logger.warning(f"Row {row_num}: {e}")
                    continue
                
                # Batch insert every N records
                if len(batch) >= batch_size:
                    total_loaded += _insert_batch(cursor, batch, conn)
                    batch = []
                    logger.info(f"Inserted {total_loaded} providers so far...")
                
                if (row_num - 2) % 100000 == 0 and row_num > 2:
                    logger.debug(f"Parsed {row_num - 2} rows")
        
        # Final batch
        if batch:
            total_loaded += _insert_batch(cursor, batch, conn)
        
        logger.info(f"✅ Ingestion complete: {total_parsed} parsed, {total_loaded} loaded")


def _insert_batch(cursor, batch: list, conn) -> int:
    """Insert a batch of provider records."""
    if not batch:
        return 0
    
    # Build multi-row INSERT
    placeholders = ", ".join(
        [
            "("
            + ", ".join(["%s"] * 17)
            + ")"
        ]
        * len(batch)
    )
    
    values = []
    for p in batch:
        values.extend([
            p["npi"],
            p["first_name"],
            p["last_name"],
            p["organization_name"],
            p["credential_text"],
            p["taxonomy_code"],
            p["taxonomy_description"],
            p["practice_location_address_line_1"],
            p["practice_location_city"],
            p["practice_location_state"],
            p["practice_location_zip"],
            p["practice_location_phone"],
            f"POINT({p['longitude']} {p['latitude']})",  # PostGIS WKT
            p["accepting_new_patients"],
            p["quality_rating"],
            p["hospital_name"],
            p["audit_source"],
        ])
    
    # ON CONFLICT DO NOTHING: skip duplicate NPIs
    sql = f"""
        INSERT INTO providers (
            npi, first_name, last_name, organization_name, credential_text,
            taxonomy_code, taxonomy_description,
            practice_location_address_line_1, practice_location_city,
            practice_location_state, practice_location_zip, practice_location_phone,
            location, accepting_new_patients, quality_rating, hospital_name,
            audit_source
        )
        VALUES {placeholders}
        ON CONFLICT (npi) DO NOTHING
    """
    
    try:
        cursor.execute(sql, values)
        inserted = cursor.rowcount
        
        # Log to audit trail
        for p in batch:
            data_hash = hashlib.sha256(str(p).encode()).hexdigest()
            audit_sql = """
                INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(audit_sql, (
                "providers",
                p["npi"],
                p["audit_source"],
                data_hash,
                "https://download.cms.gov/nppes/NPI_Files.html"
            ))
        
        return inserted
    except Exception as e:
        logger.error(f"Batch insert failed: {e}")
        raise


def main():
    """Main entry point."""
    
    # Initialize Hydra config
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="npi_ingest", overrides=sys.argv[1:])
    
    logger.info(f"Config: {OmegaConf.to_yaml(cfg)}")
    
    # Download NPPES
    csv_file = download_nppes(cfg.npi.download_url, cfg.npi.extract_dir)
    
    # Load to Postgres
    load_providers_to_db(csv_file, cfg)


if __name__ == "__main__":
    main()

