import io
import pdfplumber


def extract_tables_pdfplumber(content: bytes) -> dict[int, list[list[list]]]:
    """Returns {page_index: [table, ...]} where each table is list of rows (list of cells)."""
    result: dict[int, list[list[list]]] = {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            result[i] = tables or []
    return result
