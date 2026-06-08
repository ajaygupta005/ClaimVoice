#!/usr/bin/env python3
"""
Lightweight NPPES V2 downloader (no Postgres required for initial download).
Downloads CMS NPPES V2 May 2026 dump (~1GB), unzips, and parses a sample.
"""

import csv
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def download_nppes_sample():
    """Download and extract NPPES V2, show sample."""
    
    url = "https://download.cms.gov/nppes/npi_data.zip"
    extract_dir = Path("data/raw/nppes_v2_may2026")
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    csv_file = extract_dir / "npidata_20260507.csv"
    
    if csv_file.exists():
        print(f"✅ NPPES CSV already downloaded: {csv_file}")
        print(f"   File size: {csv_file.stat().st_size / 1e6:.1f} MB")
        show_sample(csv_file)
        return
    
    print(f"📥 Downloading NPPES V2 from {url}")
    print(f"   This is a large file (~1GB). Please wait...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "nppes.zip"
        
        try:
            urllib.request.urlretrieve(
                url,
                zip_path,
                reporthook=lambda block, read, total: print_progress(read, total)
            )
            print(f"\n✅ Downloaded to {zip_path}")
            
            print(f"📦 Extracting ZIP...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)
            
            csv_files = list(extract_dir.glob("npidata_*.csv"))
            if csv_files:
                csv_file = csv_files[0]
                print(f"✅ Extracted: {csv_file}")
                print(f"   File size: {csv_file.stat().st_size / 1e6:.1f} MB")
                show_sample(csv_file)
            else:
                print("❌ No CSV found in extracted files")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise


def print_progress(block_num, block_size, total_size):
    """Simple download progress indicator."""
    downloaded = min(block_num * block_size, total_size)
    pct = 100 * downloaded / total_size if total_size > 0 else 0
    mb = downloaded / 1e6
    total_mb = total_size / 1e6
    
    if block_num % 100 == 0:
        print(f"   {pct:5.1f}% ({mb:7.1f} / {total_mb:7.1f} MB)", end="\r")


def show_sample(csv_file: Path):
    """Show first few records."""
    print(f"\n📊 Sample records from {csv_file.name}:")
    print("-" * 80)
    
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            npi = row.get("NPI", "?")
            name = row.get("Provider First Name", "") + " " + row.get("Provider Last Name (Legal Name)", "")
            specialty = row.get("Provider Primary Taxonomy Code", "?")
            state = row.get("First Line Business Practice Location Address State Code", "?")
            
            print(f"  {i+1}. NPI={npi} | {name.strip()} | {specialty} | {state}")
    
    print("-" * 80)
    print(f"✅ NPPES data is ready for WS-3 (Document AI) and WS-4 (Eligibility)")
    print(f"\nNext steps:")
    print(f"  1. Set up Postgres database")
    print(f"  2. Run Alembic migrations: alembic upgrade head")
    print(f"  3. Load data into database: python data/ingest/npi_ingest.py")


if __name__ == "__main__":
    download_nppes_sample()
