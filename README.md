# Rätselbuch

Generator für eigene Logik-Rätsel auf einem Raster: Personen auf einen
Grundriss setzen (eine pro Zeile und Spalte), Hinweise auswerten und den
Übeltäter finden – wer hat dem „Opfer“ diesmal was angetan? Das Ergebnis ist ein druckfertiges PDF (A4) mit Spielregeln,
Rätselseiten und Lösungen. Nur für den privaten Gebrauch.

## Benutzung

```bash
python3 baue.py faelle/01_stadion.toml --vorschau
```

Ergebnis: `ausgabe/01_stadion.pdf` (dazu ein `.json` mit Lösung und Hinweisen,
mit `--vorschau` zusätzlich PNG-Bilder jeder Seite).

Mehrere Fälle zu einem Buch:

```bash
python3 baue.py faelle/*.toml -o ausgabe/buch.pdf
```

Voraussetzungen: Python ≥ 3.11 und Node mit Playwright/Chromium (für den PDF-Export).

## Einen neuen Fall anlegen

Am einfachsten mit der **Grundriss-Werkstatt** (`editor/grundriss-werkstatt.html`,
im Browser öffnen): Bereiche malen, Gegenstände setzen, Personen eintragen,
Text kopieren und als `.toml` unter `faelle/` speichern. Die Werkstatt prüft
schon beim Malen, ob der Plan aufgehen kann. Nach Änderungen am Katalog neu
erzeugen mit `python3 werkzeuge/editor_bauen.py`.

Oder eine Datei in `faelle/` kopieren und von Hand anpassen:

* `plan` – ein Buchstabe pro Feld, welcher Bereich (Raum) das ist
* `objekte` – ein Kürzel pro Feld (`..` = frei), siehe `krimi/katalog.py`
* `personen` / `opfer` – Namen und in welchem Bereich sie laut Lösung waren
* `schwierigkeit` – `leicht`, `mittel` oder `schwer`
* `seed` – ein anderer Wert ergibt ein anderes Rätsel auf demselben Plan
* `frage` / `tat` – die Prämisse, z. B. „Wer hat X mit Kölsch beworfen?“ /
  „hat X mit Kölsch beworfen“
* `[stil]` – Akzentfarbe, Textfarbe, Titel- und Textschrift dieses Falls
* `[gegenstaende]` – eigene Gegenstände nur für diesen Fall
  (`Kr = { name = "Krippe", genus = "f", besetzbar = true, verb = "lag in" }`)

Jede verdächtige Person bekommt **genau einen Hinweis**. Der Generator wählt
eine Aufstellung, sammelt je Person alle wahren Aussagen und tauscht so lange
aus, bis die sieben Hinweise zusammen

1. genau **eine** Lösung ergeben (exakter Löser) und
2. sich **ohne Raten** lösen lassen (logischer Löser; die Zahl der nötigen
   kurzen „Was wäre wenn“-Proben bestimmt die Schwierigkeit).

Regeln für die Hinweise: „neben“ gilt nur innerhalb desselben Bereichs (wer
auf der Tribüne steht, ist nie „neben dem Tor“), keine Aussage kommt doppelt
vor, und jede Satzform höchstens zweimal.

Der logische Löser schreibt dabei den **Lösungsweg** mit, der hinten bei den
Lösungen abgedruckt wird. Fertige Rätsel landen in `.cache/` – ein erneuter
Bau ist dann in einer Sekunde fertig, solange Fall-Datei und Generator gleich
bleiben (reine Layout-Änderungen erzwingen keine Neuberechnung).

## Aufbau

| Datei | Inhalt |
|---|---|
| `krimi/katalog.py` | Gegenstände (Name, Grammatik, besetzbar?, Icon) |
| `krimi/fall.py` | Fall-Datei laden, Geometrie |
| `krimi/hinweise.py` | Hinweis-Typen und ihre deutschen Sätze |
| `krimi/loeser.py` | exakter Löser (Eindeutigkeit) |
| `krimi/logik.py` | logischer Löser mit Lösungsweg-Protokoll |
| `krimi/generator.py` | Rätsel erzeugen und bewerten |
| `krimi/druck.py` | Seiten-Layout (HTML/SVG) |
| `werkzeuge/pdf.cjs` | HTML → PDF über Chromium |
| `schriften/` | Special Elite (Apache 2.0), Crimson Pro (OFL) |
