import base64
import os

import httpx

from src.pdf.extractor import ExtractionResult

MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"


def _count_markdown_tables(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("|") and "---" in line)


async def extract_ocr(content: bytes, page_count: int) -> ExtractionResult:
    api_key = os.environ["MISTRAL_API_KEY"]
    b64 = base64.b64encode(content).decode()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                MISTRAL_OCR_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-ocr-latest",
                    "document": {
                        "type": "document_url",
                        "document_url": f"data:application/pdf;base64,{b64}",
                    },
                },
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Mistral OCR API {exc.response.status_code}: {exc.response.text}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Mistral OCR API injoignable : {exc}") from exc

    data = resp.json()
    pages = data.get("pages", [])

    parts: list[str] = []
    for i, page in enumerate(pages):
        if i > 0:
            parts.append(f"<!-- page:{i + 1} -->")
        md = page.get("markdown", "") or ""
        if md.strip():
            parts.append(md.strip())

    content_markdown = "\n\n".join(p for p in parts if p)

    return ExtractionResult(
        content_markdown=content_markdown,
        is_scanned=True,
        page_count=len(pages) or page_count,
        tables_detected=_count_markdown_tables(content_markdown),
    )
