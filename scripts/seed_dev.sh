#!/usr/bin/env bash
set -euo pipefail
just data.ingest
python services/providers/scripts/seed_demo.py
python services/eligibility/scripts/seed_demo_member.py
