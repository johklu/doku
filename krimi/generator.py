"""Generator: erzeugt aus einem Fall (Plan + Personen) ein lösbares Rätsel.

Ablauf
  1. Eine zufällige Lösung wählen, die zu den vorgegebenen Bereichen der
     Personen passt (jede Zeile/Spalte genau eine Person).
  2. Alle Aussagen sammeln, die für diese Lösung wahr sind (großer Pool).
  3. Hinweise nacheinander streichen – langweilige zuerst –, solange das
     Rätsel eindeutig UND ohne Raten lösbar bleibt.
  4. Das mehrfach mit verschiedenen Zufallswerten machen und das beste
     Ergebnis (passende Länge und Schwierigkeit) nehmen.
"""

from __future__ import annotations

import itertools
import random
from collections import Counter
from dataclasses import dataclass

from .fall import Fall, Zelle
from .hinweise import (AmRand, AndererBereich, AufObjekt, Allein, GleicherBereich,
                       Hinweis, ImBereich, Links, NebenObjekt, NichtImBereich,
                       NichtNebenObjekt, Niemand, Oben, Schraeg)
from .loeser import finde_loesungen, loese_logisch

# Ziele je Schwierigkeitsgrad: (min Proben, max Proben, ideale Hinweisanzahl)
ZIELE = {
    "leicht": (0, 0, 12),
    "mittel": (1, 4, 11),
    "schwer": (3, 12, 9),
}


@dataclass
class Raetsel:
    fall: Fall
    loesung: dict[int, Zelle]
    hinweise: list[Hinweis]
    proben: int

    @property
    def taeter(self) -> int:
        f = self.fall
        b = f.bereich(self.loesung[f.opfer_index])
        return next(p for p, z in self.loesung.items()
                    if p != f.opfer_index and f.bereich(z) == b)


def alle_aufstellungen(fall: Fall) -> list[dict[int, Zelle]]:
    """Alle Aufstellungen, bei denen jede Person in ihrem Bereich steht."""
    n = fall.n
    soll = Counter(p.bereich for p in fall.personen)
    nach_bereich: dict[str, list[int]] = {}
    for i, p in enumerate(fall.personen):
        nach_bereich.setdefault(p.bereich, []).append(i)

    ergebnis = []
    for perm in itertools.permutations(range(n)):
        zellen = [(r, perm[r]) for r in range(n)]
        if not all(fall.besetzbar(z) for z in zellen):
            continue
        if Counter(fall.bereich(z) for z in zellen) != soll:
            continue
        ergebnis.append(zellen)

    aufstellungen = []
    for zellen in ergebnis:
        je_bereich: dict[str, list[Zelle]] = {}
        for z in zellen:
            je_bereich.setdefault(fall.bereich(z), []).append(z)
        # alle Zuordnungen Personen -> Zellen innerhalb der Bereiche
        teile = []
        for b, personen in nach_bereich.items():
            teile.append([(personen, perm) for perm in itertools.permutations(je_bereich[b])])
        for kombi in itertools.product(*teile):
            pos = {}
            for personen, zs in kombi:
                pos.update(zip(personen, zs))
            aufstellungen.append(pos)
    return aufstellungen


def hinweis_pool(fall: Fall, pos: dict[int, Zelle], rng: random.Random) -> list[Hinweis]:
    P = len(fall.personen)
    v = fall.opfer_index
    verdaechtige = [p for p in range(P) if p != v]
    arten = sorted({fall.objekt(z).kuerzel for z in fall.zellen() if fall.objekt(z)})
    pool: list[Hinweis] = []

    for p in verdaechtige:
        z = pos[p]
        b = fall.bereich(z)
        pool.append(ImBereich(p, b))
        for andere in fall.bereiche:
            if andere != b:
                pool.append(NichtImBereich(p, andere))
        o = fall.objekt(z)
        if o is not None:
            pool.append(AufObjekt(p, o.kuerzel))
        nachbar_arten = {fall.objekt(nz).kuerzel for nz in fall.nachbarn4(z) if fall.objekt(nz)}
        for k in nachbar_arten:
            h = NebenObjekt(p, k)
            if fall.anzahl_objekt(k) >= 8:      # "neben einem Sitz" ist fast nichtssagend
                h.prio = 2
            pool.append(h)
        # "nicht neben X" nur, wenn X im eigenen Bereich überhaupt eine Rolle spielt
        relevant = {fall.objekt(nz).kuerzel
                    for bz in fall.bereichs_zellen(b) if fall.besetzbar(bz)
                    for nz in fall.nachbarn4(bz) if fall.objekt(nz)}
        for k in sorted(relevant - nachbar_arten):
            pool.append(NichtNebenObjekt(p, k))
        rand = z[0] in (0, fall.n - 1) or z[1] in (0, fall.n - 1)
        pool.append(AmRand(p, rand))
        if sum(1 for q in range(P) if fall.bereich(pos[q]) == b) == 1:
            pool.append(Allein(p))

    for p, q in itertools.combinations(verdaechtige, 2):
        zp, zq = pos[p], pos[q]
        a, b = (p, q) if zp[1] < zq[1] else (q, p)
        pool.append(Links(a, b, umgekehrt=rng.random() < 0.4))
        a, b = (p, q) if zp[0] < zq[0] else (q, p)
        pool.append(Oben(a, b, umgekehrt=rng.random() < 0.4))
        if abs(zp[0] - zq[0]) == 1 and abs(zp[1] - zq[1]) == 1:
            pool.append(Schraeg(p, q))
        if fall.bereich(zp) == fall.bereich(zq):
            pool.append(GleicherBereich(p, q))
        else:
            pool.append(AndererBereich(p, q))

    belegt = {fall.objekt(z).kuerzel for z in pos.values() if fall.objekt(z)}
    for k in arten:
        from .katalog import KATALOG
        if KATALOG[k].besetzbar and k not in belegt:
            pool.append(Niemand(k, P))

    assert all(h.gilt(fall, pos) for h in pool)
    return pool


def _erwaehnt(hinweise, p) -> int:
    return sum(1 for h in hinweise if p in h.personen and not isinstance(h, Niemand))


def reduziere(fall: Fall, pool: list[Hinweis], rng: random.Random, max_proben: int):
    """Streicht Hinweise, solange das Rätsel eindeutig und logisch lösbar bleibt."""
    if len(finde_loesungen(fall, pool)) != 1:
        return None
    reihenfolge = sorted(pool, key=lambda h: h.prio + rng.random() * 2.5)
    aktiv = list(pool)
    v = fall.opfer_index
    for h in reihenfolge:
        # Jede verdächtige Person soll mindestens einmal vorkommen.
        if any(p != v and _erwaehnt(aktiv, p) == 1 for p in h.personen
               if not isinstance(h, Niemand)):
            continue
        probe = [x for x in aktiv if x is not h]
        if len(finde_loesungen(fall, probe)) != 1:
            continue
        loesung, proben = loese_logisch(fall, probe, max_proben=max_proben)
        if loesung is None or proben > max_proben:
            continue
        aktiv = probe
    loesung, proben = loese_logisch(fall, aktiv, max_proben=max_proben)
    return aktiv, proben


def _bewertung(hinweise: list[Hinweis], proben: int, ziel) -> float:
    min_p, max_p, ideal = ziel
    s = abs(len(hinweise) - ideal) * 2.0
    if proben < min_p:
        s += (min_p - proben) * 3
    if proben > max_p:
        s += (proben - max_p) * 3
    typen = Counter(type(h).__name__ for h in hinweise)
    s -= len(typen) * 0.8                       # Abwechslung belohnen
    s += max(0, typen["ImBereich"] - 1) * 1.5   # direkte Angaben bestrafen
    s += max(0, typen["NichtImBereich"] - 2) * 1.0
    s += max(0, max(typen.values()) - 4) * 1.0  # nicht zu viel vom Gleichen
    return s


def erzeuge(fall: Fall, versuche: int = 40, log=print) -> Raetsel:
    ziel = ZIELE[fall.schwierigkeit]
    rng = random.Random(fall.seed)
    aufstellungen = alle_aufstellungen(fall)
    if not aufstellungen:
        raise ValueError("Mit diesem Plan und diesen Bereichen gibt es keine gültige "
                         "Aufstellung (jede Zeile/Spalte genau eine Person).")
    log(f"  {len(aufstellungen)} mögliche Aufstellungen")
    bestes = None
    for i in range(versuche):
        pos = rng.choice(aufstellungen)
        pool = hinweis_pool(fall, pos, rng)
        ergebnis = reduziere(fall, pool, rng, max_proben=ziel[1] + 2)
        if ergebnis is None:
            continue
        hinweise, proben = ergebnis
        note = _bewertung(hinweise, proben, ziel)
        if bestes is None or note < bestes[0]:
            bestes = (note, Raetsel(fall, pos, hinweise, proben))
            log(f"  Versuch {i + 1:2d}: {len(hinweise)} Hinweise, {proben} Proben "
                f"(Bewertung {note:.1f})")
    if bestes is None:
        raise RuntimeError("Kein lösbares Rätsel gefunden.")
    r = bestes[1]
    r.hinweise = _sortiere(fall, r.hinweise, rng)
    return r


def _sortiere(fall: Fall, hinweise: list[Hinweis], rng: random.Random):
    """Mischt die Hinweise, aber allgemeine Aussagen ("Niemand ...") ans Ende."""
    h = list(hinweise)
    rng.shuffle(h)
    return sorted(h, key=lambda x: isinstance(x, Niemand))
