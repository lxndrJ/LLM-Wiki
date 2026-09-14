"""
LLM-Wiki MCP-Server.

Bietet die Wiki-Operationen als Tools über das Model Context Protocol (stdio-Transport)
an, damit Open WebUI (oder ein anderer MCP-Client) das Wiki lesen und pflegen kann.

Start:
    python -m wiki_mcp

Der Wiki-Root liegt per Default im aktuellen Arbeitsverzeichnis (..).
Überschreibbar via Umgebungsvariable WIKI_ROOT.
"""
from __future__ import annotations

import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

WIKI_ROOT = Path(os.environ.get("WIKI_ROOT", Path(__file__).resolve().parent.parent)).resolve()
RAW_DIR = WIKI_ROOT / "raw"
WIKI_DIR = WIKI_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"

SLUG_RE = re.compile(r"[^a-z0-9]+")
TODAY = date.today().isoformat()


def _slug(title: str) -> str:
    return SLUG_RE.sub("-", title.lower()).strip("-") or "eintrag"


def _relative(p: Path) -> str:
    try:
        return str(p.relative_to(WIKI_ROOT))
    except ValueError:
        return str(p)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _ensure_dirs() -> None:
    for d in (RAW_DIR, RAW_DIR / "assets", WIKI_DIR,
             WIKI_DIR / "sources", WIKI_DIR / "entities",
             WIKI_DIR / "concepts", WIKI_DIR / "analyses"):
        d.mkdir(parents=True, exist_ok=True)


def _list_wiki_pages() -> list[str]:
    if not WIKI_DIR.exists():
        return []
    return [_relative(p) for p in sorted(WIKI_DIR.rglob("*.md"))]


def _append_log(kind: str, title: str, lines: list[str]) -> None:
    entry = f"## [{TODAY}] {kind} | {title}\n" + "".join(f"- {l}\n" for l in lines) + "\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


def _update_index(new_pages: list[str]) -> None:
    if not INDEX_FILE.exists():
        return
    body = _read(INDEX_FILE)
    for rel in new_pages:
        name = Path(rel).stem
        line = f"- [[{name}]] — neu ({TODAY})"
        section = None
        if rel.startswith("wiki/sources/"):
            section = "## Sources"
        elif rel.startswith("wiki/entities/"):
            section = "## Entities"
        elif rel.startswith("wiki/concepts/"):
            section = "## Concepts"
        elif rel.startswith("wiki/analyses/"):
            section = "## Analyses"
        if section and section in body:
            placeholder = "_Noch keine"
            if placeholder in body.split(section, 1)[1].split("##", 1)[0]:
                body = body.replace(
                    body.split(section, 1)[1].split("##", 1)[0].strip().splitlines()[0],
                    line,
                )
            else:
                body = body.replace(section, section + "\n" + line, 1)
    INDEX_FILE.write_text(body, encoding="utf-8")


mcp = MCPServer("llm-wiki")


@mcp.tool()
def wiki_list() -> str:
    """Alle Wiki-Seiten auflisten (Pfade relativ zum Wiki-Root)."""
    pages = _list_wiki_pages()
    return "\n".join(pages) if pages else "(leer — noch keine Seiten)"


@mcp.tool()
def wiki_read(page: str) -> str:
    """Eine Wiki-Seite lesen. `page` ist ein relativer Pfad (z. B. 'wiki/index.md') oder ein Seitenslug/titel."""
    p = _resolve_page(page)
    if not p or not p.exists():
        return f"Nicht gefunden: {page}"
    return _read(p)


@mcp.tool()
def wiki_write(page: str, content: str) -> str:
    """Eine Wiki-Seite schreiben/überschreiben. `page` ist ein relativer Pfad unter wiki/ (z. B. 'wiki/entities/foo.md').
    Legt fehlende Verzeichnisse an. Aktualisiert NICHT automatisch Index/Log — für Ingest wiki.ingest verwenden."""
    if not page.startswith("wiki/"):
        return "Fehler: Seite muss unter wiki/ liegen (z. B. 'wiki/entities/foo.md')."
    p = (WIKI_ROOT / page).resolve()
    if WIKI_ROOT not in p.parents and p != WIKI_DIR:
        return "Fehler: Pfad darf das Wiki-Verzeichnis nicht verlassen."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Geschrieben: {_relative(p)}"


@mcp.tool()
def wiki_ingest(source: str, summary: str, entities: list[str] | None = None,
                concepts: list[str] | None = None) -> str:
    """Eine Quelle aufnehmen: legt eine Zusammenfassungsseite unter wiki/sources/ an,
    erstellt/verlinkt Entitäts-/Konzept-Seed-Seiten, aktualisiert Index und Log.
    `source`: relativer Pfad unter raw/ (z. B. 'raw/artikel.md').
    `summary`: Zusammenfassungstext der Quelle.
    `entities`/`concepts`: optionale Listen von Seitennamen, die (als Stub) angelegt/verlinkt werden sollen."""
    _ensure_dirs()
    src = (WIKI_ROOT / source).resolve()
    if not src.exists():
        return f"Quelle nicht gefunden: {source}"
    if RAW_DIR not in src.parents and src.parent != RAW_DIR:
        return "Fehler: Quelle muss unter raw/ liegen."

    slug = _slug(src.stem)
    summary_page = WIKI_DIR / "sources" / f"{slug}.md"
    content = f"""---
title: {src.stem}
type: source
created: {TODAY}
updated: {TODAY}
source: {source}
tags: []
---

# {src.stem}

{summary}

## Quelle
- `{source}`

"""
    summary_page.write_text(content, encoding="utf-8")
    created = [_relative(summary_page)]

    def _stub(name: str, sub: str) -> str:
        s = _slug(name)
        path = WIKI_DIR / sub / f"{s}.md"
        body = f"""---
title: {name}
type: {sub[:-1]}
created: {TODAY}
updated: {TODAY}
sources: [{src.name}]
tags: []
---

# {name}

Stub — wird mit weiteren Quellen ausgefüllt.

Siehe auch: [[{slug}]]
"""
        if not path.exists():
            path.write_text(body, encoding="utf-8")
            created.append(_relative(path))
        return s

    ent_links = [f"[[{_stub(e, 'entities')}]]" for e in (entities or [])]
    con_links = [f"[[{_stub(c, 'concepts')}]]" for c in (concepts or [])]

    full = summary_page.read_text(encoding="utf-8")
    if ent_links:
        full += f"\n## Entitäten\n{', '.join(ent_links)}\n"
    if con_links:
        full += f"\n## Konzepte\n{', '.join(con_links)}\n"
    summary_page.write_text(full, encoding="utf-8")

    _update_index(created)
    _append_log("ingest", src.stem,
               [f"Neue Seiten: {', '.join(created)}",
                f"Quelle: {source}"])
    return f"Ingested: {source}\nNeue/berührte Seiten:\n" + "\n".join(created)


@mcp.tool()
def wiki_query(question: str) -> str:
    """Frage ans Wiki: liest den Index, sucht nach passenden Seitennamen/Tags
    und liefert die Trefferseiten zurück, damit das Modell sie synthetisieren kann.
    Gibt eine kompakte Trefferliste mit Seitenauszügen zurück."""
    if not INDEX_FILE.exists():
        return "Index fehlt — Wiki noch nicht initialisiert."
    index = _read(INDEX_FILE)
    keywords = [w.lower() for w in question.split() if len(w) > 3]
    pages = [p for p in (WIKI_DIR.rglob("*.md")) if p.name not in ("index.md", "log.md")]
    scored = []
    for p in pages:
        text = _read(p).lower()
        score = sum(text.count(k) for k in keywords) + sum(
            2 for k in keywords if k in p.stem.lower())
        if score > 0:
            scored.append((score, p))
    scored.sort(reverse=True)
    top = scored[:5]
    if not top:
        return f"Keine Treffer für: {question}\n\nIndex:\n{index}"
    out = [f"Treffer für: {question}", ""]
    for score, p in top:
        snippet = _read(p).split("\n", 15)
        out.append(f"### {_relative(p)} (score {score})")
        out.append("\n".join(snippet[:14]))
        out.append("")
    return "\n".join(out)


@mcp.tool()
def wiki_lint() -> str:
    """Einfacher Health-Check des Wikis: findet verwaiste Seiten (ohne eingehende Links),
    leere Stub-Seiten und Seiten, die im Index fehlen. Gibt eine Karteikarten-Liste zurück."""
    if not WIKI_DIR.exists():
        return "Wiki-Verzeichnis fehlt."
    pages = list(WIKI_DIR.rglob("*.md"))
    names = {p.stem: p for p in pages if p.name not in ("index.md", "log.md")}
    text_blob = "\n".join(_read(p) for p in pages)

    orphans = [n for n, p in names.items() if f"[[{n}]]" not in text_blob.replace(f"[[{n}]]", "", 1) and f"[[{n}" not in _read(p)]
    stubs = [n for n, p in names.items() if "Stub —" in _read(p)]
    in_index = set(re.findall(r"\[\[(.+?)\]\]", _read(INDEX_FILE))) if INDEX_FILE.exists() else set()
    missing_index = [n for n in names if n not in in_index]

    cards = ["# Lint-Ergebnisse", ""]
    cards.append("## Verwaiste Seiten (kein eingehender Link)")
    cards.extend(f"- {n}" for n in orphans) or cards.append("- (keine)")
    cards.append("")
    cards.append("## Stub-Seiten (ausbaufähig)")
    cards.extend(f"- {n}" for n in stubs) or cards.append("- (keine)")
    cards.append("")
    cards.append("## Im Index fehlende Seiten")
    cards.extend(f"- {n}" for n in missing_index) or cards.append("- (keine)")
    _append_log("lint", "wiki", [f"Orphans: {len(orphans)}", f"Stubs: {len(stubs)}", f"Im Index fehlend: {len(missing_index)}"])
    return "\n".join(cards)


@mcp.tool()
def wiki_search(query: str, limit: int = 10) -> str:
    """Einfache BM25-ähnliche Suche über alle Wiki-Seiten (ohne externe Abhängigkeit).
    Liefert gerankte Pfade mit Score."""
    pages = [p for p in WIKI_DIR.rglob("*.md")] if WIKI_DIR.exists() else []
    if not pages:
        return "(leer)"
    q_terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
    if not q_terms:
        return "Query zu kurz."
    results = []
    for p in pages:
        text = _read(p).lower()
        tf = sum(text.count(t) for t in q_terms)
        if tf:
            results.append((tf, _relative(p)))
    results.sort(reverse=True)
    return "\n".join(f"{s}\t{p}" for s, p in results[:limit]) or "Keine Treffer."


def _resolve_page(page: str) -> Path | None:
    candidates = []
    p = Path(page)
    if not p.is_absolute():
        candidates.append(WIKI_ROOT / p)
        candidates.append(WIKI_DIR / p)
        candidates.append(WIKI_DIR / f"{page}.md")
        candidates.append(WIKI_DIR / "entities" / f"{page}.md")
        candidates.append(WIKI_DIR / "concepts" / f"{page}.md")
        candidates.append(WIKI_DIR / "sources" / f"{page}.md")
        candidates.append(WIKI_DIR / "analyses" / f"{page}.md")
    else:
        candidates.append(p)
    for c in candidates:
        c = c.resolve()
        if c.exists() and c.is_file():
            return c
    by_stem = [pp for pp in (WIKI_DIR.rglob("*.md") if WIKI_DIR.exists() else []) if pp.stem.lower() == page.lower()]
    if by_stem:
        return by_stem[0]
    return None


def main() -> None:
    _ensure_dirs()
    mcp.run()


if __name__ == "__main__":
    main()
