#!/usr/bin/env python3
"""Download or convert contract HTML into real PDF and/or DOCX files.

The SEC normally publishes filing exhibits as HTML.  Changing the extension to
``.pdf`` or ``.docx`` does not convert them, so this script uses LibreOffice's
headless Writer conversion and then validates the generated file signatures.

Examples (run from the ContractsAnalysis directory):

    # Convert HTML files that downloader.py already fetched.
    python docs/download_contracts_as_documents.py --format both

    # Download the URLs in downloader.py, then convert them.
    python docs/download_contracts_as_documents.py \
        --config docs/downloader.py --email you@example.com --format both

    # Download one or more explicit contract URLs.
    python docs/download_contracts_as_documents.py \
        --url MSA=https://www.sec.gov/Archives/edgar/data/.../ex10.htm \
        --email you@example.com --format pdf
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = SCRIPT_DIR / "Downloaded_Contracts"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Converted_Contracts"
DEFAULT_CONFIG = SCRIPT_DIR / "downloader.py"


@dataclass
class Result:
    source: str
    category: str
    name: str
    status: str
    outputs: list[str]
    message: str = ""


def safe_name(value: str, fallback: str = "contract") -> str:
    value = urllib.parse.unquote(value).strip()
    value = re.sub(r"\.(?:html?|pdf|docx?)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return value[:120] or fallback


def find_libreoffice(explicit: str | None) -> Path:
    candidates = [
        explicit,
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/lib/libreoffice/program/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError(
        "LibreOffice was not found. Install it, or pass --libreoffice with the "
        "full path to the soffice executable."
    )


def load_config(path: Path) -> dict[str, list[str]]:
    spec = importlib.util.spec_from_file_location("contract_download_config", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load config: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = getattr(module, "CONTRACTS_DATA", None)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must define CONTRACTS_DATA as a dictionary")
    return {str(category): list(urls) for category, urls in data.items()}


def parse_url_arguments(values: Iterable[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --url value {value!r}; use CATEGORY=https://...")
        category, url = value.split("=", 1)
        category = safe_name(category, "UNCATEGORIZED").upper()
        result.setdefault(category, []).append(url)
    return result


def html_title(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()


def validate_contract_html(content: bytes, source: str) -> None:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"} and parsed.netloc.lower().endswith("sec.gov"):
        if parsed.path in {"", "/"}:
            raise ValueError("the URL is the SEC homepage, not a filing exhibit")

    title = html_title(content).lower()
    if title in {"sec.gov | home", "sec.gov", "home | sec.gov"}:
        raise ValueError("the downloaded page is the SEC homepage, not a contract")

    decoded = content.decode("utf-8", errors="ignore")
    visible = re.sub(r"<script\b.*?</script>", " ", decoded, flags=re.I | re.S)
    visible = re.sub(r"<style\b.*?</style>", " ", visible, flags=re.I | re.S)
    visible = html.unescape(re.sub(r"<[^>]+>", " ", visible))
    visible = re.sub(r"\s+", " ", visible).strip()
    if len(visible) < 500:
        raise ValueError("the HTML page contains too little text to be a contract")


def document_kind(content: bytes, content_type: str = "") -> str:
    if content.startswith(b"%PDF-"):
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        try:
            import io

            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
            if "[Content_Types].xml" in names and "word/document.xml" in names:
                return "docx"
        except zipfile.BadZipFile:
            pass
    lowered = content[:4096].lower()
    if (
        "html" in content_type.lower()
        or b"<html" in lowered
        or b"<!doctype html" in lowered
        or b"<document>" in lowered
    ):
        return "html"
    return "unknown"


def download(url: str, user_agent: str, timeout: float) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "identity",
            "Accept": "text/html,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
        return content, response.headers.get_content_type(), response.geturl()


def extract_html_document(content: bytes, source_url: str | None) -> bytes:
    """Remove the SEC <DOCUMENT>/<TEXT> envelope and add a base URL."""
    decoded = content.decode("utf-8", errors="replace")
    match = re.search(r"<html\b", decoded, re.I)
    if match:
        decoded = decoded[match.start() :]
    end = re.search(r"</html\s*>", decoded, re.I)
    if end:
        decoded = decoded[: end.end()]

    if source_url and re.search(r"<head\b[^>]*>", decoded, re.I):
        base = f'<base href="{html.escape(source_url, quote=True)}">'
        decoded = re.sub(
            r"(<head\b[^>]*>)", lambda m: m.group(1) + base, decoded, count=1, flags=re.I
        )
    return decoded.encode("utf-8")


def validate_output(path: Path, expected: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"LibreOffice did not create {path.name}")
    with path.open("rb") as stream:
        head = stream.read(8)
    if expected == "pdf" and not head.startswith(b"%PDF-"):
        raise RuntimeError(f"{path.name} is not a real PDF file")
    if expected == "docx":
        if not zipfile.is_zipfile(path):
            raise RuntimeError(f"{path.name} is not a real DOCX package")
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise RuntimeError(f"{path.name} is not a valid Word DOCX package")


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NS}}}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def ooxml_text(element: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def has_visible_table_borders(table: ET.Element) -> bool:
    for borders_name in ("tblBorders", "tcBorders"):
        for borders in table.iter(f"{W}{borders_name}"):
            for border in borders:
                value = border.get(f"{W}val", "single")
                size = border.get(f"{W}sz", "1")
                if value not in {"nil", "none"} and size != "0":
                    return True
    return False


def is_list_marker(value: str) -> bool:
    value = value.strip()
    if value in {"•", "●", "◦", "▪", "o", "-", "–", "—"}:
        return True
    return bool(
        re.fullmatch(
            r"(?:\(?[A-Za-z0-9ivxlcdmIVXLCDM]{1,8}\)?[.)]?|\d+(?:\.\d+)*\.?)",
            value,
        )
    )


def should_flatten_layout_table(table: ET.Element) -> bool:
    """Identify borderless tables used by SEC HTML only for text positioning."""
    if has_visible_table_borders(table):
        return False
    rows = table.findall(f"{W}tr")
    if not rows:
        return False
    row_cells = [row.findall(f"{W}tc") for row in rows]
    if any(not cells or len(cells) > 3 for cells in row_cells):
        return False
    if all(len(cells) == 1 for cells in row_cells):
        return True

    def row_is_layout(cells: list[ET.Element]) -> bool:
        texts = [ooxml_text(cell) for cell in cells]
        prefixes = [text for text in texts[:-1] if text]
        marker = prefixes[-1] if prefixes else ""
        return (
            not prefixes
            or is_list_marker(marker)
            or len(texts[-1]) >= 60
        )

    # A single short two-column row without a marker is commonly a signature
    # or key/value pair, so keep it as a real table.
    return all(row_is_layout(cells) for cells in row_cells)


def table_as_paragraphs(table: ET.Element) -> list[ET.Element]:
    paragraphs: list[ET.Element] = []
    for row in table.findall(f"{W}tr"):
        cells = row.findall(f"{W}tc")
        source_paragraphs: list[ET.Element] = []
        for cell in cells:
            direct = cell.findall(f"{W}p")
            source_paragraphs.extend(p for p in direct if ooxml_text(p))
        if not source_paragraphs:
            continue

        paragraph = ET.Element(f"{W}p")
        # The narrative cell normally carries the useful alignment/indentation.
        preferred = source_paragraphs[-1]
        properties = preferred.find(f"{W}pPr")
        if properties is not None:
            paragraph.append(copy.deepcopy(properties))

        added_content = False
        for source in source_paragraphs:
            content = [child for child in source if child.tag != f"{W}pPr"]
            if not content:
                continue
            if added_content:
                separator_run = ET.SubElement(paragraph, f"{W}r")
                separator = ET.SubElement(separator_run, f"{W}t")
                separator.set(XML_SPACE, "preserve")
                separator.text = " "
            for child in content:
                paragraph.append(copy.deepcopy(child))
            added_content = True
        if added_content:
            paragraphs.append(paragraph)
    return paragraphs


def flatten_layout_tables(root: ET.Element) -> int:
    parent_map = {child: parent for parent in root.iter() for child in parent}
    tables = list(root.iter(f"{W}tbl"))
    converted = 0
    # Handle nested layout tables before their containers.
    for table in reversed(tables):
        parent = parent_map.get(table)
        if parent is None or not should_flatten_layout_table(table):
            continue
        replacement = table_as_paragraphs(table)
        if not replacement:
            continue
        position = list(parent).index(table)
        parent.remove(table)
        for offset, paragraph in enumerate(replacement):
            parent.insert(position + offset, paragraph)
        converted += 1
    return converted


def normalize_docx_tables(path: Path) -> None:
    """Convert layout tables to paragraphs and fit true tables to the page.

    SEC exhibits commonly use HTML tables at 100% of the browser viewport.
    Many are only substitutes for paragraph indentation, numbering, or bullets.
    LibreOffice imports them as actual Word tables and can also let them extend
    beyond the page margins. This pass restores paragraphs where appropriate
    and keeps genuine tabular data with corrected widths.
    """
    with zipfile.ZipFile(path, "r") as source:
        document_xml = source.read("word/document.xml")
        archive_items = [(item, source.read(item.filename)) for item in source.infolist()]

    root = ET.fromstring(document_xml)
    changed = flatten_layout_tables(root) > 0
    section = root.find(f".//{W}sectPr")
    available_width = None
    if section is not None:
        page_size = section.find(f"{W}pgSz")
        margins = section.find(f"{W}pgMar")
        if page_size is not None and margins is not None:
            page_width = int(page_size.get(f"{W}w", "0"))
            left = int(margins.get(f"{W}left", "0"))
            right = int(margins.get(f"{W}right", "0"))
            if page_width > left + right:
                available_width = page_width - left - right
    for table in root.iter(f"{W}tbl") if available_width else ():
        properties = table.find(f"{W}tblPr")
        table_width = properties.find(f"{W}tblW") if properties is not None else None
        if table_width is None or table_width.get(f"{W}type") != "dxa":
            continue
        width = int(table_width.get(f"{W}w", "0"))
        if width <= available_width:
            continue
        ratio = available_width / width
        table_width.set(f"{W}w", str(available_width))

        grid = table.find(f"{W}tblGrid")
        if grid is not None:
            for column in grid.findall(f"{W}gridCol"):
                column_width = int(column.get(f"{W}w", "0"))
                if column_width:
                    column.set(f"{W}w", str(max(1, round(column_width * ratio))))

        # Only direct cells belong to this table; nested tables are normalized
        # separately when encountered by root.iter().
        for row in table.findall(f"{W}tr"):
            for cell in row.findall(f"{W}tc"):
                cell_properties = cell.find(f"{W}tcPr")
                cell_width = (
                    cell_properties.find(f"{W}tcW") if cell_properties is not None else None
                )
                if cell_width is not None and cell_width.get(f"{W}type") == "dxa":
                    value = int(cell_width.get(f"{W}w", "0"))
                    if value:
                        cell_width.set(f"{W}w", str(max(1, round(value * ratio))))
        changed = True

    if not changed:
        return

    replacement_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    temporary = path.with_suffix(".normalized.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for item, data in archive_items:
            target.writestr(item, replacement_xml if item.filename == "word/document.xml" else data)
    temporary.replace(path)
    validate_output(path, "docx")


def libreoffice_convert(
    executable: Path, source_path: Path, output_dir: Path, output_format: str
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lo-contract-profile-") as profile:
        profile_uri = Path(profile).resolve().as_uri()
        if output_format == "pdf":
            convert_to = "pdf:writer_pdf_Export"
        else:
            convert_to = "docx:Office Open XML Text"
        command = [
            str(executable),
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            convert_to,
            "--outdir",
            str(output_dir),
            str(source_path),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, timeout=180)
        generated = output_dir / f"{source_path.stem}.{output_format}"
        if completed.returncode != 0 or not generated.exists():
            details = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"LibreOffice conversion failed: {details or 'no output'}")
        validate_output(generated, output_format)
        return generated


def convert_html(
    content: bytes,
    source_url: str | None,
    stem: str,
    category_dir: Path,
    formats: list[str],
    executable: Path,
    force: bool,
) -> list[str]:
    category_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}
    requested_paths = {fmt: category_dir / f"{stem}.{fmt}" for fmt in formats}
    for fmt, path in requested_paths.items():
        if path.exists() and not force:
            validate_output(path, fmt)
            outputs[fmt] = str(path)
    if len(outputs) == len(formats):
        return [outputs[fmt] for fmt in formats]

    with tempfile.TemporaryDirectory(prefix="contract-html-") as temp_dir:
        temp_path = Path(temp_dir)
        html_path = Path(temp_dir) / f"{stem}.html"
        html_path.write_bytes(extract_html_document(content, source_url))
        existing_docx = category_dir / f"{stem}.docx"
        working_docx = temp_path / f"{stem}.docx"
        if existing_docx.exists() and not force:
            shutil.copy2(existing_docx, working_docx)
        else:
            working_docx = libreoffice_convert(executable, html_path, temp_path, "docx")
            normalize_docx_tables(working_docx)

        if "docx" in formats and "docx" not in outputs:
            final_docx = requested_paths["docx"]
            shutil.copy2(working_docx, final_docx)
            validate_output(final_docx, "docx")
            outputs["docx"] = str(final_docx)

        if "pdf" in formats and "pdf" not in outputs:
            pdf_dir = temp_path / "pdf"
            generated_pdf = libreoffice_convert(executable, working_docx, pdf_dir, "pdf")
            final_pdf = requested_paths["pdf"]
            shutil.move(str(generated_pdf), final_pdf)
            validate_output(final_pdf, "pdf")
            outputs["pdf"] = str(final_pdf)
    return [outputs[fmt] for fmt in formats]


def copy_native_document(
    content: bytes, kind: str, stem: str, category_dir: Path, formats: list[str], force: bool
) -> list[str]:
    if formats != [kind]:
        raise ValueError(
            f"source is already {kind.upper()}, but requested {', '.join(formats).upper()}; "
            "automatic PDF-to-DOCX or DOCX-to-PDF conversion is not enabled for native downloads"
        )
    category_dir.mkdir(parents=True, exist_ok=True)
    output = category_dir / f"{stem}.{kind}"
    if force or not output.exists():
        output.write_bytes(content)
    validate_output(output, kind)
    return [str(output)]


def formats_for(value: str) -> list[str]:
    return ["pdf", "docx"] if value == "both" else [value]


def process_content(
    *,
    content: bytes,
    content_type: str,
    source: str,
    resolved_url: str | None,
    category: str,
    stem: str,
    output_dir: Path,
    formats: list[str],
    executable: Path,
    force: bool,
) -> Result:
    kind = document_kind(content, content_type)
    if kind == "unknown":
        raise ValueError(f"unsupported response type {content_type or '(missing Content-Type)'}")
    category_dir = output_dir / safe_name(category, "UNCATEGORIZED").upper()
    if kind == "html":
        validate_contract_html(content, resolved_url or source)
        outputs = convert_html(
            content, resolved_url, stem, category_dir, formats, executable, force
        )
    else:
        outputs = copy_native_document(content, kind, stem, category_dir, formats, force)
    return Result(source, category, stem, "ok", outputs)


def iter_local_html(input_dir: Path) -> Iterable[tuple[str, Path]]:
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".html", ".htm"}:
            relative = path.relative_to(input_dir)
            category = relative.parts[0] if len(relative.parts) > 1 else "UNCATEGORIZED"
            yield category, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--from-html",
        type=Path,
        metavar="DIRECTORY",
        help=f"convert existing HTML files (default: {DEFAULT_INPUT_DIR})",
    )
    source.add_argument(
        "--config",
        type=Path,
        metavar="PYTHON_FILE",
        help=f"download CONTRACTS_DATA from a Python file (for example {DEFAULT_CONFIG})",
    )
    source.add_argument(
        "--url",
        action="append",
        default=[],
        metavar="CATEGORY=URL",
        help="download an explicit URL; may be repeated",
    )
    parser.add_argument("--format", choices=("pdf", "docx", "both"), default="both")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--email", help="contact email used in the SEC User-Agent")
    parser.add_argument("--user-agent", help="complete HTTP User-Agent (overrides --email)")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=0.2, help="seconds between downloads")
    parser.add_argument("--force", action="store_true", help="replace existing output files")
    parser.add_argument("--libreoffice", help="path to soffice/LibreOffice executable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    formats = formats_for(args.format)
    output_dir = args.output_dir.resolve()
    executable = find_libreoffice(args.libreoffice)
    results: list[Result] = []

    # With no source option, convert the HTML already produced by downloader.py.
    local_dir = args.from_html.resolve() if args.from_html else None
    remote_data: dict[str, list[str]] | None = None
    if args.config:
        remote_data = load_config(args.config.resolve())
    elif args.url:
        remote_data = parse_url_arguments(args.url)
    elif local_dir is None:
        local_dir = DEFAULT_INPUT_DIR

    if local_dir is not None:
        if not local_dir.is_dir():
            print(f"ERROR: input directory does not exist: {local_dir}", file=sys.stderr)
            return 2
        files = list(iter_local_html(local_dir))
        if not files:
            print(f"ERROR: no HTML files found under {local_dir}", file=sys.stderr)
            return 2
        for category, path in files:
            print(f"Converting {path} ...")
            try:
                result = process_content(
                    content=path.read_bytes(),
                    content_type="text/html",
                    source=str(path),
                    resolved_url=None,
                    category=category,
                    stem=safe_name(path.stem),
                    output_dir=output_dir,
                    formats=formats,
                    executable=executable,
                    force=args.force,
                )
                results.append(result)
                print("  OK: " + ", ".join(result.outputs))
            except Exception as error:  # Continue so one bad source does not lose the batch.
                results.append(Result(str(path), category, path.stem, "skipped", [], str(error)))
                print(f"  SKIPPED: {error}", file=sys.stderr)

    if remote_data is not None:
        user_agent = args.user_agent or (
            f"ContractsAnalysis contract downloader {args.email}" if args.email else ""
        )
        if not user_agent:
            print(
                "ERROR: remote downloads require --email you@example.com or --user-agent 'Name email'",
                file=sys.stderr,
            )
            return 2
        seen_hashes: set[str] = set()
        for category, urls in remote_data.items():
            for index, url in enumerate(urls, start=1):
                stem = f"{safe_name(category).upper()}_Template_{index}"
                print(f"Downloading {category} {index}/{len(urls)}: {url}")
                try:
                    content, content_type, resolved_url = download(url, user_agent, args.timeout)
                    digest = hashlib.sha256(content).hexdigest()
                    if digest in seen_hashes:
                        raise ValueError("duplicate response; this URL returned a page already seen")
                    seen_hashes.add(digest)
                    result = process_content(
                        content=content,
                        content_type=content_type,
                        source=url,
                        resolved_url=resolved_url,
                        category=category,
                        stem=stem,
                        output_dir=output_dir,
                        formats=formats,
                        executable=executable,
                        force=args.force,
                    )
                    results.append(result)
                    print("  OK: " + ", ".join(result.outputs))
                except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
                    results.append(Result(url, category, stem, "skipped", [], str(error)))
                    print(f"  SKIPPED: {error}", file=sys.stderr)
                time.sleep(max(0.0, args.delay))

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "conversion_manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(result) for result in results], indent=2), encoding="utf-8"
    )
    succeeded = sum(result.status == "ok" for result in results)
    skipped = len(results) - succeeded
    print(f"\nFinished: {succeeded} succeeded, {skipped} skipped")
    print(f"Manifest: {manifest_path}")
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
