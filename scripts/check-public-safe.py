#!/usr/bin/env python3
"""Scan for content that must not ship in the public equser package.

equser is published to PyPI and its repository is public. This script is a
fail-closed guardrail: it scans source and/or the built distribution artifacts
for secrets and internal-only detail (internal service/mount names, ports,
network topology, unreleased-product roadmap, private codenames) that belong in
the private repos, not in a public client toolkit.

Usage::

    # Scan the git-tracked working tree (default)
    python scripts/check-public-safe.py

    # Scan explicit paths
    python scripts/check-public-safe.py equser/ CHANGELOG.md

    # Scan the built sdist + wheel in dist/ (what actually ships)
    python scripts/check-public-safe.py --dist

Exit status is non-zero if any match is found. Reviewed, intentional matches can
be listed in scripts/public-safe-allow.txt (one substring per line; a line is
skipped if it contains any allowlisted substring).

Former *public* API names that are legitimate migration history (documented in
the changelog) are intentionally NOT flagged; only internal-only names are.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Secret patterns use generic, industry-standard token formats, so keeping them
# in cleartext reveals nothing about EQ. (name, severity, compiled pattern.)
_SECRET_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("PyPI token", "CRITICAL", re.compile(r"pypi-[A-Za-z0-9_]{16,}")),
    ("GitHub token", "CRITICAL", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("OpenAI-style key", "CRITICAL", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Slack token", "CRITICAL", re.compile(r"xox[baprs]-[A-Za-z0-9-]+")),
    ("AWS access key", "CRITICAL", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private key block", "CRITICAL", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Inline password", "HIGH", re.compile(r"""password\s*=\s*['"][^'"]+['"]""")),
]

# Internal-marker patterns (service/mount names, ports, topology, codenames,
# roadmap) are base64-encoded so this *public* file is not itself a cleartext
# index of EQ's internal names. This is obfuscation, not encryption — these are
# hygiene items, not secrets — but it keeps a plain `grep` on the public repo
# from turning up the very terms the scanner exists to remove.
# To add a term:  python scripts/check-public-safe.py --encode 'your-regex'
_INTERNAL_B64: list[tuple[str, str]] = [
    ("HIGH", "UkFHX1NFUlZFUl9CSU5E"),
    ("MEDIUM", "XGJOZWJ1bGFcYg=="),
    ("MEDIUM", "ZXEtd2F0Y2g="),
    ("MEDIUM", "ZXEtc2lnaHQ="),
    ("MEDIUM", "L21udC9lcWRhdGE="),
    ("MEDIUM", "L3Zhci9saWIvZXEtKD86d2F0Y2h8c2lnaHQp"),
    ("MEDIUM", "XGJTRVAtXGQrXGI="),
    ("MEDIUM", "RVEgU3luYXBzZQ=="),
    ("MEDIUM", "ZXEtc3luYXBzZQ=="),
    ("MEDIUM", "c3luYXBzZS0oPzpjb21wdXRlfHJhZ3x3ZWJ8ZGVtb2R8Y29yZXxkYik="),
    ("MEDIUM", "RGF0YWxha2VDbGllbnQ="),
]

_RULES: list[tuple[str, str, re.Pattern[str]]] = _SECRET_RULES + [
    ("Internal-only detail", severity, re.compile(base64.b64decode(enc).decode()))
    for severity, enc in _INTERNAL_B64
]

# Files that legitimately contain the trigger strings (this scanner and its
# allowlist define the patterns themselves).
_SELF_SKIP = {"scripts/check-public-safe.py", "scripts/public-safe-allow.txt"}

# Extensions worth scanning as text; anything else is treated as binary/skip.
_TEXT_SUFFIXES = {
    ".py", ".ipynb", ".md", ".rst", ".txt", ".toml", ".cfg", ".ini",
    ".yaml", ".yml", ".json", ".sh", ".html", ".cson", "",
}


def _load_allowlist() -> list[str]:
    path = REPO_ROOT / "scripts" / "public-safe-allow.txt"
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return [REPO_ROOT / p for p in out.stdout.splitlines() if p]


def _iter_paths(args: list[str]) -> list[tuple[str, Path]]:
    """Return (display_name, path) pairs to scan from explicit args or git."""
    result: list[tuple[str, Path]] = []
    targets = [Path(a) for a in args] if args else _tracked_files()
    for target in targets:
        if target.is_dir():
            result.extend((str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT)
                           else str(p), p) for p in sorted(target.rglob("*")) if p.is_file())
        elif target.is_file():
            rel = str(target.relative_to(REPO_ROOT)) if target.is_relative_to(REPO_ROOT) \
                else str(target)
            result.append((rel, target))
    return result


def _scan_text(name: str, text: str, allow: list[str]) -> list[tuple[int, str, str, str]]:
    """Return (lineno, severity, rule, line) findings for one text blob."""
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(a in line for a in allow):
            continue
        for rule_name, severity, pattern in _RULES:
            if pattern.search(line):
                findings.append((lineno, severity, rule_name, line.strip()[:160]))
    return findings


def _scan_files(pairs: list[tuple[str, Path]], allow: list[str]) -> int:
    total = 0
    for name, path in pairs:
        if name.replace("\\", "/") in _SELF_SKIP:
            continue
        if path.suffix not in _TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, severity, rule, line in _scan_text(name, text, allow):
            print(f"{severity:8} {name}:{lineno}: {rule}: {line}")
            total += 1
    return total


def _scan_dist(allow: list[str]) -> int:
    """Scan the contents of built sdist/wheel artifacts in dist/."""
    dist = REPO_ROOT / "dist"
    artifacts = sorted(dist.glob("*.tar.gz")) + sorted(dist.glob("*.whl"))
    if not artifacts:
        print("ERROR: no artifacts found in dist/ (build first with `uv build`)", file=sys.stderr)
        return -1

    total = 0
    for artifact in artifacts:
        print(f"# scanning {artifact.name}")
        members: list[tuple[str, bytes]] = []
        if artifact.suffix == ".whl" or artifact.name.endswith(".zip"):
            with zipfile.ZipFile(artifact) as zf:
                members = [(n, zf.read(n)) for n in zf.namelist() if not n.endswith("/")]
        else:
            with tarfile.open(artifact, "r:gz") as tf:
                for m in tf.getmembers():
                    if m.isfile():
                        f = tf.extractfile(m)
                        if f is not None:
                            members.append((m.name, f.read()))
        for member_name, raw in members:
            if Path(member_name).suffix not in _TEXT_SUFFIXES:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, severity, rule, line in _scan_text(member_name, text, allow):
                print(f"{severity:8} {artifact.name}!{member_name}:{lineno}: {rule}: {line}")
                total += 1
    return total


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--encode" in argv:
        i = argv.index("--encode")
        term = argv[i + 1]
        print(f'    ("MEDIUM", "{base64.b64encode(term.encode()).decode()}"),')
        return 0

    allow = _load_allowlist()

    if "--dist" in argv:
        argv.remove("--dist")
        count = _scan_dist(allow)
    else:
        count = _scan_files(_iter_paths(argv), allow)

    if count < 0:
        return 2
    if count:
        print(f"\nFAIL: {count} public-safety issue(s) found. "
              f"Remove them, or allowlist reviewed exceptions in "
              f"scripts/public-safe-allow.txt.")
        return 1
    print("OK: no public-safety issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
