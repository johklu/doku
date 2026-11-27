# Mordsrätsel

Generator für eigene Logik-Krimirätsel auf einem Raster: Personen auf einen
Grundriss setzen (eine pro Zeile und Spalte), Hinweise auswerten, den Täter
finden. Das Ergebnis ist ein druckfertiges PDF (A4) mit Spielregeln,
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

Eine Datei in `faelle/` kopieren und anpassen:

* `plan` – ein Buchstabe pro Feld, welcher Bereich (Raum) das ist
* `objekte` – ein Kürzel pro Feld (`..` = frei), siehe `krimi/katalog.py`
* `personen` / `opfer` – Namen und in welchem Bereich sie laut Lösung waren
* `schwierigkeit` – `leicht`, `mittel` oder `schwer`
* `seed` – ein anderer Wert ergibt ein anderes Rätsel auf demselben Plan

Der Generator wählt eine Aufstellung, sammelt alle wahren Aussagen dazu und
streicht so lange Hinweise, bis ein knapper Satz übrig bleibt, der

1. genau **eine** Lösung hat (exakter Löser) und
2. sich **ohne Raten** lösen lässt (logischer Löser, die Zahl der nötigen
   „Was wäre wenn“-Proben bestimmt die Schwierigkeit).

## Aufbau

| Datei | Inhalt |
|---|---|
| `krimi/katalog.py` | Gegenstände (Name, Grammatik, besetzbar?, Icon) |
| `krimi/fall.py` | Fall-Datei laden, Geometrie |
| `krimi/hinweise.py` | Hinweis-Typen und ihre deutschen Sätze |
| `krimi/loeser.py` | exakter und logischer Löser |
| `krimi/generator.py` | Rätsel erzeugen und bewerten |
| `krimi/druck.py` | Seiten-Layout (HTML/SVG) |
| `werkzeuge/pdf.cjs` | HTML → PDF über Chromium |
| `schriften/` | Special Elite (Apache 2.0), Crimson Pro (OFL) |
