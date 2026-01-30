#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto-unzip AOZORA zip files and convert Shift_JIS text to UTF-8.

Input:  ./aozora_zips/
Output: ./aozora_utf8/

Behavior:
- For each .zip, extracts into ./aozora_utf8/<zip_stem>/
- Converts .txt/.htm/.html to UTF-8 (tries cp932, shift_jis, shift_jisx0213, shift_jis_2004)
- Leaves other files unchanged
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

IN_DIR = Path("./aozora_zips_Rosanjin")
OUT_DIR = Path("./aozora_utf8_Rosanjin")

TEXT_EXTS = {".txt", ".htm", ".html"}
ENCODING_CANDIDATES = ("cp932", "shift_jis", "shift_jisx0213", "shift_jis_2004")


def safe_folder_name(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = name.strip().strip(".")
    return name or "zip"


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def is_probably_binary(data: bytes) -> bool:
    # Heuristic: presence of null bytes suggests binary
    return b"\x00" in data


def decode_shift_jis_family(data: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Try common Windows/Japanese Shift_JIS variants.
    Returns (text, encoding_used).
    """
    if is_probably_binary(data):
        return None, None

    for enc in ENCODING_CANDIDATES:
        try:
            text = data.decode(enc)
            return text, enc
        except UnicodeDecodeError:
            continue
    return None, None


def ensure_within_dir(base: Path, target: Path) -> Path:
    """
    Prevent Zip Slip by ensuring 'target' stays within 'base'.
    """
    base_resolved = base.resolve()
    target_resolved = target.resolve()
    if not str(target_resolved).startswith(str(base_resolved) + os.sep) and target_resolved != base_resolved:
        raise ValueError(f"Unsafe path detected (Zip Slip): {target}")
    return target


def extract_member(zipf: zipfile.ZipFile, member: zipfile.ZipInfo, dest_dir: Path) -> Path:
    """
    Extract a single zip member safely to dest_dir, returning extracted path.
    """
    # Skip directories
    if member.is_dir():
        out_path = dest_dir / member.filename
        out_path = ensure_within_dir(dest_dir, out_path)
        out_path.mkdir(parents=True, exist_ok=True)
        return out_path

    out_path = dest_dir / member.filename
    out_path = ensure_within_dir(dest_dir, out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipf.open(member, "r") as src, open(out_path, "wb") as dst:
        shutil.copyfileobj(src, dst)

    return out_path


def convert_text_file_in_place(path: Path) -> Optional[str]:
    """
    Convert file to UTF-8 in place if it decodes as Shift_JIS-family.
    Returns encoding used if converted, else None.
    """
    ext = path.suffix.lower()
    if ext not in TEXT_EXTS:
        return None

    data = path.read_bytes()

    # If it's already valid UTF-8, leave it as-is
    try:
        data.decode("utf-8")
        return None
    except UnicodeDecodeError:
        pass

    text, enc = decode_shift_jis_family(data)
    if text is None or enc is None:
        return None

    # Write UTF-8 (no BOM)
    path.write_text(text, encoding="utf-8", newline="\n")
    return enc


def process_zip(zip_path: Path, out_root: Path) -> None:
    zip_stem = safe_folder_name(zip_path.stem)
    dest_dir = out_root / zip_stem
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n== {zip_path.name} -> {dest_dir} ==")

    with zipfile.ZipFile(zip_path, "r") as z:
        members = z.infolist()

        for m in members:
            try:
                extracted_path = extract_member(z, m, dest_dir)
            except Exception as e:
                print(f"  [EXTRACT ERROR] {m.filename}: {e}", file=sys.stderr)
                continue

            # Convert text files
            if extracted_path.is_file():
                used = None
                try:
                    used = convert_text_file_in_place(extracted_path)
                except Exception as e:
                    print(f"  [CONVERT ERROR] {extracted_path.relative_to(dest_dir)}: {e}", file=sys.stderr)

                if used:
                    print(f"  converted: {extracted_path.relative_to(dest_dir)} ({used} -> utf-8)")
                else:
                    # Keep output quieter: comment out if you want full logs
                    # print(f"  extracted: {extracted_path.relative_to(dest_dir)}")
                    pass


def main() -> int:
    if not IN_DIR.exists():
        print(f"Input folder not found: {IN_DIR.resolve()}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    zip_files = sorted(IN_DIR.glob("*.zip"))
    if not zip_files:
        print(f"No .zip files found in: {IN_DIR.resolve()}", file=sys.stderr)
        return 1

    print(f"Input : {IN_DIR.resolve()}")
    print(f"Output: {OUT_DIR.resolve()}")
    print(f"ZIPs  : {len(zip_files)}")

    for zp in zip_files:
        try:
            process_zip(zp, OUT_DIR)
        except zipfile.BadZipFile:
            print(f"[BAD ZIP] {zp.name}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] {zp.name}: {e}", file=sys.stderr)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
