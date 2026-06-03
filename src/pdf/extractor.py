import fitz  # PyMuPDF — import fitz, not pymupdf
from dataclasses import dataclass

from src.pdf.fallback import extract_tables_pdfplumber

SCAN_THRESHOLD = 50  # avg chars per page below this → scanned PDF


@dataclass
class ExtractionResult:
    content_markdown: str
    is_scanned: bool
    page_count: int
    tables_detected: int


def _table_to_markdown(rows: list[list]) -> str:
    if not rows:
        return ""
    # Filter entirely empty rows
    rows = [r for r in rows if any(c is not None and str(c).strip() for c in r)]
    if not rows:
        return ""

    def cell(v: object) -> str:
        return str(v).strip().replace("|", "\\|") if v is not None else ""

    col_count = max(len(r) for r in rows)
    header = rows[0]
    padded_header = list(header) + [None] * (col_count - len(header))

    lines = ["| " + " | ".join(cell(c) for c in padded_header) + " |"]
    lines.append("|" + "|".join("---" for _ in padded_header) + "|")
    for row in rows[1:]:
        padded = list(row) + [None] * (col_count - len(row))
        lines.append("| " + " | ".join(cell(c) for c in padded[:col_count]) + " |")
    return "\n".join(lines)


def _table_key(md: str) -> str:
    return "".join(md.split()).lower()


def _count_markdown_tables(text: str) -> int:
    # Each table has exactly one separator row (|---|)
    return sum(1 for line in text.splitlines() if line.startswith("|") and "---" in line)


def extract_pdf(content: bytes) -> ExtractionResult:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"PDF illisible : {exc}") from exc

    page_count = len(doc)

    # Scan detection: average chars on first 5 pages
    sample = min(5, page_count)
    total_chars = sum(len(doc[i].get_text()) for i in range(sample))
    avg_chars = total_chars / sample if sample > 0 else 0
    is_scanned = avg_chars < SCAN_THRESHOLD

    if is_scanned:
        doc.close()
        return ExtractionResult("", True, page_count, 0)

    # Extract page texts and fitz tables
    page_texts: list[str] = []
    fitz_tables: dict[int, list[list[list]]] = {}

    for i in range(page_count):
        page = doc[i]
        page_texts.append(page.get_text("text").strip())
        found = page.find_tables()
        fitz_tables[i] = [tab.extract() for tab in found.tables] if found else []

    doc.close()

    # Extract pdfplumber tables (always — merge and dedup with fitz)
    plumber_tables = extract_tables_pdfplumber(content)

    # Build content_markdown page by page
    parts: list[str] = []
    total_tables = 0

    for i in range(page_count):
        if i > 0:
            parts.append(f"<!-- page:{i + 1} -->")

        # Merge tables from both sources, deduplicate by normalized content
        seen: set[str] = set()
        merged_mds: list[str] = []

        for rows in fitz_tables.get(i, []):
            md = _table_to_markdown(rows)
            if md:
                key = _table_key(md)
                if key not in seen:
                    seen.add(key)
                    merged_mds.append(md)

        for rows in plumber_tables.get(i, []):
            md = _table_to_markdown(rows)
            if md:
                key = _table_key(md)
                if key not in seen:
                    seen.add(key)
                    merged_mds.append(md)

        total_tables += len(merged_mds)

        if page_texts[i]:
            parts.append(page_texts[i])
        for md in merged_mds:
            parts.append(md)

    content_markdown = "\n\n".join(p for p in parts if p)

    return ExtractionResult(
        content_markdown=content_markdown,
        is_scanned=False,
        page_count=page_count,
        tables_detected=total_tables,
    )
