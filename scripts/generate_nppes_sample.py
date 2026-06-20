#!/usr/bin/env python3
"""
Generate synthetic NPPES sample data for local testing.
Creates realistic NPI records without downloading the full 1GB+ file.

Usage:
    python scripts/generate_nppes_sample.py  # Creates data/raw/nppes_sample.csv
"""

import csv
from pathlib import Path
from random import choice, randint, uniform


# Realistic payor-related taxonomies
TAXONOMIES = [
    "207Q00000X",  # Family Medicine
    "2084P0805X",  # Psychiatry
    "207R00000X",  # Internal Medicine
    "208000000X",  # Allopathic & Osteopathic Physicians
    "2084A0401X",  # Emergency Medicine
    "207RP1001X",  # Pediatrics
]

FIRST_NAMES = [
    "Michael", "James", "David", "Robert", "Sarah", "Jessica", "Jennifer",
    "Lisa", "Maria", "Patricia", "John", "William", "Richard"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez"
]

CITIES_NY_METRO = [
    ("New York", "NY", 40.7128, -74.0060),
    ("Brooklyn", "NY", 40.6501, -73.9496),
    ("Manhattan", "NY", 40.7831, -73.9712),
    ("Queens", "NY", 40.7282, -73.7949),
    ("Newark", "NJ", 40.7357, -74.1724),
    ("Jersey City", "NJ", 40.7178, -74.0431),
    ("Bronx", "NY", 40.8448, -73.8648),
]

CREDENTIALS = ["MD", "DO", "NP", "PA-C", "MD, PhD"]


def generate_npi() -> str:
    """Generate a valid-looking NPI (10 digits)."""
    return str(randint(1000000000, 9999999999))


def generate_phone() -> str:
    """Generate a US phone number."""
    return f"({randint(201, 973)}) {randint(200, 999)}-{randint(1000, 9999)}"


def generate_zip() -> str:
    """Generate a valid NY metro ZIP code."""
    zips = ["10001", "10002", "11201", "07101", "07102", "07103", "10451", "10453"]
    return choice(zips)


def create_sample_nppes(num_records: int = 500) -> Path:
    """Generate a synthetic NPPES CSV sample."""
    
    output_file = Path("data/raw/nppes_sample.csv")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {num_records} synthetic NPPES records...")
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "NPI",
            "Entity Type Code",
            "Provider First Name",
            "Provider Last Name (Legal Name)",
            "Provider Organization Name (Legal Business Name)",
            "Provider Credential Text (Legal Auth. forGrad. Med. Edu.)",
            "Provider Primary Taxonomy Code",
            "Provider Primary Taxonomy Switch",
            "First Line Business Practice Location Address",
            "First Line Business Practice Location Address City Name",
            "First Line Business Practice Location Address State Code",
            "First Line Business Practice Location Address State Name",
            "First Line Business Practice Location Address Postal Code",
            "First Line Business Practice Location Address Latitude",
            "First Line Business Practice Location Address Longitude",
            "First Line Business Practice Location Address Telephone Number",
            "NPI Deactivation Reason Code",
        ])
        writer.writeheader()
        
        for i in range(num_records):
            # 70% individuals, 30% organizations
            if i % 10 < 7:
                entity_type = "1"  # Individual
                first_name = choice(FIRST_NAMES)
                last_name = choice(LAST_NAMES)
                org_name = ""
                credential = choice(CREDENTIALS)
            else:
                entity_type = "2"  # Organization
                first_name = ""
                last_name = ""
                org_name = f"{choice(LAST_NAMES)} Medical Group"
                credential = ""
            
            # Random location in NY metro
            city, state_code, base_lat, base_lon = choice(CITIES_NY_METRO)
            latitude = base_lat + uniform(-0.05, 0.05)  # ~5 km radius
            longitude = base_lon + uniform(-0.05, 0.05)
            
            writer.writerow({
                "NPI": generate_npi(),
                "Entity Type Code": entity_type,
                "Provider First Name": first_name,
                "Provider Last Name (Legal Name)": last_name,
                "Provider Organization Name (Legal Business Name)": org_name,
                "Provider Credential Text (Legal Auth. forGrad. Med. Edu.)": credential,
                "Provider Primary Taxonomy Code": choice(TAXONOMIES),
                "Provider Primary Taxonomy Switch": "Y",
                "First Line Business Practice Location Address": f"{randint(100, 9999)} Main Street",
                "First Line Business Practice Location Address City Name": city,
                "First Line Business Practice Location Address State Code": state_code,
                "First Line Business Practice Location Address State Name": "NY" if state_code == "NY" else "NJ",
                "First Line Business Practice Location Address Postal Code": generate_zip(),
                "First Line Business Practice Location Address Latitude": f"{latitude:.6f}",
                "First Line Business Practice Location Address Longitude": f"{longitude:.6f}",
                "First Line Business Practice Location Address Telephone Number": generate_phone(),
                "NPI Deactivation Reason Code": "",  # All active
            })
    
    print(f"Created {num_records} synthetic records: {output_file}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    print("\nSample records:")
    print("-" * 100)
    
    with open(output_file, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            name = (f"{row['Provider First Name']} {row['Provider Last Name (Legal Name)']}" 
                   if row['Provider First Name'] 
                   else row['Provider Organization Name (Legal Business Name)'])
            spec = row['Provider Primary Taxonomy Code']
            lat = row['First Line Business Practice Location Address Latitude']
            lon = row['First Line Business Practice Location Address Longitude']
            
            print(f"  {i+1}. NPI={row['NPI']} | {name.strip()} | {spec} | ({lat}, {lon})")
    
    print("-" * 100)
    return output_file


def show_download_instructions():
    """Show how to download real NPPES data."""
    print("\n" + "=" * 100)
    print("To download the REAL NPPES V2 data from CMS:")
    print("=" * 100)
    print("""
1. Visit: https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/NPI/index.html

2. Download the ZIP file: "NPPES NPI Registry File Updates (Monthly)"
   - URL: https://download.cms.gov/nppes/npi_data.zip
   - Size: ~1.5 GB (compressed)
   - Updated: Monthly

3. Extract the ZIP to: data/raw/nppes_v2_may2026/

4. Load into Postgres:
   python data/ingest/npi_ingest.py

Note: Some networks block direct downloads from CMS. If so:
  - Try from a different network
  - Use wget or curl with user-agent headers
  - Download via browser and move the file manually
    """)
    print("=" * 100)


if __name__ == "__main__":
    create_sample_nppes(num_records=500)
    show_download_instructions()
