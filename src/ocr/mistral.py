import asyncio
import base64
import os

from mistralai import Mistral

from src.pdf.extractor import ExtractionResult


def _count_markdown_tables(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("|") and "---" in line)


async def extract_ocr(content: bytes, page_count: int) -> ExtractionResult:
    def _call() -> object:
        client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        b64 = base64.b64encode(content).decode()
        return client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{b64}",
            },
        )

    try:
        response = await asyncio.to_thread(_call)
    except Exception as exc:
        raise RuntimeError(f"Mistral OCR API error : {exc}") from exc

    pages = getattr(response, "pages", [])
    parts: list[str] = []

    for i, page in enumerate(pages):
        if i > 0:
            parts.append(f"<!-- page:{i + 1} -->")
        md = getattr(page, "markdown", "") or ""
        if md.strip():
            parts.append(md.strip())

    content_markdown = "\n\n".join(p for p in parts if p)

    return ExtractionResult(
        content_markdown=content_markdown,
        is_scanned=True,
        page_count=len(pages) or page_count,
        tables_detected=_count_markdown_tables(content_markdown),
    )
