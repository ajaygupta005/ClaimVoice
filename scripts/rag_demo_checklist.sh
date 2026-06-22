#!/usr/bin/env bash
# Component 72 — SBC RAG demo readiness smoke test.
#
# Validates every layer from DB to API before a demo:
#   1. pgvector extension present
#   2. sbc_chunks table + row count
#   3. Demo plan UUID discoverable
#   4. GET /api/v1/rag/readiness → ragStatus = "ready"
#   5. POST /api/v1/sbc/retrieve → at least 1 chunk for a known question
#   6. GET /api/v1/runtime/status → rag_status = "ready"
#
# Usage:
#   bash scripts/rag_demo_checklist.sh
#   bash scripts/rag_demo_checklist.sh --plan-name "Aetna Silver 3500"
#   bash scripts/rag_demo_checklist.sh --eligibility-url http://localhost:8002 \
#                                      --voice-agent-url http://localhost:8004
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed (details printed above)
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────

ELIGIBILITY_URL="${ELIGIBILITY_URL:-http://localhost:8002}"
VOICE_AGENT_URL="${VOICE_AGENT_URL:-http://localhost:8004}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-claimvoice-postgres-1}"
DB_NAME="${POSTGRES_DB:-claimvoice}"
DB_USER="${POSTGRES_USER:-postgres}"
PLAN_NAME="${PLAN_NAME:-ClaimVoice Demo PPO}"
RAG_QUERY="Is MRI of the brain covered?"
TOP_K=3

# ── Colour helpers ────────────────────────────────────────────────────────────

_supports_colour() {
    [[ -t 1 ]] && command -v tput &>/dev/null && tput colors &>/dev/null && [[ $(tput colors) -ge 8 ]]
}

if _supports_colour; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
    CYAN='\033[1;36m'; RESET='\033[0m'; BOLD='\033[1m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; RESET=''; BOLD=''
fi

ok()   { echo -e "${GREEN}  ✔${RESET}  $*"; }
fail() { echo -e "${RED}  ✖${RESET}  $*"; FAILURES=$((FAILURES + 1)); }
warn() { echo -e "${YELLOW}  ⚠${RESET}  $*"; }
hdr()  { echo -e "\n${CYAN}${BOLD}$*${RESET}"; }
info() { echo -e "     $*"; }

FAILURES=0

# ── CLI args ──────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --eligibility-url)   ELIGIBILITY_URL="$2";   shift 2 ;;
        --voice-agent-url)   VOICE_AGENT_URL="$2";   shift 2 ;;
        --plan-name)         PLAN_NAME="$2";          shift 2 ;;
        --rag-query)         RAG_QUERY="$2";          shift 2 ;;
        --pg-container)      POSTGRES_CONTAINER="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────

_psql() {
    docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "$1" 2>/dev/null
}

_curl_json() {
    # $1 = method (GET or POST), $2 = url, optional $3 = JSON body
    local method="$1" url="$2" body="${3:-}"
    if [[ -n "$body" ]]; then
        curl -sf -X "$method" "$url" \
             -H "Content-Type: application/json" \
             -d "$body" 2>/dev/null
    else
        curl -sf -X "$method" "$url" 2>/dev/null
    fi
}

_jq_or_python() {
    # Extract a JSON field using jq if available, otherwise python
    local json="$1" key="$2"
    if command -v jq &>/dev/null; then
        echo "$json" | jq -r ".$key // empty" 2>/dev/null
    else
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$key',''))" <<< "$json"
    fi
}

# ── Check 1: pgvector extension ───────────────────────────────────────────────

hdr "Check 1 — pgvector extension"

if ! docker info &>/dev/null; then
    fail "Docker is not running; cannot query Postgres"
else
    pgv_row=$(_psql "SELECT extname FROM pg_extension WHERE extname = 'vector';" | xargs 2>/dev/null || echo "")
    if [[ "$pgv_row" == "vector" ]]; then
        ok "pgvector extension is installed"
    else
        fail "pgvector extension NOT found in $POSTGRES_CONTAINER/$DB_NAME"
        info "Fix: the Postgres image must be built from infra/postgres/Dockerfile (includes pgvector)"
        info "     docker compose down -v && docker compose up -d postgres"
        info "     cd services/eligibility && uv run alembic upgrade head"
    fi
fi

# ── Check 2: sbc_chunks table and row count ───────────────────────────────────

hdr "Check 2 — sbc_chunks table"

table_exists=$(_psql "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='sbc_chunks';" | xargs 2>/dev/null || echo "")
if [[ "$table_exists" != "1" ]]; then
    fail "sbc_chunks table does not exist"
    info "Fix: uv run alembic upgrade head  (from services/eligibility)"
else
    ok "sbc_chunks table exists"
    chunk_count=$(_psql "SELECT COUNT(*) FROM sbc_chunks;" | xargs 2>/dev/null || echo "0")
    chunk_count=$(echo "$chunk_count" | tr -d ' ')
    if [[ "$chunk_count" -gt 0 ]]; then
        ok "sbc_chunks has $chunk_count rows"
        plan_count=$(_psql "SELECT COUNT(DISTINCT plan_id) FROM sbc_chunks;" | xargs 2>/dev/null || echo "0")
        plan_count=$(echo "$plan_count" | tr -d ' ')
        ok "$plan_count distinct plan(s) with indexed chunks"
    else
        fail "sbc_chunks is empty — no chunks indexed yet"
        info "Fix: uv run python data/ingest/sbc_download.py"
        info "     uv run python data/ingest/sbc_embed_ingest.py"
    fi
fi

# ── Check 3: demo plan UUID ───────────────────────────────────────────────────

hdr "Check 3 — demo plan '${PLAN_NAME}'"

plan_uuid=$(_psql "SELECT id::text FROM plans WHERE LOWER(plan_marketing_name) = LOWER('${PLAN_NAME}') LIMIT 1;" | xargs 2>/dev/null || echo "")
plan_uuid=$(echo "$plan_uuid" | tr -d ' ')

if [[ -n "$plan_uuid" ]]; then
    ok "Found plan UUID: $plan_uuid"

    # Check that at least one chunk is linked to this plan
    linked=$(_psql "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = '$plan_uuid'::uuid;" | xargs 2>/dev/null || echo "0")
    linked=$(echo "$linked" | tr -d ' ')
    if [[ "$linked" -gt 0 ]]; then
        ok "$linked chunks linked to this plan"
    else
        warn "Plan found but 0 chunks linked — ingest against this plan name has not run"
        info "Fix: ensure sbc sidecar JSON has plan_name = '${PLAN_NAME}'"
        info "     then: uv run python data/ingest/sbc_embed_ingest.py"
    fi
else
    fail "Plan '${PLAN_NAME}' not found in plans table"
    info "Fix: bash scripts/seed_dev.sh  (runs seed_demo_member.py which inserts the demo plan)"
fi

# ── Check 4: GET /api/v1/rag/readiness ───────────────────────────────────────

hdr "Check 4 — GET ${ELIGIBILITY_URL}/api/v1/rag/readiness"

readiness_json=$(_curl_json GET "${ELIGIBILITY_URL}/api/v1/rag/readiness" || echo "")
if [[ -z "$readiness_json" ]]; then
    fail "Eligibility service not reachable at ${ELIGIBILITY_URL}"
    info "Fix: start services with  python scripts/start.py  or  just dev"
else
    rag_status=$(_jq_or_python "$readiness_json" "ragStatus")
    rag_reason=$(_jq_or_python "$readiness_json" "ragReason")
    voyage_ok=$(_jq_or_python "$readiness_json" "voyageConfigured")
    pgv_ok=$(_jq_or_python "$readiness_json" "pgvectorAvailable")
    sbc_count=$(_jq_or_python "$readiness_json" "sbcChunksCount")

    info "ragStatus       : $rag_status"
    info "ragReason       : $rag_reason"
    info "voyageConfigured: $voyage_ok"
    info "pgvectorAvailable: $pgv_ok"
    info "sbcChunksCount  : $sbc_count"

    if [[ "$rag_status" == "ready" ]]; then
        ok "RAG readiness: ready"
    elif [[ "$rag_status" == "key_missing" ]]; then
        fail "RAG readiness: key_missing — VOYAGE_API_KEY not configured"
        info "Fix: set VOYAGE_API_KEY in .env and restart the eligibility service"
    elif [[ "$rag_status" == "table_missing" ]]; then
        fail "RAG readiness: table_missing"
        info "Fix: see Checks 1 and 2 above"
    elif [[ "$rag_status" == "empty" ]]; then
        fail "RAG readiness: empty — no chunks indexed"
        info "Fix: run sbc_embed_ingest.py (see Check 2)"
    elif [[ "$rag_status" == "no_plan_links" ]]; then
        fail "RAG readiness: no_plan_links — chunks exist but none join to a plan"
        info "Fix: ensure sidecar plan_name matches plans.plan_marketing_name exactly"
    else
        fail "RAG readiness: $rag_status — $rag_reason"
    fi
fi

# ── Check 5: POST /api/v1/sbc/retrieve ───────────────────────────────────────

hdr "Check 5 — POST ${ELIGIBILITY_URL}/api/v1/sbc/retrieve"

if [[ -z "$plan_uuid" ]]; then
    warn "Skipping retrieve smoke test — no plan UUID (failed Check 3)"
elif [[ -z "$readiness_json" ]]; then
    warn "Skipping retrieve smoke test — eligibility service not reachable (failed Check 4)"
else
    retrieve_body="{\"planId\": \"${plan_uuid}\", \"query\": \"${RAG_QUERY}\", \"topK\": ${TOP_K}}"
    retrieve_json=$(_curl_json POST "${ELIGIBILITY_URL}/api/v1/sbc/retrieve" "$retrieve_body" || echo "")

    if [[ -z "$retrieve_json" ]]; then
        fail "POST /api/v1/sbc/retrieve returned no response"
    else
        if command -v jq &>/dev/null; then
            chunk_count_resp=$(echo "$retrieve_json" | jq '.chunks | length' 2>/dev/null || echo "0")
            first_chunk=$(echo "$retrieve_json" | jq -r '.chunks[0].chunkText // ""' 2>/dev/null | head -c 120)
            first_section=$(echo "$retrieve_json" | jq -r '.chunks[0].sectionName // ""' 2>/dev/null)
        else
            chunk_count_resp=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('chunks',[])))" <<< "$retrieve_json" 2>/dev/null || echo "0")
            first_chunk=$(python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('chunks',[]); print(c[0].get('chunkText','')[:120] if c else '')" <<< "$retrieve_json" 2>/dev/null || echo "")
            first_section=$(python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('chunks',[]); print(c[0].get('sectionName','') if c else '')" <<< "$retrieve_json" 2>/dev/null || echo "")
        fi

        info "query           : $RAG_QUERY"
        info "chunks returned : $chunk_count_resp"
        if [[ -n "$first_section" ]]; then
            info "top section     : $first_section"
        fi
        if [[ -n "$first_chunk" ]]; then
            info "top chunk text  : ${first_chunk}..."
        fi

        if [[ "$chunk_count_resp" -gt 0 ]]; then
            ok "RAG retrieve returned $chunk_count_resp chunk(s)"
        else
            fail "RAG retrieve returned 0 chunks for '$RAG_QUERY'"
            info "The plan exists and has $linked chunks, but none matched the query."
            info "Check: the sidecar used the correct plan_name, and the PDF text is readable."
        fi
    fi
fi

# ── Check 6: GET /api/v1/runtime/status (voice-agent RAG fields) ──────────────

hdr "Check 6 — GET ${VOICE_AGENT_URL}/api/v1/runtime/status"

runtime_json=$(_curl_json GET "${VOICE_AGENT_URL}/api/v1/runtime/status" || echo "")
if [[ -z "$runtime_json" ]]; then
    warn "Voice-agent service not reachable at ${VOICE_AGENT_URL} — skipping"
else
    va_rag_status=$(_jq_or_python "$runtime_json" "rag_status")
    va_rag_reason=$(_jq_or_python "$runtime_json" "rag_reason")
    va_runtime=$(_jq_or_python "$runtime_json" "runtime")

    info "runtime         : $va_runtime"
    info "rag_status      : $va_rag_status"
    info "rag_reason      : $va_rag_reason"

    if [[ "$va_rag_status" == "ready" ]]; then
        ok "Voice-agent runtime reports RAG ready"
    elif [[ "$va_rag_status" == "unreachable" ]]; then
        warn "Voice-agent could not reach the eligibility RAG readiness endpoint"
        info "Check that eligibility service is running and ELIGIBILITY_BASE_URL is set"
    else
        fail "Voice-agent reports rag_status=$va_rag_status: $va_rag_reason"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "─────────────────────────────────────────────────────"
if [[ "$FAILURES" -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}  All checks passed — RAG demo is ready.${RESET}"
    echo ""
    echo "  Next steps:"
    echo "  1. Open http://localhost:3000"
    echo "  2. Check the 'Plan RAG' indicator in the connections rail (green = ready)"
    echo "  3. Ask: 'Is MRI of the brain covered?'"
    echo "  4. Verify the Plan Document Evidence panel appears below the answer"
else
    echo -e "${RED}${BOLD}  $FAILURES check(s) failed — see details above.${RESET}"
    echo ""
    echo "  Full setup guide:"
    echo "  docs/components/72-ws2-ws7-local-rag-demo-readiness/RESULTS.md"
fi
echo "─────────────────────────────────────────────────────"
echo ""

exit "$FAILURES"
