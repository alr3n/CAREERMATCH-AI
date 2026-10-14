"""Builders for synthetic test documents (no real personal data)."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from docx import Document

FIXTURES = Path(__file__).parent / "fixtures"


def resume_text() -> str:
    return (FIXTURES / "synthetic_resume.txt").read_text(encoding="utf-8")


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    lines = text.split("\n")
    for start in range(0, len(lines), 45):
        page = doc.new_page()
        y = 50
        for line in lines[start : start + 45]:
            page.insert_text((40, y), line, fontsize=10)
            y += 15
    data = doc.tobytes()
    doc.close()
    return data


def make_image_only_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200), False)
    pix.clear_with(200)
    page.insert_image(fitz.Rect(50, 50, 250, 250), pixmap=pix)
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(text: str) -> bytes:
    document = Document()
    for line in text.split("\n"):
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
