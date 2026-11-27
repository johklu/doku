#!/usr/bin/env python3
"""Baut aus Fall-Dateien ein druckfertiges PDF.

Beispiele:
    python3 baue.py faelle/01_stadion.toml
    python3 baue.py faelle/*.toml -o ausgabe/buch.pdf
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from krimi.druck import buch_html
from krimi.fall import lade_fall
from krimi.generator import erzeuge

WURZEL = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("faelle", nargs="+", help="TOML-Dateien unter faelle/")
    ap.add_argument("-o", "--ausgabe", default=None, help="Ziel-PDF")
    ap.add_argument("--versuche", type=int, default=40, help="Generator-Versuche je Fall")
    ap.add_argument("--vorschau", action="store_true", help="zusätzlich PNG je Seite")
    args = ap.parse_args()

    raetsel = []
    for pfad in args.faelle:
        fall = lade_fall(pfad)
        print(f"Fall {fall.nummer:02d}: {fall.titel}")
        r = erzeuge(fall, versuche=args.versuche)
        print(f"  -> Täter: {fall.personen[r.taeter].name}, "
              f"{len(r.hinweise)} Hinweise, {r.proben} Proben")
        for i, h in enumerate(r.hinweise, 1):
            print(f"     {i:2d}. {h.text(fall)}")
        raetsel.append(r)

    ausgabe = Path(args.ausgabe) if args.ausgabe else (
        WURZEL / "ausgabe" / (Path(args.faelle[0]).stem + ".pdf"))
    ausgabe.parent.mkdir(parents=True, exist_ok=True)
    html_pfad = ausgabe.with_suffix(".html")
    html_pfad.write_text(buch_html(raetsel), encoding="utf-8")

    # Lösungen zusätzlich als JSON festhalten (zum Nachprüfen)
    protokoll = [{
        "fall": r.fall.nummer, "titel": r.fall.titel,
        "taeter": r.fall.personen[r.taeter].name,
        "positionen": {r.fall.personen[p].name: r.fall.koordinate(z) for p, z in r.loesung.items()},
        "hinweise": [h.text(r.fall) for h in r.hinweise],
        "proben": r.proben,
    } for r in raetsel]
    ausgabe.with_suffix(".json").write_text(json.dumps(protokoll, ensure_ascii=False, indent=2),
                                            encoding="utf-8")

    cmd = ["node", str(WURZEL / "werkzeuge" / "pdf.cjs"), str(html_pfad), str(ausgabe)]
    if args.vorschau:
        cmd.append(str(ausgabe.parent / (ausgabe.stem + "_vorschau")))
    subprocess.run(cmd, check=True)
    print(f"Fertig: {ausgabe}")


if __name__ == "__main__":
    sys.exit(main())
