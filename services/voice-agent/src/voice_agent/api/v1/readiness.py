"""GET /health/readiness — DB preflight for WS-7 production readiness.

Checks that the required tables are present and populated so callers know
whether real tool mode is usable before starting a session.

Returns HTTP 200 with status="ready" when all checks pass.
Returns HTTP 200 with status="degraded" when some checks fail (DB is up but data is incomplete).
Returns HTTP 200 with status="unavailable" when the DB is unreachable.

Never 503 — degraded/unavailable states are expected in demo/dev environments.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from voice_agent.core.config import settings
from voice_agent.lib.logger import logger

router = APIRouter()


class TableCheck(BaseModel):
    table: str
    ok: bool
    row_count: int = -1
    detail: str = ""


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded", "unavailable"]
    tool_mode: str
    demo_mode: bool
    demo_member_present: bool
    checks: list[TableCheck]
    note: str = ""


# Tables required for real tool mode, with minimum usable row counts.
_REQUIRED_TABLES: list[tuple[str, int]] = [
    ("members", 1),
    ("plans", 1),
    ("plan_benefits", 1),
    ("formulary_drug", 1),
    ("providers", 1),
    ("in_network", 1),
]

_DEMO_MEMBER_ID = "CVX-0042-MT"


def _check_db() -> tuple[list[TableCheck], bool]:
    """Return (checks, demo_member_present). Falls back gracefully on any error."""
    try:
        import sqlalchemy as sa
        engine = sa.create_engine(settings.database_url, pool_pre_ping=True)
    except Exception as exc:
        logger.warning("readiness.db_import_error", error=str(exc))
        return [], False

    checks: list[TableCheck] = []
    demo_member_present = False

    try:
        with engine.connect() as conn:
            for table, min_rows in _REQUIRED_TABLES:
                try:
                    row = conn.execute(
                        sa.text(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
                    ).scalar()
                    count = int(row or 0)
                    ok = count >= min_rows
                    checks.append(TableCheck(
                        table=table,
                        ok=ok,
                        row_count=count,
                        detail="" if ok else f"expected ≥{min_rows} rows, found {count}",
                    ))
                except Exception as exc:
                    checks.append(TableCheck(
                        table=table,
                        ok=False,
                        detail=f"query failed: {exc}",
                    ))

            # Check canonical demo member
            try:
                row = conn.execute(
                    sa.text("SELECT 1 FROM members WHERE member_id = :mid LIMIT 1"),
                    {"mid": _DEMO_MEMBER_ID},
                ).fetchone()
                demo_member_present = row is not None
            except Exception:
                demo_member_present = False

    except Exception as exc:
        logger.warning("readiness.db_connect_error", error=str(exc))
        return [], False
    finally:
        engine.dispose()

    return checks, demo_member_present


@router.get("/health/readiness", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    checks, demo_member_present = _check_db()

    if not checks:
        return ReadinessResponse(
            status="unavailable",
            tool_mode=settings.tool_mode,
            demo_mode=settings.demo_mode,
            demo_member_present=False,
            checks=[],
            note="Database unreachable — voice agent running in mock mode only.",
        )

    all_ok = all(c.ok for c in checks)
    status: Literal["ready", "degraded", "unavailable"] = "ready" if all_ok else "degraded"

    failing = [c.table for c in checks if not c.ok]
    note = ""
    if failing:
        note = (
            f"Tables with issues: {', '.join(failing)}. "
            "Real tool mode may return errors. Run seed script to populate."
        )

    return ReadinessResponse(
        status=status,
        tool_mode=settings.tool_mode,
        demo_mode=settings.demo_mode,
        demo_member_present=demo_member_present,
        checks=checks,
        note=note,
    )
