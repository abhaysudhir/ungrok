#!/usr/bin/env python3
"""Build a deterministic source archive from a clean committed checkout."""
import argparse
import gzip
import hashlib
from pathlib import Path
import re
import subprocess


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def build(root, output):
    if git(root, "status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("Commit or remove working-tree changes before packaging.")
    source = git(root, "show", "HEAD:ungrok.py").decode()
    match = re.search(r'^VERSION = "([0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?)"$', source, re.M)
    if not match:
        raise ValueError("Missing or invalid committed VERSION.")
    version = match.group(1)
    name = f"ungrok-{version}.tar.gz"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / name
    checksums = output / "SHA256SUMS"
    if archive.exists() or checksums.exists():
        raise ValueError("Output already exists; choose a fresh output directory.")
    data = git(root, "archive", "--format=tar", f"--prefix=ungrok-{version}/", "HEAD")
    # GzipFile fixes filename, timestamp, and platform byte for repeatable builds.
    with archive.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(data)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    with checksums.open("x", encoding="ascii") as stream:
        stream.write(f"{sha}  {name}\n")
    return archive, checksums


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        for path in build(Path(__file__).resolve().parents[1], args.output_dir.resolve()):
            print(path)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release build failed: {error}\n")
