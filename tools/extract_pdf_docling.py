#!/usr/bin/env python3
"""
PDF -> Markdown-Extraktion ueber eine docling-serve REST-API.

Anders als eine lokale Docling-Installation ruft dieses Skript einen laufenden
docling-serve-Service (FastAPI, Defaultport 5001) auf und laedt die PDF als
multipart/form-data hoch. Damit laufen Layout-, Tabellen-, OCR- und
Bildbeschreibungs-Modelle serverseitig — inkl. optionaler VLM-Anbindung
(z. B. Ollama/llava) ueber `picture_description_api`.

Nutzung:
    python tools/extract_pdf_docling.py raw/beispiel.pdf > raw/beispiel.md
    DOCLING_SERVE_URL=http://docling:5001 python tools/extract_pdf_docling.py raw/x.pdf > raw/x.md
    python tools/extract_pdf_docling.py raw/x.pdf --config tools/docling_pipeline.json > raw/x.md
    python tools/extract_pdf_docling.py raw/x.pdf --fallback > raw/x.md   # pypdf, wenn kein Service

Konfiguration (Pipeline-Optionen):
    Standard ist die projektspezifische Pipeline (tools/docling_pipeline.json):
    OCR an, dlparse_v4-Backend, accurate-Tabellen, Tesseract/de,
    Bildbeschreibung via Ollama (llava:latest), Formel-Anreicherung.
    Ueberschreibbar via --config <datei.json> oder Umgebungsvariablen
    DOCLING_SERVE_URL (Service-URL) und DOCLING_SERVE_API_KEY (X-Api-Key).

Hinweis: `picture_description_api` (remote VLM) ist ab docling-serve v1.21.0
deprecated zugunsten von `picture_description_custom_config`, funktioniert aber
weiter. Fuer die Bildbeschreibung muss der docling-serve mit
DOCLING_SERVE_ENABLE_REMOTE_SERVICES=true gestartet sein.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_PIPELINE_CONFIG: dict = {
    "do_ocr": True,
    "pdf_backend": "dlparse_v4",
    "table_mode": "accurate",
    "ocr_engine": "tesseract",
    "ocr_lang": ["de"],
    "do_picture_description": True,
    "picture_description_api": json.dumps({
        "url": "http://ollama:11434/v1/chat/completions",
        "params": {"model": "llava:latest"},
        "timeout": 60,
        "prompt": "Describe this image in great detail.",
    }),
    "do_formula_enrichment": True,
}


def _stringify(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _build_multipart(fields: list[tuple[str, str]], file_field: str,
                      file_name: str, file_bytes: bytes,
                      file_mime: str) -> tuple[bytes, str]:
    boundary = "----llm-wiki-docling-boundary-f9beaa"
    crlf = "\r\n"
    parts: list[bytes] = []
    for name, value in fields:
        parts.append(
            f"--{boundary}{crlf}"
            f'Content-Disposition: form-data; name="{name}"{crlf}{crlf}'
            f"{value}{crlf}".encode("utf-8")
        )
    parts.append(
        f"--{boundary}{crlf}"
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{file_name}"{crlf}'
        f"Content-Type: {file_mime}{crlf}{crlf}".encode("utf-8")
    )
    parts.append(file_bytes)
    parts.append(f"{crlf}--{boundary}--{crlf}".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def extract_via_api(pdf_path: Path, config: dict, base_url: str,
                    api_key: str | None, timeout: float) -> str:
    url = base_url.rstrip("/") + "/v1/convert/file"
    sys.stderr.write(f"Docling-API: POST {url}\n")

    fields: list[tuple[str, str]] = [
        ("from_formats", "pdf"),
        ("to_formats", "md"),
    ]
    for key, value in config.items():
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                fields.append((key, _stringify(item)))
        else:
            fields.append((key, _stringify(value)))

    mime = mimetypes.guess_type(str(pdf_path))[0] or "application/pdf"
    body, content_type = _build_multipart(
        fields, "files", pdf_path.name, pdf_path.read_bytes(), mime,
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": content_type,
    }
    if api_key:
        headers["X-Api-Key"] = api_key

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        sys.stderr.write(f"Docling-API-Fehler {e.code}: {detail}\n")
        sys.exit(3)
    except urllib.error.URLError as e:
        sys.stderr.write(
            f"Docling-Service nicht erreichbar ({base_url}): {e.reason}\n"
            "URL via DOCLING_SERVE_URL setzen; fuer reinen Text-Layer --fallback.\n"
        )
        sys.exit(4)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Antwort nicht als JSON parsbar: {e}\n")
        sys.exit(5)

    document = payload.get("document") or {}
    md = document.get("md_content")
    if not md:
        sys.stderr.write(
            "Antwort enthaelt kein document.md_content. "
            f"Status: {payload.get('status')}, errors: {payload.get('errors')}\n"
        )
        sys.exit(6)
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


def load_config(config_path: Path | None) -> dict:
    if config_path:
        return json.loads(config_path.read_text(encoding="utf-8"))
    local = Path(__file__).resolve().parent / "docling_pipeline.json"
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    return dict(DEFAULT_PIPELINE_CONFIG)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF -> Markdown ueber eine docling-serve REST-API.",
    )
    parser.add_argument("pdf", help="Pfad zur PDF-Datei")
    parser.add_argument(
        "--config", metavar="DATEI",
        help="JSON-Datei mit Pipeline-Optionen (Default: tools/docling_pipeline.json).",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("DOCLING_SERVE_URL", "http://localhost:5001"),
        help="docling-serve Basis-URL (Env: DOCLING_SERVE_URL).",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DOCLING_SERVE_API_KEY"),
        help="X-Api-Key bei aktivierter Auth (Env: DOCLING_SERVE_API_KEY).",
    )
    parser.add_argument(
        "--timeout", type=float, default=600.0,
        help="HTTP-Timeout in Sekunden (OCR/VLM dauern laenger).",
    )
    parser.add_argument(
        "--fallback", action="store_true",
        help="pypdf statt API verwenden (reiner Text-Layer, kein Layout/OCR).",
    )
    args = parser.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        sys.stderr.write(f"Nicht gefunden: {pdf}\n")
        sys.exit(1)

    if args.fallback:
        sys.stderr.write("Verwende pypdf (Fallback, reiner Text-Layer).\n")
        sys.stdout.write(extract_with_pypdf(pdf))
        return

    config = load_config(Path(args.config) if args.config else None)
    sys.stdout.write(
        extract_via_api(pdf, config, args.url, args.api_key, args.timeout)
    )


if __name__ == "__main__":
    main()
