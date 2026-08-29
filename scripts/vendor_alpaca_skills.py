"""Vendor an allowlisted subset of alpacahq/alpaca-skills reproducibly."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

REPOSITORY = "https://github.com/alpacahq/alpaca-skills"
DEFAULT_REF = "62891eca3d71f855bd6f87dffcfadb0dab882fb4"
ALLOWLIST = (
    "LICENSE",
    "skills/trading-api/backtest/SKILL.md",
    "skills/trading-api/backtest/reference.md",
    "skills/trading-api/paper-trading/SKILL.md",
    "skills/trading-api/paper-trading/reference.md",
    "skills/trading-api/paper-trading-cli/SKILL.md",
    "skills/trading-api/paper-trading-cli/reference.md",
    "skills/trading-api/paper-trading-mcp/SKILL.md",
    "skills/trading-api/paper-trading-mcp/reference.md",
)
ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / ".agents" / "skills" / "vendor" / "alpaca"
MANIFEST = DESTINATION / "PROVENANCE.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def safe_member(archive: tarfile.TarFile, suffix: str) -> tarfile.TarInfo:
    matches = [
        member
        for member in archive.getmembers()
        if member.isfile() and member.name.endswith("/" + suffix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one archive member for {suffix!r}; found {len(matches)}"
        )
    return matches[0]


def vendor(ref: str) -> None:
    if (
        not ref
        or any(character not in "0123456789abcdef" for character in ref.lower())
        or len(ref) != 40
    ):
        raise ValueError("--ref must be an explicit 40-character Git commit SHA")
    request = urllib.request.Request(
        f"{REPOSITORY}/archive/{ref}.tar.gz",
        headers={"User-Agent": "shadowfund-vendor-script/1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()

    temporary = DESTINATION.with_name("alpaca.incoming")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for relative in ALLOWLIST:
            member = safe_member(archive, relative)
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"Cannot read {member.name}")
            target.write_bytes(source.read())

    manifest = {
        "repository": REPOSITORY,
        "commit": ref,
        "authority": "Repository AGENTS.md and .agents/rules override vendored instructions.",
        "files": {relative: digest(temporary / relative) for relative in ALLOWLIST},
    }
    (temporary / "PROVENANCE.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    temporary.replace(DESTINATION)


def check() -> None:
    if not MANIFEST.is_file():
        raise RuntimeError(f"Missing provenance manifest: {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("repository") != REPOSITORY
        or manifest.get("commit") != DEFAULT_REF
    ):
        raise RuntimeError(
            "Vendored Alpaca provenance does not match the repository pin"
        )
    expected = manifest.get("files", {})
    if set(expected) != set(ALLOWLIST):
        raise RuntimeError("Vendored Alpaca allowlist differs from provenance manifest")
    actual_files = {
        path.relative_to(DESTINATION).as_posix()
        for path in DESTINATION.rglob("*")
        if path.is_file() and path != MANIFEST
    }
    if actual_files != set(ALLOWLIST):
        raise RuntimeError(
            f"Unexpected or missing vendored files: {sorted(actual_files ^ set(ALLOWLIST))}"
        )
    for relative, expected_digest in expected.items():
        actual_digest = digest(DESTINATION / relative)
        if actual_digest != expected_digest:
            raise RuntimeError(f"Checksum mismatch: {relative}")
    print(f"Verified {len(ALLOWLIST)} Alpaca files at {DEFAULT_REF}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", help="Explicit upstream Git commit SHA")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed files without network access",
    )
    args = parser.parse_args()
    if args.check:
        if args.ref:
            parser.error("--ref and --check are mutually exclusive")
        check()
        return
    if not args.ref:
        parser.error("vendoring requires an explicit --ref")
    vendor(args.ref)
    check()


if __name__ == "__main__":
    main()
