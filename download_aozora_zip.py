#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download all ZIP files linked from Aozora Bunko author works list page.

Example target:
https://www.aozora.gr.jp/index_pages/person1403.html#sakuhin_list_1

How it works:
1) Parse the author page and collect "図書カード" links.
2) For each card page, find links ending in ".zip".
3) Download each zip into output directory.

Output naming:
- Files are saved as sequential IDs in download order: 000001.zip, 000002.zip, ...
- Files are NOT unzipped.
"""

from __future__ import annotations

import os
import re
import sys
import time
import pathlib
import urllib.parse
from typing import Iterable, List, Set, Tuple

import requests
from bs4 import BeautifulSoup

AUTHOR_PAGE_URL = "https://www.aozora.gr.jp/index_pages/person1403.html"
BASE_URL = "https://www.aozora.gr.jp/"
OUTPUT_DIR = "aozora_zips_Rosanjin"
SLEEP_SEC = 0.5  # polite delay between requests


def fetch_html(session: requests.Session, url: str, timeout: int = 30) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    if not resp.encoding:
        resp.encoding = "shift_jis"
    return resp.text


def absolute_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def iter_card_links(author_html: str) -> Iterable[Tuple[str, str]]:
    """
    Returns iterable of (title, card_url).
    """
    soup = BeautifulSoup(author_html, "html.parser")
    card_re = re.compile(r"^https?://www\.aozora\.gr\.jp/cards/\d+/card\d+\.html$")
    seen: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = absolute_url(BASE_URL, a["href"])
        if card_re.match(href) and href not in seen:
            seen.add(href)
            title = a.get_text(strip=True)
            yield title, href


def extract_zip_links(card_html: str, card_url: str) -> List[str]:
    """
    From a work card page, return all zip file URLs.
    """
    soup = BeautifulSoup(card_html, "html.parser")

    zip_links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".zip"):
            zip_links.append(absolute_url(card_url, href))

    # Deduplicate while preserving order
    seen: Set[str] = set()
    out: List[str] = []
    for u in zip_links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_file(session: requests.Session, url: str, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # If exists and non-empty, skip
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"SKIP: {out_path.name} (already downloaded)")
        return

    with session.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        tmp_path = out_path.with_suffix(out_path.suffix + ".part")
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        tmp_path.replace(out_path)

    print(f"DOWNLOADED: {out_path.name}")


def main() -> int:
    out_dir = pathlib.Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; aozora-zip-downloader/1.0; +https://www.aozora.gr.jp/)"
    }

    session = requests.Session()
    session.headers.update(headers)

    print(f"Author page: {AUTHOR_PAGE_URL}")
    author_html = fetch_html(session, AUTHOR_PAGE_URL)

    card_links = list(iter_card_links(author_html))
    print(f"Found {len(card_links)} work card pages")

    all_zips: List[Tuple[str, str]] = []  # (title, zip_url)

    for idx, (title, card_url) in enumerate(card_links, start=1):
        try:
            card_html = fetch_html(session, card_url)
        except Exception as e:
            print(f"ERROR fetching card page: {card_url} ({e})", file=sys.stderr)
            continue

        zip_urls = extract_zip_links(card_html, card_url)
        for z in zip_urls:
            all_zips.append((title, z))

        print(f"[{idx}/{len(card_links)}] {title}: {len(zip_urls)} zip link(s)")
        time.sleep(SLEEP_SEC)

    # Deduplicate zip urls overall (preserving first-seen order)
    seen_zip: Set[str] = set()
    unique_zips: List[Tuple[str, str]] = []
    for title, z in all_zips:
        if z not in seen_zip:
            seen_zip.add(z)
            unique_zips.append((title, z))

    print(f"Total unique ZIP files: {len(unique_zips)}")

    # Download with sequential numeric IDs in download order
    width = max(6, len(str(len(unique_zips))))  # at least 6 digits (000001), grow if needed

    for file_id, (_title, zip_url) in enumerate(unique_zips, start=1):
        # Preserve .zip extension (Aozora links are .zip by construction)
        out_name = f"{file_id:0{width}d}.zip"
        out_path = out_dir / out_name

        try:
            download_file(session, zip_url, out_path)
        except Exception as e:
            print(f"ERROR downloading {zip_url} ({e})", file=sys.stderr)

        time.sleep(SLEEP_SEC)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
