# LLM Wiki

Ein persönliches, persistentes Wissensbasis-System nach dem [LLM-Wiki-Muster von Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Statt bei jeder Frage Wissen aus Rohdokumenten neu abzuleiten (klassisches RAG), baut und pflegt das LLM inkrementell ein strukturiertes, verlinktes Wiki aus Markdown-Dateien. Das Wissen wird einmal kompiliert und dann aktuell gehalten — es wächst mit jeder Quelle und jeder Frage.

## Architektur (drei Schichten)

| Schicht | Ort | Wer schreibt | Wer liest | Inhalt |
|---------|-----|-------------|-----------|--------|
| **Rohe Quellen** | `raw/` | Du | LLM | Artikel, Paper, Notizen, PDFs, Bilder |
| **Wiki** | `wiki/` | LLM | Du | Zusammenfassungen, Entitäten, Konzepte, Analysen, Querverweise |
| **Schema** | `AGENTS.md` | Du + LLM | LLM | Struktur, Konventionen, Workflows |

## Schnellstart

1. Quelle in `raw/` ablegen (z. B. `raw/mein-artikel.md`).
2. Dem LLM sagen: „Ingeste `raw/mein-artikel.md`" (oder natürlich: „Nimm diesen Artikel auf").
3. LLM liest, bespricht Takeaways, schreibt eine Zusammenfassungsseite, aktualisiert Index und relevante Entitäts-/Konzeptseiten, hängt einen Eintrag ans Log an.
4. Fragen stellen: „Was ist der Unterschied zwischen X und Y?" → LLM sucht im Index, liest Seiten, antwortet mit Zitaten.

Integration in Open WebUI: siehe [`INTEGRATION.md`](./INTEGRATION.md).

## Verzeichnisstruktur

```
.
├── AGENTS.md              # Schema / Konfiguration für das LLM
├── INTEGRATION.md          # Anleitung zur Integration in Open WebUI
├── README.md              # Diese Datei
├── raw/                   # Rohe Quellen (unveränderlich, du schreibst)
│   ├── assets/            #   Bilder und Anhänge
│   └── *.md / *.pdf       #   Quelldokumente
└── wiki/                  # LLM-generiertes und -gepflegtes Wiki
    ├── index.md           #   Inhaltsorientierter Katalog aller Seiten
    ├── log.md             #   Chronologisches, append-only Aktionsprotokoll
    ├── overview.md        #   Gesamtdüberblick / laufende Synthese
    ├── conventions.md     #   Nutzungspräferenzen (deine Vorgaben ans LLM)
    ├── sources/           #   Zusammenfassungsseiten pro Quelle
    ├── entities/          #   Entitäten (Personen, Organisationen, Werkzeuge)
    ├── concepts/         #   Konzepte (Theorien, Methoden, Muster)
    └── analyses/          #   Analysen (Vergleiche, Synthesen)
```

## Lizenz

Dieses Gerüst folgt dem öffentlichen Muster von A. Karpathy. Frei verwendbar.
