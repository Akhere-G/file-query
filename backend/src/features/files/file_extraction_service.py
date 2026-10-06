import csv
import io
import subprocess
from typing import cast

import fitz
import pymupdf4llm
from docx import Document


def extract_text(file: bytes) -> str:
    return file.decode("utf-8")


def extract_csv(file: bytes) -> str:
    content = file.decode("utf-8")
    reader = csv.reader(io.StringIO(content))

    rows = []

    for row in reader:
        cleaned_row = [cell.strip() for cell in row]

        if any(cleaned_row):
            rows.append(" | ".join(cleaned_row))

    return "\n\n".join(rows)


def extract_pdf(file: bytes) -> str:
    document = fitz.open(stream=file, filetype="pdf")

    text = cast(
        str,
        pymupdf4llm.to_markdown(
            document,
            write_images=False,
            embed_images=False,
        ),
    )

    document.close()

    return text.strip()


def extract_docx(file: bytes) -> str:
    document = Document(io.BytesIO(file))
    text = []

    for paragraph in document.paragraphs:
        paragraph_text = paragraph.text.strip()

        if not paragraph_text:
            continue

        style_name = paragraph.style.name if paragraph.style else None

        if style_name and style_name.startswith("Heading"):
            level = style_name.replace("Heading ", "")
            text.append(f"{'#' * int(level)} {paragraph_text}")
        else:
            text.append(paragraph_text)

    for table in document.tables:
        for row in table.rows:
            text.append(" | ".join(cell.text.strip() for cell in row.cells))

    return "\n\n".join(text)


def extract_doc(file: bytes) -> str:
    result = subprocess.run(
        ["antiword", "-"],
        input=file,
        capture_output=True,
        check=True,
    )

    return result.stdout.decode("utf-8").strip()


EXTRACTION_METHODS = {
    "text/plain": extract_text,
    "text/markdown": extract_text,
    "text/csv": extract_csv,
    "application/pdf": extract_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_docx,
    "application/msword": extract_doc,
}


def extract_file(file: bytes, mime_type: str) -> str:
    extraction_method = EXTRACTION_METHODS.get(mime_type)

    if not extraction_method:
        raise ValueError(f"Unsupported file type: {mime_type}")

    return extraction_method(file)
