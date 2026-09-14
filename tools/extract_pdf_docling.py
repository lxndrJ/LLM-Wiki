#!/usr/bin/env python3
"""
PDF -> Markdown-Extraktion mit Docling für das LLM-Wiki.

Docling erfasst — anders als reiner Text-Layer — Layout, Lesereihenfolge,
Tabellenstruktur (TableFormer) und per OCR auch eingescannte Seiten.
Damit werden PDFs als saubere `.md` ingestbar, die das Wiki direkt verwerten kann.

Nutzung (durch den Agenten im Open-Terminal-Workspace):
    python tools/extract_pdf_docling.py raw/beispiel.pdf > raw/beispiel.md
    python tools/extract_pdf_docling.py raw/beispiel.pdf --ocr          # OCR erzwingen
    python tools/extract_pdf_docling.py raw/beispiel.pdf --fallback      # pypdf, wenn Docling fehlt

Abhängigkeit (wird vom Agenten bei Bedarf installiert):
    pip install docling

Fehlt Docling, bricht das Skript mit Hinweis ab — außer mit --fallback, dann
wird tools/extract_pdf.py (pypdf) verwendet.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def extract_with_docling(pdf_path: Path, force_ocr: bool) -> str:
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import PdfFormatOption
    except ImportError:
        sys.stderr.write(
            "docling fehlt. Installiere mit:  pip install docling\n"
            "Für reine Text-Extraktion ohne Docling:  --fallback (pypdf)\n"
        )
        sys.exit(2)

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    if force_ocr:
        pipeline_options.ocr_options.force_full_page_ocr = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        },
    )
    result = converter.convert(str(pdf_path))
    md = result.document.export_to_markdown()

    return f"# {pdf_path.stem}\n\n{md}\n"


def extract_with_pypdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.stderr.write("pypdf fehlt. Installiere mit:  pip install pypdf\n")
        sys.exit(2)

    reader = PdfReader(str(pdf_path))
    parts = [f"# {pdf_path.stem}", ""]
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(f"## Seite {i}\n\n{text}\n")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF -> Markdown mit Docling (Layout, Tabellen, OCR).",
    )
    parser.add_argument("pdf", help="Pfad zur PDF-Datei")
    parser.add_argument(
        "--ocr", action="store_true",
        help="OCR erzwingen (force_full_page_ocr) — für gescannte/scanslastige PDFs.",
    )
    parser.add_argument(
        "--fallback", action="store_true",
        help="pypdf statt Docling verwenden (reiner Text-Layer, keine Layout-/OCR-Fähigkeit).",
    )
    args = parser.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        sys.stderr.write(f"Nicht gefunden: {pdf}\n")
        sys.exit(1)

    if args.fallback:
        sys.stderr.write("Verwende pypdf (Fallback, reiner Text-Layer).\n")
        sys.stdout.write(extract_with_pypdf(pdf))
    else:
        sys.stderr.write("Verwende Docling (Layout, Tabellen, OCR).\n")
        sys.stdout.write(extract_with_docling(pdf, force_ocr=args.ocr))


if __name__ == "__main__":
    main()
