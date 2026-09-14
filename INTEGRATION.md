# Integration in Open WebUI

Dieses LLM-Wiki ist ein reines Markdown-Datei-Verzeichnis. Open WebUI kann es als persönliche Wissensbasis nutzen. Der richtige Weg hängt davon ab, **was dein LLM im Chat darf**.

## Voraussetzung

- Open WebUI ist installiert und läuft.
- Du hast dieses Repo lokal geklont bzw. das Gerüst auf deiner Maschine angelegt (z. B. unter `~/llm-wiki` oder `/workspace`).

---

## Weg 0 — Mit Open Terminal (Computer-Substrat) [empfohlen]

**Open Terminal** ist Open WebUIs Computer-Substrat: ein realer Workspace mit Shell, Dateisystem und Paketmanager, den der Agent aus dem Chat ansteuert. Es vollendet das Agent-Harness — das Modell kann planen, Dateien erstellen, Code ausführen, Ausgaben prüfen und bis zu einem fertigen Artefakt weiterarbeiten. Siehe [docs.openwebui.com/features/open-terminal](https://docs.openwebui.com/features/open-terminal/).

Für das LLM-Wiki heißt das: **kein MCP, kein extra Server.** Das Modell arbeitet direkt auf dem Wiki-Verzeichnis, gesteuert durch `AGENTS.md`. Open Terminal liefert die Ausführungsebene; `AGENTS.md` die disziplinierende Anweisung, die das Modell zum Wiki-Pfleger macht.

### Voraussetzungen (laut Open-Terminal-Doku)

- Open Terminal ist in Open WebUI eingerichtet und mit einem Workspace verbunden (Docker-Sandbox *oder* bare metal, wenn direkt auf dem Host gearbeitet werden soll).
- Genutzt wird ein **fähiges Modell mit zuverlässigem Tool-Calling** — Open Terminal braucht agentic Qualität, nicht nur „unterstützt Tools". Kleine Modelle brechen oft im mehrgängigen Loop ab. Native Tool-Calling ist ab v0.10.0 Standard; prüfe den Tool-Calling-Modus des Modells, falls keine Tools feuern.

### Einrichtung

1. **Workspace bekannt machen**: lege dieses Repo (oder das Gerüst) in den Open-Terminal-Workspace, sodass `raw/`, `wiki/` und `AGENTS.md` dort liegen. (Bare metal → auf dem Host; Docker → ins Volume/Container-Verzeichnis.)
2. **System Prompt setzen**: erzeuge in Open WebUI einen neuen Agent (oder Modellanweisung) und füge den **gesamten Inhalt von `AGENTS.md`** als System Prompt ein. Damit kennt das Modell die drei Operationen (Ingest / Query / Lint), die Seitenkonventionen und den Index-/Log-Mechanismus.
3. **Open-Terminal-Tool aktivieren**: stelle sicher, dass der Agent den Terminal-/Workspace-Tool-Call nutzen darf (Shell + Dateizugriff). Ohne das fehlt ihm das Computer-Substrat.
4. **Erste Quellen ablegen**: kopiere Quelldokumente nach `raw/` (z. B. `raw/mein-artikel.md` — per Upload, Dateibrowser oder `curl` im Terminal).
5. **Im Chat natürlich ansprechen** — das Modell führt die Operationen als realen Code aus:
   - „Ingeste `raw/mein-artikel.md`" → liest die Quelle, zeigt Takeaways, schreibt `wiki/sources/…`, aktualisiert `wiki/index.md` + `wiki/log.md` über Shell/Dateizugriff.
   - „Was steht im Wiki zu …?" → liest `wiki/index.md`, dann die passenden Seiten, antwortet mit `[[Wikilink]]`-Zitaten.
   - „Linke das Wiki" → durchsucht alle Seiten, liefert Karteikarten zu Widersprüchen, verwaisten Seiten, Lücken.

### Mental-Modell: das Harness zusammen

| Rolle | Schicht |
|-------|--------|
| **Open WebUI** | Kontrollschicht: System Prompt (`AGENTS.md`), Chat, Tool-Selection, Genehmigungen |
| **Open Terminal** | Ausführungsschicht: Shell + Dateisystem — hier werden `raw/` gelesen und `wiki/` geschrieben |
| **AGENTS.md** | Anweisung, die das Modell zum geordneten Wiki-Pfleger macht (statt generischem Chatbot) |

Die Schleife ist stateful: Modell plant → schreibt/liest Dateien → beobachtet Ausgabe → korrigiert → verifiziert. Genau das braucht das Wiki, weil eine Quelle 10–15 Seiten berührt und der Agent über mehrere Gänge konsistent bleiben muss.

### Wann Open Terminal besser ist als MCP

MCP (Weg 3) brauchen nur reine Chat-Clients *ohne* Dateizugriff. Mit Open Terminal hat das Modell **vollen** Dateizugriff und kann direkt lesen/schreiben, statt über ein eingeschränktes Tool-Protokoll zu gehen. Der mitgelieferte MCP-Server (`wiki_mcp/`) bleibt als Fallback verfügbar.

---

## Weg 1 — Als Wissensbasis (Workspace) einbinden [nur Lesen+Query, kein Schreiben]

Open WebUI kennt **Workspaces** (früher „Documents"/„Knowledge"): eine Sammlung von Dateien, die das Modell bei Antworten durchsucht.

1. In Open WebUI: **Workspace → Knowledge** (oder **Documents**) öffnen.
2. **Neue Knowledge Base** anlegen, z. B. `LLM-Wiki`.
3. Die Dateien aus `wiki/` hochladen ( rekursiv: `index.md`, `log.md`, `overview.md`, `conventions.md` und alle Unterordner).
4. Beim Modell/Antwort: diese Knowledge Base auswählen → Open WebUI macht die Wiki-Seiten durchsuchbar.

**Hinweis**: Das Wiki wird so *durchsucht*, aber Open WebUI schreibt nicht zurück. Für die **Pflege** (Ingest/Lint) brauchst du Weg 2 oder 3.

**Tipp**: Lege zusätzlich eine zweite Knowledge Base `LLM-Wiki-Raw` mit `raw/` an, falls das Modell Quell- und Wiki-Ebene kombiniert beantworten soll.

---

## Weg 2 — Mit einem Agent/Skill, der Dateien schreiben darf [empfohlen für Pflege]

Damit das LLM das Wiki auch *schreibt* (Ingest, Lint), braucht es Dateizugriff. In Open WebUI über einen **Agent** mit Werkzeugen:

1. **System Prompt** für einen neuen Agent/Model: den Inhalt von `AGENTS.md` einfügen (oder per `# Datei` referenzieren, wenn dein Open-WebUI-Setup das unterstützt).
2. **Werkzeug/Tool** für Dateizugriff aktivieren:
   - Wenn Open WebUI gegen ein lokales Dateisystem läuft: ein kleines **Function-Tool/Custom-Tool** anlegen, das in `~/llm-wiki` liest/schreibt (read_file, write_file, list_dir).
   - Alternativ: das Repo als **MCP-Server** anbinden (siehe Weg 3).
3. Agent dann wie gewohnt ansprechen: „Ingeste `raw/artikel.md`", „Linke das Wiki", „Was sagt das Wiki zu X?".

So wird Open WebUI zur Wiki-IDE wie Obsidian — das Modell pflegt die Dateien, du liest und steuerst.

---

## Weg 3 — Als MCP-Server anbinden [mächtigste Variante]

Das LLM-Wiki ist nur Markdown + ein paar Skripte. Wenn du Open WebUI mit **MCP (Model Context Protocol)**-Unterstützung nutzt, baue ein kleines MCP-Server-Tool, das diese Operationen als native Tools anbietet:

- `wiki.ingest(path)` — Quelle aus `raw/` lesen, Wiki aktualisieren.
- `wiki.query(frage)` — Index lesen, relevante Seiten laden, antworten.
- `wiki.lint()` — Health-Check ausführen.
- `wiki.read(page)`, `wiki.write(page, content)`, `wiki.list()` — niedriglevelig.

Vorgehen:
1. MCP-Server implementieren (Python/Node), der auf `~/llm-wiki` operiert.
2. In Open WebUI unter **Settings → Tools / MCP** registrieren.
3. Dem Modell stehen dann die Wiki-Operationen als Tools zur Verfügung; der System Prompt aus `AGENTS.md` erklärt ihre Nutzung.

Für die Suche im wachsenden Wiki eignet sich **qmd** (lokaler BM25/Vektor-Hybrid-Suche mit LLM-Re-Ranking) — ebenfalls als CLI oder MCP-Server verfügbar.

---

## Weg 4 — Obsidian parallel (optional, zum Browsen)

Die Wiki-Ebene ist reines Markdown. Öffne das Verzeichnis `~/llm-wiki/wiki` zusätzlich in Obsidian:

- Graph-Ansicht zeigt, was mit was verbunden ist, welche Seiten Hubs oder Waisen sind.
- Backlinks pro Seite automatisch.
- Dataview-Plugin wertet das YAML-Frontmatter aus (z. B. alle Seiten mit `type: source`).
- Web-Clipper legt neue Quellen direkt in `raw/` ab.

Open WebUI pflegt → Obsidian browsen. Das entspricht genau dem Setup, das Karpathy beschreibt („Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase").

---

## Empfehlung für den Start

- **Hat dein LLM Dateizugriff/Terminal?** → **Weg 0** (direkt, kein MCP). Das ist der einfachste und mächtigste Weg.
- **Nur Lesen nötig, kein Schreiben?** → **Weg 1** (Knowledge Base).
- **Chat-Client hat keinen Dateizugriff, aber du willst pflegen?** → **Weg 2** (Agent mit Custom-Tool) oder **Weg 3** (MCP-Server, liegt bereit unter `wiki_mcp/`, konfiguriert in `mcp.json`).
- **Optional zum Browsen** → **Weg 4** (Obsidian parallel).

---

## Prüfschritte nach der Einrichtung

- [ ] Open WebUI erreicht die Wiki-Dateien (Knowledge Base zeigt Inhalt von `index.md`).
- [ ] System Prompt / `AGENTS.md` ist dem Modell bekannt (Agent fragt nach Takeaways, liest Index zuerst).
- [ ] Erster Test-Ingest: eine Datei nach `raw/` legen und „Ingeste …" — prüfen, ob `wiki/sources/`, `wiki/index.md`, `wiki/log.md` aktualisiert werden.
- [ ] Erste Query: „Was steht im Wiki zu …?" — Antwort mit `[[Wikilink]]`-Zitaten.
- [ ] Lint: „Linke das Wiki" — Karteikarten mit Widersprüchen/Lücken.
