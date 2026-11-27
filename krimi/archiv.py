"""Fertige Rätsel dauerhaft speichern ("einfrieren") und wieder laden.

Ein abgenommenes Rätsel liegt neben seiner Fall-Datei als
`faelle/<name>.raetsel.json`. Darin stehen Lösung, Hinweise (als Struktur UND
als fertiger Satz) und der Lösungsweg. Beim Bauen wird es nicht neu erzeugt,
sondern nur geprüft: Gilt jeder Hinweis noch, und ist die Lösung weiterhin
eindeutig? So bleibt ein Rätsel exakt so, wie es abgenommen wurde – auch wenn
der Generator später verbessert wird.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import hinweise as H
from .fall import Fall
from .generator import Raetsel
from .loeser import finde_loesungen

# Konstruktor-Argumente je Hinweis-Typ (p/q sind Personen, werden als Namen gespeichert)
ARGUMENTE = {
    "ImBereich": ["p", "b"], "NichtImBereich": ["p", "b"],
    "AufObjekt": ["p", "k"], "NebenObjekt": ["p", "k"], "NichtNebenObjekt": ["p", "k"],
    "AmRand": ["p", "ja"], "Allein": ["p"],
    "GleicherBereich": ["p", "q"], "AndererBereich": ["p", "q"], "Schraeg": ["p", "q"],
    "Links": ["p", "q", "umgekehrt"], "Oben": ["p", "q", "umgekehrt"],
}


def archiv_pfad(fall_pfad: str | Path) -> Path:
    p = Path(fall_pfad)
    return p.with_name(p.stem + ".raetsel.json")


def _hinweis_zu_dict(fall: Fall, h: H.Hinweis) -> dict:
    typ = type(h).__name__
    if typ == "Kombi":
        return {"typ": typ, "a": _hinweis_zu_dict(fall, h.a), "b": _hinweis_zu_dict(fall, h.b)}
    d = {"typ": typ}
    for arg in ARGUMENTE[typ]:
        wert = getattr(h, arg)
        d[arg] = fall.personen[wert].name if arg in ("p", "q") else wert
    return d


def _hinweis_aus_dict(fall: Fall, d: dict) -> H.Hinweis:
    if d["typ"] == "Kombi":
        return H.Kombi(_hinweis_aus_dict(fall, d["a"]), _hinweis_aus_dict(fall, d["b"]))
    index = {p.name: i for i, p in enumerate(fall.personen)}
    args = [index[d[a]] if a in ("p", "q") else d[a] for a in ARGUMENTE[d["typ"]]]
    return getattr(H, d["typ"])(*args)


def speichere(r: Raetsel, fall_pfad: str | Path) -> Path:
    f = r.fall
    daten = {
        "fall": Path(fall_pfad).name,
        "titel": f.titel,
        "gespeichert": date.today().isoformat(),
        "uebeltaeter": f.personen[r.taeter].name,
        "loesung": {f.personen[p].name: f.koordinate(z) for p, z in sorted(r.loesung.items())},
        "proben": r.proben,
        "hinweise": [dict(_hinweis_zu_dict(f, h), text=r.text(h)) for h in r.hinweise],
        "loesungsweg": r.schritte,
    }
    ziel = archiv_pfad(fall_pfad)
    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ziel


def _zelle(koord: str):
    return (int(koord[1:]) - 1, "ABCDEFGHIJKL".index(koord[0]))


def lade(fall: Fall, fall_pfad: str | Path) -> Raetsel:
    pfad = archiv_pfad(fall_pfad)
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    index = {p.name: i for i, p in enumerate(fall.personen)}
    try:
        loesung = {index[name]: _zelle(k) for name, k in daten["loesung"].items()}
        hinweise = [_hinweis_aus_dict(fall, d) for d in daten["hinweise"]]
    except KeyError as e:
        raise ValueError(f"{pfad.name}: passt nicht mehr zur Fall-Datei ({e} unbekannt). "
                         f"Wurde ein Name geändert?") from e

    # Prüfen, ob das eingefrorene Rätsel zur (evtl. geänderten) Fall-Datei passt
    falsch = [d["text"] for h, d in zip(hinweise, daten["hinweise"]) if not h.gilt(fall, loesung)]
    if falsch:
        raise ValueError(f"{pfad.name}: Diese Hinweise stimmen mit der Fall-Datei nicht mehr: "
                         + "; ".join(falsch))
    gefunden = finde_loesungen(fall, hinweise)
    if gefunden != [loesung]:
        raise ValueError(f"{pfad.name}: Das Rätsel ist mit der aktuellen Fall-Datei nicht mehr "
                         f"eindeutig lösbar. Datei löschen, um es neu zu erzeugen.")

    texte = {id(h): d["text"] for h, d in zip(hinweise, daten["hinweise"])}
    return Raetsel(fall, loesung, hinweise, daten["proben"], list(daten["loesungsweg"]), texte)
