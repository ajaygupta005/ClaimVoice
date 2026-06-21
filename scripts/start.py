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
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
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


# ── Tool resolution ───────────────────────────────────────────────────────────

def _find_pnpm() -> list[str] | None:
    """
    Return the argv prefix to invoke pnpm, e.g. ["pnpm"] or ["/path/node", "corepack.js", "pnpm"].
    Corepack shims are shell scripts that delegate to whatever `node` is active in the shell.
    When nvm overrides PATH with an old Node, those shims break. Instead we find a Node binary
    >= 19 and run Corepack directly through it, guaranteeing the right runtime.
    """
    # 1. pnpm is a real binary on PATH (standalone installer, Volta, etc.)
    found = shutil.which("pnpm")
    if found:
        r = subprocess.run([found, "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            return [found]

    home = Path.home()

    # 2. Find a Node >= 19 binary, then run corepack pnpm through it
    node_candidates: list[Path] = []

    # Homebrew Cellar: sorted newest first
    cellar = Path("/opt/homebrew/Cellar/node")
    if cellar.exists():
        node_candidates += sorted(cellar.glob("*/bin/node"), reverse=True)

    # nvm versions: sorted newest first
    for nvm_root in [
        home / ".local" / "share" / "nvm",
        home / ".nvm" / "versions" / "node",
    ]:
        if nvm_root.exists():
            node_candidates += sorted(nvm_root.glob("*/bin/node"), reverse=True)

    # Homebrew prefix bin + system locations
    node_candidates += [
        Path("/opt/homebrew/bin/node"),
        Path("/usr/local/bin/node"),
    ]

    for node_bin in node_candidates:
        if not node_bin.exists():
            continue
        ver_r = subprocess.run([str(node_bin), "--version"], capture_output=True, text=True)
        if ver_r.returncode != 0:
            continue
        ver_str = ver_r.stdout.strip().lstrip("v")
        try:
            major = int(ver_str.split(".")[0])
        except ValueError:
            continue
        if major < 19:
            continue

        # Look for corepack.js next to this node binary
        corepack_js = node_bin.parent.parent / "lib" / "node_modules" / "corepack" / "dist" / "corepack.js"
        if not corepack_js.exists():
            continue

        # Verify it actually works
        test = subprocess.run(
            [str(node_bin), str(corepack_js), "pnpm", "--version"],
            capture_output=True, text=True,
        )
        if test.returncode == 0:
            return [str(node_bin), str(corepack_js), "pnpm"]

    # 3. Fallback: plain executable candidates (standalone pnpm, Windows)
    plain_candidates: list[Path] = [
        home / ".local" / "share" / "pnpm" / "pnpm",
        home / ".corepack" / "shims" / "pnpm",
        Path("/opt/homebrew/bin/pnpm"),
        Path("/usr/local/bin/pnpm"),
        home / "AppData" / "Local" / "pnpm" / "pnpm.cmd",
        home / "AppData" / "Roaming" / "npm" / "pnpm.cmd",
    ]
    for p in plain_candidates:
        if p.exists():
            return [str(p)]

    return None


def _find_tool(name: str) -> str | None:
    """Return the executable path for a tool, checking PATH and common install locations."""
    found = shutil.which(name)
    if found:
        return found

    home = Path.home()
    candidates: list[Path] = []

    if name == "uv":
        candidates = [
            home / ".local" / "bin" / "uv",
            home / ".cargo" / "bin" / "uv",
            Path("/opt/homebrew/bin/uv"),
            Path("/usr/local/bin/uv"),
            home / "AppData" / "Local" / "uv" / "bin" / "uv.exe",
        ]
    elif name == "docker":
        candidates = [
            Path("/usr/local/bin/docker"),
            Path("/opt/homebrew/bin/docker"),
            home / "AppData" / "Local" / "Docker" / "wsl" / "distro" / "usr" / "bin" / "docker",
        ]
    elif name == "just":
        candidates = [
            home / ".cargo" / "bin" / "just",
            Path("/opt/homebrew/bin/just"),
            Path("/usr/local/bin/just"),
            home / "AppData" / "Local" / "just" / "just.exe",
        ]
    elif name == "dvc":
        candidates = [
            home / ".local" / "bin" / "dvc",
            Path("/opt/homebrew/bin/dvc"),
            Path("/usr/local/bin/dvc"),
        ]

    for path in candidates:
        if path.exists():
            return str(path)

    return None


# Resolved tool invocations (populated by check_prerequisites).
# Values are argv prefixes: ["pnpm"] or ["/path/node", "corepack.js", "pnpm"].
TOOLS: dict[str, list[str]] = {}


def _pnpm_node_env(pnpm: list[str]) -> dict[str, str]:
    """
    Ensure pnpm lifecycle scripts use the same modern Node runtime used to
    launch Corepack. Without this, `pnpm --filter ... dev` can start tsx with
    an older nvm Node from PATH, which breaks Fastify 5.
    """
    if len(pnpm) >= 2 and Path(pnpm[0]).name == "node":
        node_bin_dir = str(Path(pnpm[0]).parent)
        existing_path = os.environ.get("PATH", "")
        return {"PATH": f"{node_bin_dir}{os.pathsep}{existing_path}"}
    return {}

# ── Prerequisite checks ───────────────────────────────────────────────────────

# required=True → hard failure; required=False → warning only
TOOLS_SPEC = [
    ("docker", True,  "https://docs.docker.com/get-docker/"),
    ("pnpm",   True,  "https://pnpm.io/installation"),
    ("uv",     True,  "https://docs.astral.sh/uv/getting-started/installation/"),
    ("just",   False, "https://github.com/casey/just#installation"),
    ("dvc",    False, "https://dvc.org/doc/install"),
]

def check_prerequisites() -> bool:
    hdr("Checking prerequisites")
    all_ok = True
    for name, required, install_url in TOOLS_SPEC:
        if name == "pnpm":
            argv = _find_pnpm()
            if argv:
                TOOLS[name] = argv
                label = "pnpm" if argv == ["pnpm"] else f"pnpm (via {' '.join(argv[:2])})"
                ok(label)
            elif required:
                err(f"{name} not found  →  {install_url}")
                all_ok = False
            else:
                warn(f"{name} not found (optional)  →  {install_url}")
        else:
            path = _find_tool(name)
            if path:
                TOOLS[name] = [path]
                label = name if shutil.which(name) else f"{name} (found at {path})"
                ok(label)
            elif required:
                err(f"{name} not found  →  {install_url}")
                all_ok = False
            else:
                warn(f"{name} not found (optional)  →  {install_url}")

    # Docker daemon running?
    docker_argv = TOOLS.get("docker", ["docker"])
    result = subprocess.run(docker_argv + ["info"], capture_output=True, text=True)
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

    pnpm = TOOLS.get("pnpm", ["pnpm"])
    uv   = TOOLS.get("uv",   ["uv"])

    # Node (pnpm)
    info("pnpm install ...")
    install_env = os.environ.copy()
    install_env.update(_pnpm_node_env(pnpm))
    r = subprocess.run(
        pnpm + ["install"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=install_env,
    )
    if r.returncode != 0:
        err(f"pnpm install failed:\n{r.stderr}")
        sys.exit(1)
    ok("pnpm install")

    # Python (uv)
    info("uv sync ...")
    r = subprocess.run(uv + ["sync"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        err(f"uv sync failed:\n{r.stderr}")
        sys.exit(1)
    ok("uv sync")


# ── Voice runtime preflight ───────────────────────────────────────────────────

def _env_value(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _is_set(key: str) -> bool:
    val = _env_value(key)
    return bool(val) and val.lower() not in {
        "changeme",
        "placeholder",
        "replace_me",
        "your_key_here",
        "your-api-key",
        "dummy",
    }


def _uv_python_import_ok(service_name: str, module_name: str) -> bool:
    """Check whether a module is importable in the same uv context as a service."""
    uv = TOOLS.get("uv", ["uv"])
    service_dir = ROOT / "services" / service_name
    probe = subprocess.run(
        uv + ["run", "python", "-c", f"import importlib; importlib.import_module({module_name!r})"],
        cwd=service_dir,
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0


def validate_voice_runtime_preflight() -> None:
    """Flag common voice-agent configuration problems before services start."""
    hdr("Voice runtime preflight")

    runtime = _env_value("CLAIMVOICE_VOICE_RUNTIME", "browser")
    model = _env_value("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
    voice = _env_value("GEMINI_LIVE_VOICE", "Zephyr")

    if runtime == "gemini-live":
        info(f"Requested voice runtime: gemini-live  (model={model}, voice={voice})")
        if _is_set("GEMINI_API_KEY"):
            ok("GEMINI_API_KEY visible to startup environment")
        else:
            warn("CLAIMVOICE_VOICE_RUNTIME=gemini-live but GEMINI_API_KEY is missing/placeholder")

        if _uv_python_import_ok("voice-agent", "google.genai"):
            ok("google-genai SDK importable for voice-agent")
        else:
            warn("google-genai SDK is not importable; Gemini Live will be unavailable and the UI will fall back")
    else:
        info(f"Requested voice runtime: {runtime or 'browser'}")
        if _is_set("GEMINI_API_KEY"):
            warn("GEMINI_API_KEY is set but CLAIMVOICE_VOICE_RUNTIME is not gemini-live; Gemini will not be used")
        else:
            ok("Using browser voice runtime")

    if _env_value("VOICE_AGENT_ANSWER_MODE", "mock") == "claude":
        if _is_set("ANTHROPIC_API_KEY"):
            ok("Claude answer mode enabled and ANTHROPIC_API_KEY is set")
        else:
            warn("VOICE_AGENT_ANSWER_MODE=claude but ANTHROPIC_API_KEY is missing/placeholder")

    if _env_value("TOOL_MODE", "mock") == "http":
        missing = [
            key for key in ["ELIGIBILITY_BASE_URL", "PROVIDERS_BASE_URL"]
            if not _env_value(key)
        ]
        if missing:
            warn(f"TOOL_MODE=http but missing: {', '.join(missing)}")
        else:
            ok("HTTP tool mode configured for Eligibility and Providers")


# ── Docker infra ──────────────────────────────────────────────────────────────

def start_infra() -> None:
    hdr("Starting Docker infrastructure")
    docker = TOOLS.get("docker", ["docker"])
    info("docker compose up -d  (may pull images on first run — this can take a few minutes)")
    # Stream output so image-pull progress is visible; don't capture
    r = subprocess.run(
        docker + ["compose", "up", "-d"],
        cwd=ROOT,
    )
    if r.returncode != 0:
        err("docker compose up failed — check output above")
        sys.exit(1)
    ok("Postgres, Redis, MinIO, MLflow, Langfuse, Prometheus, Grafana")

    # Wait for Postgres to accept connections
    info("Waiting for Postgres ...")
    for attempt in range(30):
        probe = subprocess.run(
            docker + ["exec", "claimvoice-postgres-1",
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
SERVICE_PORTS = {
    "web": 3000,
    "document-ai": 8001,
    "eligibility": 8002,
    "providers": 8003,
    "voice-agent": 8004,
    "telephony": 8005,
    "api-gateway": 8080,
}

def _spawn(
    label: str,
    cmd: list[str],
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.Popen:  # type: ignore[type-arg]
    log_path = ROOT / f".logs/{label}.log"
    log_path.parent.mkdir(exist_ok=True)
    log_file = log_path.open("w")
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=log_file,
        stderr=log_file,
        # On Windows, CREATE_NEW_PROCESS_GROUP lets us send Ctrl-Break to stop
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
    )
    return proc


def _health_check(label: str, url: str, timeout: int = 30) -> bool:
    """
    Poll `url` every second for up to `timeout` seconds.
    Returns True when the endpoint responds with HTTP 2xx, False on timeout.
    On failure, prints the last 30 lines from the service log.
    """
    log_path = ROOT / f".logs/{label}.log"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 300:
                    return True
        except Exception:
            pass
        time.sleep(1)

    err(f"{label} did not become healthy at {url} within {timeout}s")
    if log_path.exists():
        lines = log_path.read_text(errors="replace").splitlines()
        tail = lines[-30:] if len(lines) > 30 else lines
        print(_c("33", f"\n  --- last {len(tail)} lines of .logs/{label}.log ---"))
        for line in tail:
            print(f"  {line}")
        print(_c("33", "  ---"))
    return False


def _runtime_status_check() -> None:
    """Report what the running voice-agent thinks the voice runtime is."""
    url = "http://localhost:8004/api/v1/runtime/status"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        warn(f"Voice runtime status unavailable at {url}: {exc}")
        return

    try:
        import json
        data = json.loads(body)
    except Exception:
        warn(f"Voice runtime status returned non-JSON: {body[:160]}")
        return

    runtime = str(data.get("runtime", "unknown"))
    model = str(data.get("model", ""))
    voice = str(data.get("voice", ""))
    note = str(data.get("note", ""))

    if runtime == "gemini-live-configured":
        ok(f"Voice runtime: Gemini Live configured  (model={model}, voice={voice})")
    elif runtime == "gemini-live-unavailable":
        warn(f"Voice runtime: Gemini Live unavailable — {note}")
    elif runtime == "fallback":
        warn(f"Voice runtime: fallback — {note}")
    else:
        ok(f"Voice runtime: {runtime}")


def _port_in_use(port: int) -> bool:
    """Return True when a local TCP port is already accepting connections."""
    for family, host in [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.25)
                if sock.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def _ensure_service_ports_free(ports: dict[str, int]) -> None:
    """Prevent health checks from accidentally validating stale old services."""
    occupied = [(label, port) for label, port in ports.items() if _port_in_use(port)]
    if not occupied:
        return

    for label, port in occupied:
        err(f"{label} port {port} is already in use before startup")
    print()
    err("Refusing to start because an old process could make health checks lie.")
    info("Find the stale process with: lsof -nP -iTCP:<port> -sTCP:LISTEN")
    info("Clear known ClaimVoice ports with: .venv/bin/python scripts/start.py --stop")
    info("Then rerun: .venv/bin/python scripts/start.py")
    sys.exit(1)


def start_services() -> None:
    hdr("Starting services")

    pnpm = TOOLS.get("pnpm", ["pnpm"])
    uv   = TOOLS.get("uv",   ["uv"])
    node_env = _pnpm_node_env(pnpm)

    # Python services use a src/ layout; each service's src/ dir must be on
    # PYTHONPATH so uvicorn can import the package without an editable install.
    def _py_env(service_name: str) -> dict[str, str]:
        src_dir = str(ROOT / "services" / service_name / "src")
        existing = os.environ.get("PYTHONPATH", "")
        merged = f"{src_dir}{os.pathsep}{existing}" if existing else src_dir
        return {"PYTHONPATH": merged}

    # (label, command, cwd, extra_env, health_url | None, health_timeout_seconds)
    ServiceDef = tuple[str, list[str], Path, dict[str, str] | None, str | None, int]
    services: list[ServiceDef] = [
        (
            "api-gateway",
            pnpm + ["--filter", "@claimvoice/api-gateway", "dev"],
            ROOT,
            node_env,
            "http://localhost:8080/health",
            30,
        ),
        (
            "telephony",
            pnpm + ["--filter", "@claimvoice/telephony", "dev"],
            ROOT,
            node_env,
            "http://localhost:8005/health",
            30,
        ),
        (
            "document-ai",
            uv + ["run", "uvicorn", "document_ai.main:app",
             "--host", "0.0.0.0", "--port", "8001", "--reload"],
            ROOT / "services" / "document-ai",
            _py_env("document-ai"),
            "http://localhost:8001/health",
            120,
        ),
        (
            "eligibility",
            uv + ["run", "uvicorn", "eligibility.main:app",
             "--host", "0.0.0.0", "--port", "8002", "--reload"],
            ROOT / "services" / "eligibility",
            _py_env("eligibility"),
            "http://localhost:8002/health",
            30,
        ),
        (
            "providers",
            uv + ["run", "uvicorn", "providers.main:app",
             "--host", "0.0.0.0", "--port", "8003", "--reload"],
            ROOT / "services" / "providers",
            _py_env("providers"),
            "http://localhost:8003/health",
            30,
        ),
        (
            "voice-agent",
            uv + ["run", "uvicorn", "voice_agent.main:app",
             "--host", "0.0.0.0", "--port", "8004", "--reload"],
            ROOT / "services" / "voice-agent",
            _py_env("voice-agent"),
            "http://localhost:8004/health",
            30,
        ),
        (
            "web",
            pnpm + ["--filter", "@claimvoice/web", "dev"],
            ROOT,
            node_env,
            None,  # Next.js takes too long on first build; skip health-check
            0,
        ),
    ]

    _ensure_service_ports_free(SERVICE_PORTS)

    pids: list[str] = []
    failed: list[str] = []

    for label, cmd, cwd, extra_env, health_url, _health_timeout in services:
        proc = _spawn(label, cmd, cwd, extra_env)
        pids.append(f"{label}:{proc.pid}")
        info(f"spawned {label}  (pid {proc.pid})  →  .logs/{label}.log")

    PIDFILE.write_text("\n".join(pids))

    # Health-check pass: verify each service that exposes /health
    hdr("Waiting for services to be healthy")
    for label, _cmd, _cwd, _extra_env, health_url, health_timeout in services:
        if health_url is None:
            continue
        if _health_check(label, health_url, timeout=health_timeout):
            ok(f"{label}  {health_url}")
        else:
            failed.append(label)

    if failed:
        print()
        err(f"The following services failed to start: {', '.join(failed)}")
        err("Check .logs/<service>.log for details, then re-run after fixing.")
        info("Cleaning up spawned services after failed startup ...")
        stop_services()
        sys.exit(1)

    hdr("All services healthy")
    _runtime_status_check()
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


def _listening_pids_for_port(port: int) -> list[int]:
    """Return PIDs listening on a local TCP port, using lsof when available."""
    if IS_WINDOWS:
        return []

    lsof = shutil.which("lsof")
    if not lsof:
        return []

    result = subprocess.run(
        [lsof, "-tiTCP:%s" % port, "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        return []

    pids: list[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid != os.getpid() and pid not in pids:
            pids.append(pid)
    return pids


def _stop_stale_port_listeners() -> None:
    """Best-effort cleanup for reload child processes left on ClaimVoice ports."""
    if IS_WINDOWS:
        warn("Skipping stale port cleanup on Windows; use Task Manager if a port remains busy")
        return

    import signal

    stopped = 0
    for label, port in SERVICE_PORTS.items():
        for pid in _listening_pids_for_port(port):
            try:
                os.kill(pid, signal.SIGTERM)
                ok(f"stale {label} listener on port {port} (pid {pid}) stopped")
                stopped += 1
            except ProcessLookupError:
                pass
            except PermissionError:
                warn(f"stale {label} listener on port {port} (pid {pid}) could not be stopped")

    if stopped == 0:
        ok("No stale ClaimVoice port listeners")
        return

    time.sleep(0.5)
    still_busy = [
        f"{label}:{port}" for label, port in SERVICE_PORTS.items()
        if _listening_pids_for_port(port)
    ]
    if still_busy:
        warn(f"Some ports are still busy after SIGTERM: {', '.join(still_busy)}")


# ── Stop ──────────────────────────────────────────────────────────────────────

def stop_services() -> None:
    hdr("Stopping services")
    if not PIDFILE.exists():
        warn("No .claimvoice.pids file found — nothing to stop")
    else:
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

    _stop_stale_port_listeners()

    # Also stop docker infra
    info("Stopping Docker infra ...")
    docker = TOOLS.get("docker", ["docker"])
    subprocess.run(docker + ["compose", "down"], cwd=ROOT, capture_output=True)
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

    prereqs_ok = check_prerequisites()

    if args.check:
        if prereqs_ok:
            ok("All required prerequisites satisfied")
        else:
            err("Some required prerequisites are missing — see above")
            sys.exit(1)
        return

    if not prereqs_ok:
        err("\nFix the missing required prerequisites above, then re-run.")
        sys.exit(1)

    load_env()
    install_dependencies()
    validate_voice_runtime_preflight()
    start_infra()
    start_services()


if __name__ == "__main__":
    main()
