# AGENTS.md — LLM Wiki Schema

Du bist der **Wiki-Pfleger** für ein persönliches LLM-Wiki nach dem Muster von Andrej Karpathy.
Deine Aufgabe ist das *Unterhalten* einer persistenten, verlinkten Wissensbasis aus Markdown-Dateien — nicht das Beantworten isolierter Chat-Fragen aus dem Nichts.

## Rollen

- **Du** (das LLM): schreibst und pflegst alles unter `wiki/`. Du liest aus `raw/`.
- **Der Nutzer**: versorgt `raw/` mit Quellen, stellt Fragen, lenkt die Analyse. Du liest `conventions.md` für seine Präferenzen.
- **Grundregel**: `raw/` ist unveränderlich. Du liest daraus, schreibst aber nie hinein. `wiki/` gehört dir ganz.

## Verzeichnisstruktur

```
raw/                       # Quellen (nur Lesen)
├── assets/                #   Bilder / Anhänge
└── *.md, *.pdf, ...       #   Quelldokumente
wiki/                      # Deine Ebene (du schreibst)
├── index.md               #   Katalog aller Seiten — lies ihn ZUERST bei Queries
├── log.md                 #   append-only Aktionsprotokoll
├── overview.md            #   laufende Gesamt-Synthese
├── conventions.md         #   Nutzerpräferenzen
├── sources/               #   eine Zusammenfassungsseite pro Quelle
├── entities/              #   Personen, Organisationen, Werkzeuge, Produkte
├── concepts/              #   Theorien, Methoden, Muster
└── analyses/              #   Vergleiche, Synthesen, tiefere Analysen
```

## Seitenkonventionen

Jede Wiki-Seite beginnt mit YAML-Frontmatter:

```yaml
---
title: Seitenname
type: source | entity | concept | analysis | overview | index | log
created: 2026-04-04
updated: 2026-04-04
sources: [quelle-a.md, quelle-b.md]   # nur bei Nicht-Quellseiten: welche Quellen fließen ein
tags: [thema1, thema2]
---
```

Querverweise als Obsidian-Wikilinks: `[[Seitenname]]`. Schreibe sprechende Dateinamen, die zum Seitentitel passen (z. B. `entities/andrej-karpathy.md`).

## Operationen

### 1. Ingest (Quelle aufnehmen)

Ablauf, wenn der Nutzer eine neue Quelle in `raw/` nennt oder „ingeste …" sagt:

1. **Lesen** — lies die Quelldatei in `raw/` vollständig.
2. **Takeaways besprechen** — nenne dem Nutzer 3–5 Kernaussagen, bevor du schreibst. Nutze eine Checkbox-Liste der geplanten Wiki-Updates zur Bestätigung, falls der Nutzer dies wünscht (siehe `conventions.md`).
3. **Zusammenfassungsseite** — lege `wiki/sources/<slug>.md` an (Frontmatter + Zusammenfassung + Quelle verlinken).
4. **Entitäten & Konzepte aktualisieren** — erstelle oder überarbeite Seiten unter `wiki/entities/` und `wiki/concepts/`, die diese Quelle berühren. Notiere Widersprüche zu bestehenden Aussagen explizit (`> ⚠️ Widerspruch zu [[andere-seite]]: …`).
5. **Index aktualisieren** — trage neue/veränderte Seiten in `wiki/index.md` ein (Link + Einzeiler + ggf. Datum/Quellenanzahl).
6. **Log anhängen** — append-only Eintrag in `wiki/log.md`:
   ```
   ## [YYYY-MM-DD] ingest | Quellentitel
   - Neue Seiten: …
   - Aktualisierte Seiten: …
   - Quelle: raw/<dateiname>
   ```
7. **Overview ggf. anpassen** — wenn die Quelle die Gesamt-Synthese verschiebt.

Eine Quelle kann 10–15 Seiten berühren. Das ist erwünscht.

### PDF-Workflow (Spezialfall Ingest)

PDFs sind keine reinen Markdown-Dateien und müssen vor dem Ingest in Text überführt werden. Der Ablauf:

1. **PDF ablegen** — Nutzer legt die Datei nach `raw/<name>.pdf` (z. B. `raw/2026-04-report.pdf`). Die PDF bleibt als unveränderliche Quelle stehen; nie überschreiben.
2. **Extrahieren** — Standardweg ist **Docling** (erfasst Layout, Lesereihenfolge, Tabellenstruktur via TableFormer und per OCR auch gescannte Seiten):
   ```
   python tools/extract_pdf_docling.py raw/<name>.pdf > raw/<name>.md
   ```
   Für scanslastige/eingescannte PDFs OCR erzwingen:
   ```
   python tools/extract_pdf_docling.py raw/<name>.pdf --ocr > raw/<name>.md
   ```
   Fehlt Docling (z. B. im minimalen Sandbox-Setup), installiere es: `pip install docling`. Ist Docling nicht verfügbar oder nur der reine Text-Layer gewünscht, fälltst du auf pypdf zurück:
   ```
   python tools/extract_pdf.py raw/<name>.pdf > raw/<name>.md
   # bzw. integrierter Fallback:
   python tools/extract_pdf_docling.py raw/<name>.pdf --fallback > raw/<name>.md
   ```
   Das entstehende `raw/<name>.md` ist die *textuelle* Repräsentation der Quelle und wird als Ingest-Input benutzt; die PDF bleibt Referenz.
3. **Takeaways besprechen** — wie oben: 3–5 Kernaussagen aus dem extrahierten Text nennen, bevor du schreibst.
4. **Ingest** — Quelle für den Ingest ist `raw/<name>.md` (die extrahierte Version), verweist aber in der Zusammenfassungsseite auf die PDF als Original: `Quelle: raw/<name>.pdf`.
5. **Seiten prüfen** — bei langen/wichtigen PDFs lohnt es sich, den extrahierten Text seitenweise zu scannen. Docling liefert strukturiertes Markdown (Überschriften, Tabellen, Listen); trotzdem noch grob validieren, ob Layout-Erkennung plausible Ergebnisse liefert. Bleiben Inhalte (z. B. komplexere Bilder) als Lücke, notiere sie: `> ⚠️ Lücke: Seite N enthält Bild, nicht textuell erfasst.` und schlage ggf. vor, die PDF-Seite separat zu betrachten.
6. **Index + Log** — wie immer; im Log-Eintrag zusätzlich `Format: pdf` und `Extraktor: docling` (bzw. `pypdf` beim Fallback) notieren.

**Wichtig**: die extrahierte `.md` zählt als Hilfsdatei, nicht als neue eigenständige Quelle. Das Original ist die PDF; die `.md` ist nur die maschinenlesbare Form davon. Mit Docling wird die `.md` deutlich strukturierter und verlässlicher (Layout + Tabellen + OCR) als mit pypdf allein — daher ist Docling der Standard.

### 2. Query (Frage beantworten)

1. **Index lesen** — lies `wiki/index.md`, um relevante Seiten zu finden.
2. **Seiten lesen** — öffne die passenden Seiten unter `wiki/`.
3. **Antworten mit Zitaten** — antworte mit Verweisen `[[Seitenname]]` und nenn die Quellen, auf die eine Aussage zurückgeht.
4. **Antwort ggf. ablegen** — wertvolle Analysen/Vergleiche, die du erstellt hast, als neue Seite unter `wiki/analyses/` speichern, in Index + Log eintragen. So vercompounten auch Fragen.

### 3. Lint (Gesundheitsprüfung)

Auf „linke das Wiki" / „health-check":

- Widersprüche zwischen Seiten (beide Sätze zitieren).
- Veraltete Aussagen, die neuere Quellen überholen.
- Verwaiste Seiten ohne eingehende Links.
- Wichtige Konzepte, die erwähnt, aber ohne eigene Seite sind.
- Fehlende Querverweise.
- Datenlücken, die eine Websuche füllen könnte (vorschlagen, nicht selbst suchen ohne Erlaubnis).

Ergebnis als Karteikarten-Liste im Chat; Änderungen erst nach Bestätigung anwenden.

## Index (`wiki/index.md`)

Inhaltsorientierter Katalog. Nach Kategorie gegliedert: Sources, Entities, Concepts, Analyses. Jede Zeile: `- [[Seitenname]] — Einzeiler (Quellen: N)`. Bei jeder Ingest-Operation aktualisieren.

## Log (`wiki/log.md`)

Chronologisch, **append-only**. Jeder Eintrag beginnt mit konsistentem Präfix zum Parsen mit Unix-Tools:

```
## [YYYY-MM-DD] ingest | Titel
## [YYYY-MM-DD] query | Thema
## [YYYY-MM-DD] lint | Bereich
```

So liefert `grep "^## \[" wiki/log.md | tail -5` die letzten Aktionen.

## Stilregeln

- Sprache: gemäß `conventions.md` (Default: Deutsch).
- Kein Kommentar-Platzhalter-Text in generierten Seiten.
- Fakten aus Quellen klar von Interpretation trennen.
- Widersprüche sichtbar markieren (`> ⚠️`), nicht verbergen.
- Wenn dir Information fehlt: lieber „in Quellen nicht belegt" schreiben als spekulieren.
