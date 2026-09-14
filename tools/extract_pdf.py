#!/usr/bin/env python3
"""
PDF -> Markdown-Extraktion für das LLM-Wiki.

Nutzung (durch den Agenten im Open-Terminal-Workspace):
    python tools/extract_pdf.py raw/beispiel.pdf > raw/beispiel.md

Erzeugt sauberen UTF-8-Text mit Seitenumbrüchen als Markdown.
Falls Bilder/Tabellen wichtig sind, ist das nur die Textebene —
ggf. seitenweise prüfen (siehe AGENTS.md, PDF-Workflow).

Abhängigkeit (wird vom Agenten bei Bedarf installiert):
    pip install pypdf
"""
from __future__ import annotations

import sys
from pathlib import Path


def extract(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.stderr.write(
            "pypdf fehlt. Installiere mit:  pip install pypdf\n"
        )
        sys.exit(2)

    reader = PdfReader(str(pdf_path))
    parts = [f"# {pdf_path.stem}", ""]
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(f"## Seite {i}\n\n{text}\n")
    return "\n".join(parts)


def main() -> None:
    if len(sys.argv) != 2:
        sys.stderr.write("Nutzung: extract_pdf.py <pfad/zur/datei.pdf>\n")
        sys.exit(1)
    pdf = Path(sys.argv[1])
    if not pdf.exists():
        sys.stderr.write(f"Nicht gefunden: {pdf}\n")
        sys.exit(1)
    sys.stdout.write(extract(pdf))


if __name__ == "__main__":
    main()
