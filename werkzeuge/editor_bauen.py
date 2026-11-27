#!/usr/bin/env python3
"""Baut die Grundriss-Werkstatt (editor/grundriss-werkstatt.html).

Bettet den Gegenstands-Katalog (mit denselben Icons wie im Buch) und den
Stadion-Fall als Beispiel in die Vorlage ein. Nach Änderungen am Katalog
einfach erneut ausführen:  python3 werkzeuge/editor_bauen.py
"""

import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from krimi.fall import lade_fall      # noqa: E402
from krimi.katalog import KATALOG     # noqa: E402


def _json(daten) -> str:
    return json.dumps(daten, ensure_ascii=False).replace("</", "<\\/")


def main():
    katalog = [{"k": o.kuerzel, "name": o.name, "besetzbar": o.besetzbar,
                "icon": " ".join(o.icon.split())} for o in KATALOG.values()]

    f = lade_fall(WURZEL / "faelle" / "01_stadion.toml")
    beispiel = {
        "n": f.n, "titel": f.titel, "ort": f.ort, "frage": f.frage, "tat": f.tat,
        "intro": " ".join(f.intro.split()), "schwierigkeit": f.schwierigkeit,
        "bereiche": [{"k": b.kuerzel, "name": b.name, "praep": b.praep, "farbe": b.farbe}
                     for b in f.bereiche.values()],
        "plan": f.plan,
        "objekte": [[o.kuerzel if o else None for o in zeile] for zeile in f.objekte],
        "personen": [{"name": p.name, "bereich": p.bereich} for p in f.personen if not p.opfer],
        "opfer": {"name": f.personen[-1].name, "bereich": f.personen[-1].bereich},
        "eigene": [],
    }

    vorlage = (WURZEL / "werkzeuge" / "editor_vorlage.html").read_text(encoding="utf-8")
    html = vorlage.replace("__KATALOG__", _json(katalog)).replace("__BEISPIEL__", _json(beispiel))
    ziel = WURZEL / "editor" / "grundriss-werkstatt.html"
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text(html, encoding="utf-8")
    print(f"Geschrieben: {ziel} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
