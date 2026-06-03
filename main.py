import hmac
import os

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile

from src.blossom.gateway import save_raw_document
from src.ocr.mistral import extract_ocr
from src.pdf.extractor import extract_pdf

app = FastAPI()


def _auth(provided: str | None) -> bool:
    expected = os.environ.get("EXTRACT_SECRET", "")
    return bool(expected) and hmac.compare_digest(provided or "", expected)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract")
async def extract(
    pdf_binary: UploadFile = File(...),
    dossier_id: str = Form(...),
    filename: str = Form(...),
    user_id: str = Form(...),
    x_extract_secret: str | None = Header(None),
) -> dict:
    if not _auth(x_extract_secret):
        raise HTTPException(status_code=401, detail="unauthorized")

    content = await pdf_binary.read()

    try:
        result = extract_pdf(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if result.is_scanned:
        try:
            result = await extract_ocr(content, result.page_count)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    try:
        document_id = await save_raw_document(
            dossier_id=dossier_id,
            file_name=filename,
            user_id=user_id,
            content_markdown=result.content_markdown,
            is_scanned=result.is_scanned,
            page_count=result.page_count,
            tables_detected=result.tables_detected,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "document_id": document_id,
        "content_markdown": result.content_markdown,
        "is_scanned": result.is_scanned,
        "page_count": result.page_count,
        "tables_detected": result.tables_detected,
    }
