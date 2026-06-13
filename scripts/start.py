#!/usr/bin/env python3
"""
ClaimVoice local startup script.
Cross-platform (macOS, Linux, Windows). Requires Python 3.12+.

Usage:
    python scripts/start.py            # start all services
    python scripts/start.py --stop     # stop all background processes
    python scripts/start.py --check    # dependency check only
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = platform.system() == "Windows"

# ── Colour helpers ────────────────────────────────────────────────────────────

def _supports_colour() -> bool:
    if IS_WINDOWS:
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOUR = _supports_colour()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOUR else text

def ok(msg: str)   -> None: print(_c("32", f"  ✔  {msg}"))
def warn(msg: str) -> None: print(_c("33", f"  ⚠  {msg}"))
def err(msg: str)  -> None: print(_c("31", f"  ✖  {msg}"))
def hdr(msg: str)  -> None: print(_c("1;36", f"\n{msg}"))
def info(msg: str) -> None: print(f"     {msg}")


# ── Prerequisite checks ───────────────────────────────────────────────────────

REQUIRED_TOOLS = [
    ("docker",  "https://docs.docker.com/get-docker/"),
    ("pnpm",    "https://pnpm.io/installation"),
    ("uv",      "https://docs.astral.sh/uv/getting-started/installation/"),
    ("just",    "https://github.com/casey/just#installation"),
    ("dvc",     "https://dvc.org/doc/install"),
]

def check_prerequisites() -> bool:
    hdr("Checking prerequisites")
    all_ok = True
    for tool, install_url in REQUIRED_TOOLS:
        if shutil.which(tool):
            ok(tool)
        else:
            err(f"{tool} not found  →  {install_url}")
            all_ok = False

    # Docker daemon running?
    result = subprocess.run(
        ["docker", "info"], capture_output=True, text=True
    )
    if result.returncode != 0:
        err("Docker daemon is not running — start Docker Desktop first")
        all_ok = False
    else:
        ok("Docker daemon")

    return all_ok


# ── .env handling ─────────────────────────────────────────────────────────────

def load_env() -> None:
    """Load .env into os.environ if not already set, then export to child procs."""
    hdr("Loading environment")
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"

    if not env_file.exists():
        if env_example.exists():
            warn(".env not found — copying from .env.example (fill in API keys!)")
            import shutil as _sh
            _sh.copy(env_example, env_file)
        else:
            warn(".env not found and no .env.example — skipping")
            return

    lines_loaded = 0
    with env_file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key not in os.environ:          # don't clobber shell exports
                os.environ[key] = val
            lines_loaded += 1

    ok(f".env loaded ({lines_loaded} vars)")


# ── Dependency installation ───────────────────────────────────────────────────

def install_dependencies() -> None:
    hdr("Installing dependencies")

    # Node (pnpm)
    info("pnpm install ...")
    r = subprocess.run(["pnpm", "install"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        err(f"pnpm install failed:\n{r.stderr}")
        sys.exit(1)
    ok("pnpm install")

    # Python (uv)
    info("uv sync ...")
    r = subprocess.run(["uv", "sync"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        err(f"uv sync failed:\n{r.stderr}")
        sys.exit(1)
    ok("uv sync")


# ── Docker infra ──────────────────────────────────────────────────────────────

def start_infra() -> None:
    hdr("Starting Docker infrastructure")
    info("docker compose up -d ...")
    r = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if r.returncode != 0:
        err(f"docker compose up failed:\n{r.stderr}")
        sys.exit(1)
    ok("Postgres, Redis, MinIO, MLflow, Langfuse, Prometheus, Grafana")

    # Wait for Postgres to accept connections
    info("Waiting for Postgres ...")
    for attempt in range(30):
        probe = subprocess.run(
            ["docker", "exec", "claimvoice-postgres-1",
             "pg_isready", "-U", "postgres"],
            capture_output=True,
        )
        if probe.returncode == 0:
            ok("Postgres ready")
            return
        time.sleep(1)
    warn("Postgres did not become ready in 30 s — proceeding anyway")


# ── Service launchers ─────────────────────────────────────────────────────────

PIDFILE = ROOT / ".claimvoice.pids"

def _spawn(label: str, cmd: list[str], cwd: Path) -> subprocess.Popen:  # type: ignore[type-arg]
    log_path = ROOT / f".logs/{label}.log"
    log_path.parent.mkdir(exist_ok=True)
    log_file = log_path.open("w")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=os.environ.copy(),
        stdout=log_file,
        stderr=log_file,
        # On Windows, CREATE_NEW_PROCESS_GROUP lets us send Ctrl-Break to stop
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
    )
    return proc


def start_services() -> None:
    hdr("Starting services")

    services: list[tuple[str, list[str], Path]] = [
        # (label, command, cwd)
        (
            "api-gateway",
            ["pnpm", "--filter", "@claimvoice/api-gateway", "dev"],
            ROOT,
        ),
        (
            "telephony",
            ["pnpm", "--filter", "@claimvoice/telephony", "dev"],
            ROOT,
        ),
        (
            "document-ai",
            ["uv", "run", "uvicorn", "document_ai.main:app",
             "--host", "0.0.0.0", "--port", "8001", "--reload"],
            ROOT / "services" / "document-ai",
        ),
        (
            "eligibility",
            ["uv", "run", "uvicorn", "eligibility.main:app",
             "--host", "0.0.0.0", "--port", "8002", "--reload"],
            ROOT / "services" / "eligibility",
        ),
        (
            "providers",
            ["uv", "run", "uvicorn", "providers.main:app",
             "--host", "0.0.0.0", "--port", "8003", "--reload"],
            ROOT / "services" / "providers",
        ),
        (
            "voice-agent",
            ["uv", "run", "uvicorn", "voice_agent.main:app",
             "--host", "0.0.0.0", "--port", "8004", "--reload"],
            ROOT / "services" / "voice-agent",
        ),
        (
            "web",
            ["pnpm", "--filter", "@claimvoice/web", "dev"],
            ROOT,
        ),
    ]

    pids: list[str] = []
    for label, cmd, cwd in services:
        proc = _spawn(label, cmd, cwd)
        pids.append(f"{label}:{proc.pid}")
        ok(f"{label}  (pid {proc.pid})  →  .logs/{label}.log")

    PIDFILE.write_text("\n".join(pids))

    hdr("All services started")
    print()
    info("  Web app        →  http://localhost:3000")
    info("  API gateway    →  http://localhost:8080")
    info("  Telephony      →  http://localhost:8005")
    info("  Document AI    →  http://localhost:8001")
    info("  Eligibility    →  http://localhost:8002")
    info("  Providers      →  http://localhost:8003")
    info("  Voice agent    →  http://localhost:8004")
    info("  MLflow         →  http://localhost:5000")
    info("  Langfuse       →  http://localhost:3001")
    info("  Grafana        →  http://localhost:3002")
    print()
    info("Logs are in .logs/<service>.log")
    info("To stop:  python scripts/start.py --stop")
    print()


# ── Stop ──────────────────────────────────────────────────────────────────────

def stop_services() -> None:
    hdr("Stopping services")
    if not PIDFILE.exists():
        warn("No .claimvoice.pids file found — nothing to stop")
        return

    import signal

    for entry in PIDFILE.read_text().splitlines():
        if ":" not in entry:
            continue
        label, _, pid_str = entry.partition(":")
        try:
            pid = int(pid_str)
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
            ok(f"{label} (pid {pid}) stopped")
        except (ProcessLookupError, PermissionError):
            warn(f"{label} (pid {pid}) was already gone")
        except ValueError:
            warn(f"Unreadable pid entry: {entry!r}")

    PIDFILE.unlink()

    # Also stop docker infra
    info("Stopping Docker infra ...")
    subprocess.run(["docker", "compose", "down"], cwd=ROOT, capture_output=True)
    ok("Docker infra stopped")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ClaimVoice local startup")
    parser.add_argument("--stop",  action="store_true", help="Stop all services")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")
    args = parser.parse_args()

    os.chdir(ROOT)

    if args.stop:
        stop_services()
        return

    print(_c("1;35", "\n  ClaimVoice — local startup\n"))

    if not check_prerequisites():
        err("\nFix the missing prerequisites above, then re-run.")
        sys.exit(1)

    if args.check:
        ok("All prerequisites satisfied")
        return

    load_env()
    install_dependencies()
    start_infra()
    start_services()


if __name__ == "__main__":
    main()
