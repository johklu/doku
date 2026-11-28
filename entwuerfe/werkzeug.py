"""Hilfen für handgemachte Rätsel: Plan anzeigen, Hinweise prüfen, einfrieren."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from krimi import hinweise as H                     # noqa: E402
from krimi.archiv import speichere                  # noqa: E402
from krimi.fall import lade_fall                    # noqa: E402
from krimi.generator import Raetsel                 # noqa: E402
from krimi.logik import Logik                       # noqa: E402
from krimi.loeser import finde_loesungen            # noqa: E402

SP = "ABCDEFGHIJKL"


def zelle(k: str):
    return (int(k[1:]) - 1, SP.index(k[0]))


def zeige(fall):
    print("    " + "  ".join(f"{SP[c]:>3}" for c in range(fall.n)))
    for r in range(fall.n):
        teile = []
        for c in range(fall.n):
            o = fall.objekt((r, c))
            t = (o.kuerzel if o else "..")
            t = t if fall.besetzbar((r, c)) else t.lower() + "x"
            teile.append(f"{fall.bereich((r, c))}:{t:<3}")
        print(f"{r + 1:>2}  " + " ".join(teile))


def pruefe(fall, hinweise, zeigen=True):
    loes = finde_loesungen(fall, hinweise, limit=20)
    l = Logik(fall, hinweise, protokoll=False)
    try:
        l.propagiere()
        ohne = [sorted(fall.koordinate(z) for z in d) for d in l.D]
    except Exception as e:                     # Widerspruch
        ohne = str(e)
    l2 = Logik(fall, hinweise, protokoll=False)
    erg = l2.loese()
    if zeigen:
        print(f"Lösungen: {len(loes)}{'+' if len(loes) == 20 else ''}  "
              f"logisch: {'ja' if erg else 'nein'}, Proben {l2.proben}, Kette {l2.max_kette}")
        if isinstance(ohne, list):
            for p, d in enumerate(ohne):
                print(f"   {fall.personen[p].name:<11} {' '.join(d)}")
    return loes, l2


def friere_ein(fall_pfad, fall, hinweise, texte, schritte):
    loes = finde_loesungen(fall, hinweise, limit=2)
    assert len(loes) == 1, f"{len(loes)} Lösungen"
    r = Raetsel(fall, loes[0], hinweise, 0, schritte)
    for h, t in zip(hinweise, texte):
        r.texte[id(h)] = t
    l = Logik(fall, hinweise, protokoll=False)
    l.loese()
    r.proben = l.proben
    return speichere(r, fall_pfad)
