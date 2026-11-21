#!/usr/bin/env python3
"""Download verified contract exhibits from SEC EDGAR.

Usage from the ContractsAnalysis directory:

    uv run docs/downloader.py --email you@example.com

SEC asks automated clients to identify themselves. The email is used only in
the HTTP User-Agent header; it is not otherwise stored or transmitted.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Downloaded_Contracts"


# Direct EDGAR exhibit documents, not SEC search/home pages.
CONTRACTS_DATA = {
    "MSA": [
        "https://www.sec.gov/Archives/edgar/data/1862150/000164117225009289/ex10-4.htm",
        "https://www.sec.gov/Archives/edgar/data/1786511/000119312519280540/d757284dex105.htm",
        "https://www.sec.gov/Archives/edgar/data/1271024/000119312511016022/dex1013.htm",
        "https://www.sec.gov/Archives/edgar/data/1423542/000119312511017025/dex1012.htm",
        "https://www.sec.gov/Archives/edgar/data/1752797/000119312521251454/d28493dex104.htm",
        "https://www.sec.gov/Archives/edgar/data/1535365/000119312513277818/d482189dex105.htm",
        "https://www.sec.gov/Archives/edgar/data/1103025/000119312505150092/dex1047.htm",
        "https://www.sec.gov/Archives/edgar/data/1512077/000151207715000003/exhibit10_40.htm",
        "https://www.sec.gov/Archives/edgar/data/935036/000095012309032263/c88932exv10w2.htm",
        "https://www.sec.gov/Archives/edgar/data/1336691/000119312510245218/dex102.htm",
    ],
    "SOW": [
        "https://www.sec.gov/Archives/edgar/data/1829311/000168316823008832/bitmine_ex1003.htm",
        "https://www.sec.gov/Archives/edgar/data/1094808/000095012307011075/y38003exv10w1.htm",
        "https://www.sec.gov/Archives/edgar/data/1394056/000119312518011019/d447171dex1012.htm",
        "https://www.sec.gov/Archives/edgar/data/869986/000115752311000824/a6609178ex10-3.htm",
        "https://www.sec.gov/Archives/edgar/data/908259/000149315220014446/ex10-2.htm",
        "https://www.sec.gov/Archives/edgar/data/1125011/000110465905038841/a05-12619_1ex10d1.htm",
    ],
    "NDA": [
        "https://www.sec.gov/Archives/edgar/data/1753347/000149315225028010/ex10-11.htm",
        "https://www.sec.gov/Archives/edgar/data/711065/000119312516800517/d309035dex99e5.htm",
        "https://www.sec.gov/Archives/edgar/data/768262/000119312510128597/dex99d2.htm",
        "https://www.sec.gov/Archives/edgar/data/1274644/000119312517338759/d485523dex99d2.htm",
        "https://www.sec.gov/Archives/edgar/data/1078271/000119312519192845/d72355dex99d2.htm",
    ],
    "ORDER_FORM": [
        "https://www.sec.gov/Archives/edgar/data/2084026/000143774926020200/ex_973916.htm",
        "https://www.sec.gov/Archives/edgar/data/1970743/000121390025089658/ea025801901ex1-4_rmxind.htm",
    ],
}


CATEGORY_TERMS = {
    "MSA": ("master services agreement", "master service agreement"),
    "SOW": ("statement of work", "scope of work"),
    "NDA": ("non-disclosure agreement", "nondisclosure agreement", "confidentiality agreement"),
    "ORDER_FORM": ("order form", "subscription order"),
}


@dataclass
class DownloadResult:
    category: str
    index: int
    url: str
    status: str
    path: str = ""
    message: str = ""
    sha256: str = ""


def visible_text(content: bytes) -> str:
    decoded = content.decode("utf-8", errors="ignore")
    decoded = re.sub(r"<script\b.*?</script>", " ", decoded, flags=re.I | re.S)
    decoded = re.sub(r"<style\b.*?</style>", " ", decoded, flags=re.I | re.S)
    decoded = html.unescape(re.sub(r"<[^>]+>", " ", decoded))
    return re.sub(r"\s+", " ", decoded).strip()


def validate_contract(content: bytes, content_type: str, final_url: str, category: str) -> None:
    parsed = urllib.parse.urlparse(final_url)
    if parsed.path in {"", "/"}:
        raise ValueError("response is a website homepage, not an exhibit")
    if "html" not in content_type.lower() and b"<html" not in content[:8192].lower():
        raise ValueError(f"expected HTML but received {content_type or 'an unknown content type'}")
    text = visible_text(content)
    if len(text) < 500:
        raise ValueError("response contains too little text to be a contract")
    lowered = text.lower()
    if "sec.gov | home" in lowered[:300]:
        raise ValueError("response is the SEC homepage, not an exhibit")
    if not any(term in lowered for term in CATEGORY_TERMS[category]):
        expected = " or ".join(CATEGORY_TERMS[category])
        raise ValueError(f"content does not contain the expected contract title ({expected})")


def download(url: str, user_agent: str, timeout: float) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "identity",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.2",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get_content_type(), response.geturl()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="contact email for the SEC User-Agent")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = args.output_dir.resolve()
    user_agent = f"ContractsAnalysis contract downloader {args.email}"
    results: list[DownloadResult] = []
    seen_hashes: set[str] = set()

    for category, urls in CONTRACTS_DATA.items():
        category_dir = output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        for index, url in enumerate(urls, start=1):
            path = category_dir / f"{category}_Template_{index}.html"
            print(f"Downloading {category} {index}/{len(urls)}: {url}", flush=True)
            try:
                content: bytes | None = None
                if path.exists() and not args.force:
                    existing = path.read_bytes()
                    try:
                        validate_contract(existing, "text/html", url, category)
                    except ValueError as error:
                        print(f"  Replacing invalid existing file: {error}")
                    else:
                        content = existing
                        print("  Existing file is already a valid contract")

                if content is None:
                    content, content_type, final_url = download(url, user_agent, args.timeout)
                    validate_contract(content, content_type, final_url, category)
                    atomic_write(path, content)
                digest = hashlib.sha256(content).hexdigest()
                if digest in seen_hashes:
                    raise ValueError("duplicate document content")
                seen_hashes.add(digest)
                results.append(
                    DownloadResult(category, index, url, "ok", str(path), sha256=digest)
                )
                print(f"  OK: {path}")
            except (OSError, ValueError, urllib.error.URLError) as error:
                results.append(
                    DownloadResult(category, index, url, "failed", message=str(error))
                )
                print(f"  FAILED: {error}")
            time.sleep(max(0.0, args.delay))

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = output_dir / "download_manifest.json"
    manifest.write_text(json.dumps([asdict(item) for item in results], indent=2), encoding="utf-8")
    succeeded = sum(item.status == "ok" for item in results)
    failed = len(results) - succeeded
    print(f"\nFinished: {succeeded} downloaded, {failed} failed")
    print(f"Manifest: {manifest}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
