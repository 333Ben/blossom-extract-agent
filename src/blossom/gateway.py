import os

import httpx


async def save_raw_document(
    dossier_id: str,
    file_name: str,
    user_id: str,
    content_markdown: str,
    is_scanned: bool,
    page_count: int,
    tables_detected: int,
) -> str:
    """Calls agent-gateway save_raw_document. Returns raw_document_id."""
    url = os.environ["AGENT_GATEWAY_URL"]
    secret = os.environ["AGENT_GATEWAY_SECRET"]
    extraction_source = "mistral-ocr" if is_scanned else "pymupdf+pdfplumber"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            headers={"x-agent-secret": secret, "Content-Type": "application/json"},
            json={
                "action": "save_raw_document",
                "dossier_id": dossier_id,
                "file_name": file_name,
                "content_markdown": content_markdown,
                "is_scanned": is_scanned,
                "page_count": page_count,
                "tables_detected": tables_detected,
                "uploaded_by": user_id,
                "extraction_source": extraction_source,
                "provenance": "extract-agent",
            },
        )

    if resp.status_code != 200:
        raise RuntimeError(f"agent-gateway {resp.status_code}: {resp.text}")

    return resp.json()["raw_document_id"]
