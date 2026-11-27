#!/usr/bin/env python3
"""Baut aus Fall-Dateien ein druckfertiges PDF.

Beispiele:
    python3 baue.py faelle/01_stadion.toml
    python3 baue.py faelle/*.toml -o ausgabe/buch.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import subprocess
import sys
from pathlib import Path

from krimi import archiv
from krimi.druck import buch_html
from krimi.fall import lade_fall
from krimi.generator import erzeuge

WURZEL = Path(__file__).resolve().parent
CACHE = WURZEL / ".cache"


def erzeuge_mit_cache(pfad: str, versuche: int):
    """Fertige Rätsel werden zwischengespeichert. Neu gerechnet wird nur, wenn
    sich die Fall-Datei, die Versuchszahl oder der Generator-Code ändert."""
    h = hashlib.sha256(Path(pfad).read_bytes())
    h.update(str(versuche).encode())
    for quelle in sorted((WURZEL / "krimi").glob("*.py")):
        if quelle.name != "druck.py":           # Layout-Änderungen ändern das Rätsel nicht
            h.update(quelle.read_bytes())
    datei = CACHE / f"{Path(pfad).stem}-{h.hexdigest()[:16]}.pickle"
    fall = lade_fall(pfad)
    if datei.exists():
        r = pickle.loads(datei.read_bytes())
        r.fall = fall                            # Texte/Stil frisch aus der Datei
        print("  (aus dem Zwischenspeicher)")
        return r
    r = erzeuge(fall, versuche=versuche)
    CACHE.mkdir(exist_ok=True)
    datei.write_bytes(pickle.dumps(r))
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("faelle", nargs="+", help="TOML-Dateien unter faelle/")
    ap.add_argument("-o", "--ausgabe", default=None, help="Ziel-PDF")
    ap.add_argument("--versuche", type=int, default=30, help="Generator-Versuche je Fall")
    ap.add_argument("--vorschau", action="store_true", help="zusätzlich PNG je Seite")
    ap.add_argument("--speichern", action="store_true",
                    help="Rätsel abnehmen: dauerhaft als faelle/<name>.raetsel.json einfrieren")
    ap.add_argument("--neu", action="store_true",
                    help="eingefrorenes Rätsel ignorieren und neu erzeugen")
    args = ap.parse_args()

    raetsel = []
    for pfad in args.faelle:
        fall = lade_fall(pfad)
        print(f"Fall {fall.nummer:02d}: {fall.titel}")
        if archiv.archiv_pfad(pfad).exists() and not args.neu:
            r = archiv.lade(fall, pfad)
            print(f"  (eingefroren: {archiv.archiv_pfad(pfad).name} – geprüft, eindeutig)")
        else:
            r = erzeuge_mit_cache(pfad, args.versuche)
        if args.speichern:
            print(f"  gespeichert als {archiv.speichere(r, pfad)}")
        print(f"  -> Übeltäter: {fall.personen[r.taeter].name}, "
              f"{len(r.hinweise)} Hinweise, {r.proben} Proben")
        for h in r.hinweise:
            print(f"     - {r.text(h)}")
        print("  Lösungsweg:")
        for i, s in enumerate(r.schritte, 1):
            print(f"     {i:2d}. {s}")
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
        "hinweise": [r.text(h) for h in r.hinweise],
        "proben": r.proben,
        "loesungsweg": r.schritte,
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
