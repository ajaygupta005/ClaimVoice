# Data Sources & Ingestion

Every dataset used by ClaimVoice. All are **free**, **US-public**, and
**verified live as of May 2026**.

## Public sources

| Data | Source | Script |
|---|---|---|
| NPI provider registry | CMS NPPES V2 (download.cms.gov/nppes) | `ingest/npi_ingest.py` |
| 2026 Exchange Plan PUFs | cms.gov/marketplace/resources/data/public-use-files | `ingest/plan_puf_ingest.py` |
| SBC PDFs | HealthCare.gov public plan listings | `ingest/sbc_download.py` |
| MRF in-network rates (Schema 2.0) | Payer Transparency-in-Coverage MRFs | `ingest/mrf_parser.py` |
| Part D formulary (CY 2026) | cms.gov/medicare/coverage/prescription-drug-coverage/formulary-guidance | `ingest/formulary_ingest.py` |
| Care Compare hospital quality | data.cms.gov public API | `ingest/care_compare_sync.py` |
| ICD-10 / HCPCS codes | CMS public downloads | `ingest/icd_hcpcs_ingest.py` |

## Synthetic (privacy)

| Data | Generator |
|---|---|
| Insurance cards (100) | `ingest/synthetic_cards.py` (Flux + Faker) |
| X12 271 eligibility responses | Hand-crafted in `stubs/eligibility_271/` |
