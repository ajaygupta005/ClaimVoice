#!/bin/bash
# Quick setup for WS-1 Data Engineering

set -e

echo "🚀 ClaimVoice Data Engineering Setup"
echo "====================================="

# Check Python
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python: $python_version"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --quiet \
  hydra-core \
  psycopg[binary] \
  sqlalchemy \
  alembic

# Check environment
if [ -z "$DATABASE_URL" ]; then
  echo "⚠️  DATABASE_URL not set. Using default: postgresql://localhost/claimvoice"
  export DATABASE_URL="postgresql://localhost/claimvoice"
fi

echo "🗄️  Database: $DATABASE_URL"

# Run Alembic migrations
echo ""
echo "📝 Running Alembic migrations..."
cd services/eligibility
alembic upgrade head
cd - > /dev/null

# Verify schema
echo ""
echo "✅ Schema verification..."
psql "$DATABASE_URL" -c "\dt" | head -20

echo ""
echo "🎯 Setup complete! Ready to run ingestions."
echo ""
echo "Next steps:"
echo "  python data/ingest/npi_ingest.py              # Download NPPES V2"
echo "  python data/ingest/plan_puf_ingest.py         # Load Plan PUFs"
echo "  python data/ingest/sbc_download.py            # Download SBC PDFs"
echo "  python data/ingest/mrf_parser.py              # Parse MRF JSON"
