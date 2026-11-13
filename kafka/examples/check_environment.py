"""Check local workshop prerequisites before starting either Compose project."""

import argparse
import importlib
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT_VERSION = "2.12.2"
COMPOSE_MINIMUM = (2, 20, 0)
PROFILES = {"single": (9092,), "cluster": (19092, 29092, 39092)}
GIB = 1024**3


class PrerequisiteError(RuntimeError):
    pass


def command(*args):
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, check=False,
        )
    except FileNotFoundError as error:
        raise PrerequisiteError(
            f"{args[0]} not found on PATH; install it using kafka/environment-setup.md"
        ) from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PrerequisiteError(
            f"{' '.join(args)} exited {result.returncode}: {detail[-2000:]}"
        )
    return result.stdout.strip()


def check_python():
    if sys.version_info[:2] != (3, 13) or platform.python_implementation() != "CPython":
        raise PrerequisiteError("use uv venv --python 3.13 and its CPython interpreter")
    if struct.calcsize("P") != 8:
        raise PrerequisiteError("install a native 64-bit Python")
    if sys.prefix == sys.base_prefix:
        raise PrerequisiteError("invoke .venv's Python, not the system interpreter")
    architecture = platform.machine().lower()
    if architecture not in ("amd64", "x86_64", "arm64", "aarch64"):
        raise PrerequisiteError(f"CPU architecture {architecture} is outside the baseline")
    if sys.platform == "win32" and architecture not in ("amd64", "x86_64"):
        raise PrerequisiteError("native Windows ARM is outside the workshop baseline")
    return f"{sys.version.split()[0]} at {sys.executable}"


def check_client():
    client = importlib.import_module("confluent_kafka")
    actual = client.__version__
    if actual != CLIENT_VERSION:
        raise PrerequisiteError(
            f"confluent-kafka {actual}; install pinned requirements ({CLIENT_VERSION})"
        )
    return f"confluent-kafka {actual}; librdkafka {client.libversion()[0]}"


def check_checkout():
    if Path.cwd().resolve() != ROOT:
        raise PrerequisiteError(f"run from repository root: {ROOT}")
    return str(ROOT)


def check_tools():
    return f"{command('git', '--version')}; {command('uv', '--version')}"


def check_storage():
    state = ROOT / ".state"
    storage = state if state.exists() else ROOT
    with tempfile.TemporaryDirectory(prefix=".kafka-preflight-", dir=storage) as folder:
        with closing(sqlite3.connect(str(Path(folder) / "probe.db"))) as connection:
            connection.execute("CREATE TABLE probe (value INTEGER)")
            connection.execute("INSERT INTO probe VALUES (1)")
            connection.commit()
            if connection.execute("SELECT value FROM probe").fetchone() != (1,):
                raise PrerequisiteError("SQLite write/read probe did not round-trip")
    free = shutil.disk_usage(storage).free / GIB
    if free < 10:
        raise PrerequisiteError(
            f"SQLite storage disk has {free:.1f} GiB free; allow at least 10 GiB plus tool/image headroom"
        )
    print(
        "WARN: verify Docker backing-disk free space separately; writable SQLite storage "
        "does not establish local-filesystem suitability or Docker disk capacity."
    )
    return f"temporary SQLite transaction succeeded in {storage}; disk {free:.1f} GiB free"


def check_context():
    contexts = json.loads(command("docker", "context", "inspect"))
    endpoint = contexts[0]["Endpoints"]["docker"]["Host"]
    if not os.environ.get("DOCKER_CONTEXT") and os.environ.get("DOCKER_HOST"):
        endpoint = os.environ["DOCKER_HOST"]
    if not endpoint.startswith(("unix://", "npipe://")):
        raise PrerequisiteError(
            f"Docker endpoint {endpoint!r} is not a local socket/named pipe; "
            "select local Docker Desktop/Engine and check DOCKER_HOST/DOCKER_CONTEXT"
        )
    return f"{contexts[0]['Name']}: {endpoint}"


def check_docker(profile):
    info = json.loads(command("docker", "info", "--format", "{{json .}}"))
    if info["OSType"] != "linux":
        raise PrerequisiteError("select Linux containers, not Windows containers")
    aliases = {"amd64": "x86_64", "aarch64": "arm64"}
    host = aliases.get(platform.machine().lower(), platform.machine().lower())
    engine = aliases.get(info["Architecture"].lower(), info["Architecture"].lower())
    if engine != host:
        raise PrerequisiteError(
            f"host {host} and Docker engine {engine} differ; use native tools and a local daemon"
        )
    memory = info["MemTotal"] / GIB
    budget = 4 if profile == "single" else 8
    print(
        f"WARN: Docker reports {memory:.1f} GiB total memory; allow {budget} GB "
        "available to this lab plus host overhead. Total is not available memory."
    )
    if info["MemTotal"] < budget * 1_000_000_000:
        raise PrerequisiteError(f"increase Docker/WSL memory to the {budget} GB lab budget")
    return f"Linux/{engine}; Docker server {info['ServerVersion']}"


def check_compose():
    version = command("docker", "compose", "version", "--short")
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+][\w.-]+)?", version)
    if not match or tuple(map(int, match.groups())) < COMPOSE_MINIMUM:
        raise PrerequisiteError(f"Compose {version!r}; install Compose 2.20.0 or newer")
    return version


def check_configuration():
    for profile in PROFILES:
        path = ROOT / "kafka" / "infrastructure" / f"compose.{profile}.yml"
        command("docker", "compose", "-f", str(path), "config", "--quiet")
    return "both Compose files accepted"


def check_ports(profile):
    for port in PROFILES[profile]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                # Windows SO_REUSEADDR can hide another listener; request exclusivity.
                if sys.platform == "win32":
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                listener.bind(("127.0.0.1", port))
        except OSError as error:
            raise PrerequisiteError(
                f"cannot reserve loopback port {port}: {error}. This is a pre-start "
                "check; an existing workshop broker occupies its own port. Identify "
                "the owner before stopping only your lab project without --volumes."
            ) from error
    return f"loopback ports {PROFILES[profile]} free now (released after probe)"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="single")
    args = parser.parse_args(argv)
    print(f"Host: {platform.platform()} / {platform.machine()}; profile={args.profile}")
    print("Pre-start checks only; see kafka/environment-setup.md for recovery steps.")
    checks = [
        ("repository root", check_checkout),
        ("Python environment", check_python),
        ("Python client", check_client),
        ("setup tools", check_tools),
        ("local SQLite and disk", check_storage),
        ("local Docker context", check_context),
        ("Docker daemon", lambda: check_docker(args.profile)),
        ("Compose version", check_compose),
        ("Compose configuration", check_configuration),
        ("published ports", lambda: check_ports(args.profile)),
    ]
    failures = 0
    for label, check in checks:
        try:
            detail = check()
        except (
            PrerequisiteError, OSError, subprocess.SubprocessError, ImportError,
            ValueError, KeyError, IndexError, TypeError, sqlite3.Error,
        ) as error:
            failures += 1
            print(f"FAIL [{label}]: {error}")
        else:
            print(f"PASS [{label}]: {detail}")
    if failures:
        print(f"NOT READY: {failures} blocking check(s) failed.")
        return 1
    print(
        "READY for explicit image pull/start/smoke commands, subject to resource "
        "warnings. No broker connectivity or end-to-end OS validation was performed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
