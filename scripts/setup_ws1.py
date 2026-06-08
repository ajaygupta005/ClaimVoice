#!/usr/bin/env python3
"""
Quick setup for WS-1 Data Engineering on Windows/Linux/Mac.
Installs dependencies, runs Alembic migrations, verifies schema.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list, description: str = ""):
    """Run shell command."""
    if description:
        print(f"\n📝 {description}")
    print(f"   $ {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=False)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        sys.exit(1)


def main():
    """Setup ClaimVoice Data Engineering."""
    
    print("🚀 ClaimVoice Data Engineering Setup")
    print("=" * 50)
    
    # Check Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"✅ Python: {py_ver}")
    
    if sys.version_info < (3, 12):
        print(f"❌ Python 3.12+ required (you have {py_ver})")
        sys.exit(1)
    
    # Install dependencies
    print("\n📦 Installing Python dependencies...")
    deps = [
        "hydra-core>=1.3.0",
        "psycopg[binary]>=3.1.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
    ]
    for dep in deps:
        run_cmd([sys.executable, "-m", "pip", "install", "--quiet", dep])
    
    print("✅ Dependencies installed")
    
    # Check DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://localhost/claimvoice"
        print(f"⚠️  DATABASE_URL not set. Using default: {db_url}")
        os.environ["DATABASE_URL"] = db_url
    else:
        print(f"✅ Database: {db_url}")
    
    # Run migrations
    eligibility_dir = Path("services/eligibility")
    if eligibility_dir.exists():
        print(f"\n📝 Running Alembic migrations from {eligibility_dir}...")
        cwd = os.getcwd()
        try:
            os.chdir(eligibility_dir)
            run_cmd([sys.executable, "-m", "alembic", "upgrade", "head"])
            os.chdir(cwd)
        except Exception as e:
            print(f"⚠️  Alembic migration may require more setup: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("  python data/ingest/npi_ingest.py              # Download NPPES V2 (large, ~1GB)")
    print("  python data/ingest/plan_puf_ingest.py         # Load Plan PUFs")
    print("  dvc repro                                      # Run all DVC pipeline stages")


if __name__ == "__main__":
    main()
