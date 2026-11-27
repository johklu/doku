"""Generator: erzeugt aus einem Fall (Plan + Personen) ein lösbares Rätsel.

Jede verdächtige Person bekommt GENAU EINEN Hinweis.

Ablauf
  1. Eine zufällige Aufstellung wählen, die zu den vorgegebenen Bereichen der
     Personen passt (jede Zeile/Spalte genau eine Person).
  2. Für jede Person alle Aussagen sammeln, die für diese Aufstellung wahr sind.
  3. Lokale Suche: je Person eine Aussage wählen und so lange austauschen, bis
     das Rätsel genau eine Lösung hat und sich ohne Raten lösen lässt –
     mit der gewünschten Schwierigkeit.
  4. Das mit mehreren Aufstellungen wiederholen und das beste Rätsel nehmen.
"""

from __future__ import annotations

import itertools
import random
from collections import Counter
from dataclasses import dataclass, field

from .fall import Fall, Zelle
from .hinweise import (AmRand, AndererBereich, AufObjekt, Allein, GleicherBereich,
                       Hinweis, ImBereich, Kombi, Links, NebenObjekt, NichtImBereich,
                       NichtNebenObjekt, Oben, Schraeg)
from .logik import bewerte, loese_logisch
from .loeser import finde_loesungen

# Schwierigkeit = Anzahl nötiger "Was wäre wenn"-Proben (min, max)
ZIELE = {
    "leicht": (0, 0),
    "mittel": (1, 3),
    "schwer": (3, 8),
}
ZAEHL_LIMIT = 60
MAX_KETTE = 3   # eine Probe darf höchstens so viele Folgerungen brauchen


@dataclass
class Raetsel:
    fall: Fall
    loesung: dict[int, Zelle]
    hinweise: list[Hinweis]
    proben: int
    schritte: list[str] = field(default_factory=list)
    texte: dict[int, str] = field(default_factory=dict)   # eingefrorene Hinweistexte

    def text(self, h: Hinweis) -> str:
        """Hinweistext – bei eingefrorenen Rätseln exakt der abgenommene Satz."""
        return self.texte.get(id(h)) or h.text(self.fall)

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

    aufstellungen = []
    for perm in itertools.permutations(range(n)):
        zellen = [(r, perm[r]) for r in range(n)]
        if not all(fall.besetzbar(z) for z in zellen):
            continue
        if Counter(fall.bereich(z) for z in zellen) != soll:
            continue
        je_bereich: dict[str, list[Zelle]] = {}
        for z in zellen:
            je_bereich.setdefault(fall.bereich(z), []).append(z)
        teile = [[(personen, zs) for zs in itertools.permutations(je_bereich[b])]
                 for b, personen in nach_bereich.items()]
        for kombi in itertools.product(*teile):
            pos = {}
            for personen, zs in kombi:
                pos.update(zip(personen, zs))
            aufstellungen.append(pos)
    return aufstellungen


def kandidaten(fall: Fall, pos: dict[int, Zelle], p: int) -> list[Hinweis]:
    """Alle wahren Aussagen, deren Satz mit Person p beginnt."""
    P = len(fall.personen)
    v = fall.opfer_index
    z = pos[p]
    b = fall.bereich(z)
    liste: list[Hinweis] = []

    erste: list[Hinweis] = [ImBereich(p, b)]
    zweite: list[Hinweis] = []
    liste.append(ImBereich(p, b))
    for andere in fall.bereiche:
        if andere != b:
            liste.append(NichtImBereich(p, andere))
    o = fall.objekt(z)
    if o is not None:
        h = AufObjekt(p, o.kuerzel)
        liste.append(h)
        erste.append(h)
    nachbar_arten = fall.arten_neben(z)
    for k in sorted(nachbar_arten):
        h = NebenObjekt(p, k)
        if fall.anzahl_objekt(k) >= 8:      # "neben einem Sitz" ist fast nichtssagend
            h.prio = 2
        liste.append(h)
        zweite.append(h)
    relevant = {k for bz in fall.bereichs_zellen(b) if fall.besetzbar(bz)
                for k in fall.arten_neben(bz)}
    for k in sorted(relevant - nachbar_arten):
        h = NichtNebenObjekt(p, k)
        liste.append(h)
        zweite.append(h)
    rand = z[0] in (0, fall.n - 1) or z[1] in (0, fall.n - 1)
    h = AmRand(p, rand)
    liste.append(h)
    zweite.append(h)
    if sum(1 for q in range(P) if fall.bereich(pos[q]) == b) == 1:
        liste.append(Allein(p))

    # Kombinationen nur, wenn beide Teile etwas beitragen
    frei = [zz for zz in fall.zellen() if fall.besetzbar(zz)]

    def felder(h):
        return {zz for zz in frei if h.erlaubt(fall, p, zz)}

    for a in erste:
        fa = felder(a)
        for c in zweite:
            fc = felder(c)
            beide = fa & fc
            if len(beide) < len(fa) and len(beide) < len(fc):
                liste.append(Kombi(a, c))

    for q in range(P):
        if q in (p, v):
            continue
        zq = pos[q]
        liste.append(Links(p, q) if z[1] < zq[1] else Links(q, p, umgekehrt=True))
        liste.append(Oben(p, q) if z[0] < zq[0] else Oben(q, p, umgekehrt=True))
        if abs(z[0] - zq[0]) == 1 and abs(z[1] - zq[1]) == 1 and fall.bereich(zq) == b:
            liste.append(Schraeg(p, q))
        if fall.bereich(zq) == b:
            liste.append(GleicherBereich(p, q))
        else:
            liste.append(AndererBereich(p, q))

    for h in liste:
        assert h.subjekt == p and h.gilt(fall, pos), h
    return liste


def _kosten(fall: Fall, wahl: dict[int, Hinweis], ziel) -> tuple[float, int]:
    hinweise = list(wahl.values())
    n = len(finde_loesungen(fall, hinweise, limit=ZAEHL_LIMIT))
    if n == 0:
        return 999.0, 0
    if n > 1:
        return float(n), 0
    l = bewerte(fall, hinweise, max_proben=ziel[1] + 3)
    proben = l.proben
    if l.ergebnis is None or proben > ziel[1] or l.max_kette > MAX_KETTE:
        return 1.6, proben          # eindeutig, aber zu schwer
    if proben < ziel[0]:
        return 0.6, proben          # eindeutig, aber zu leicht
    return 0.0, proben


def _gewicht(h: Hinweis) -> float:
    return 0.5 + h.prio


def satzformen(h: Hinweis) -> list[str]:
    if isinstance(h, Kombi):
        return [type(h.a).__name__, type(h.b).__name__]
    return [type(h).__name__]


def _note(hinweise: list[Hinweis]) -> float:
    """Kleiner = schöner: abwechslungsreich, wenig direkte Angaben."""
    typen = Counter(type(h).__name__ for h in hinweise)
    s = -len(typen) * 0.8
    s += typen["ImBereich"] * 1.5
    s += typen["NichtImBereich"] * 0.5
    s += max(0, typen["Kombi"] - 2) * 1.5
    formen = Counter(f for h in hinweise for f in satzformen(h))
    s += sum(max(0, n - 1) for n in formen.values()) * 1.5  # gleiche Satzform
    schwach = sum(1 for h in hinweise if isinstance(h, NichtNebenObjekt)
                  or (isinstance(h, Kombi) and isinstance(h.b, NichtNebenObjekt)))
    s += max(0, schwach - 1) * 1.5                          # "nicht neben ..." sparsam
    # gleiche Aussage über verschiedene Personen ("nicht neben einer Kamera" 2x)
    aussagen = Counter((type(h).__name__, getattr(h, "k", None), getattr(h, "b", None))
                       for h in hinweise if not h.paar())
    s += sum(n - 1 for n in aussagen.values()) * 2.0
    return s


def opfer_kandidaten(fall: Fall, pos) -> list[Hinweis]:
    """Hinweise zum "Opfer": nur über Gegenstände und den Rand – nichts, was den
    Bereich (und damit den Übeltäter) direkt verrät."""
    erlaubt = (AufObjekt, NebenObjekt, NichtNebenObjekt, AmRand)
    return [h for h in kandidaten(fall, pos, fall.opfer_index)
            if isinstance(h, erlaubt)
            or (isinstance(h, Kombi) and isinstance(h.a, AufObjekt))]


def alle_kandidaten(fall: Fall, pos) -> dict[int, list[Hinweis]]:
    v = fall.opfer_index
    kand = {p: kandidaten(fall, pos, p) for p in range(len(fall.personen)) if p != v}
    if fall.opfer_hinweis:
        kand[v] = opfer_kandidaten(fall, pos)
    return kand


def _gierig(fall: Fall, kand, rng, frei, runden: int = 2, grenze: int = 800):
    """Für große Pläne: je Person den Hinweis nehmen, der die Zahl der Lösungen
    am stärksten senkt (mit hoher Zählgrenze, damit Unterschiede sichtbar sind)."""
    wahl: dict[int, Hinweis] = {}
    for _ in range(runden):
        for p in rng.sample(list(kand), len(kand)):
            bestes = None
            for h in kand[p]:
                if not frei(p, h, wahl):
                    continue
                neu = dict(wahl)
                neu[p] = h
                n = len(finde_loesungen(fall, list(neu.values()), limit=grenze))
                schluessel = (n, -_gewicht(h) * rng.random())
                if bestes is None or schluessel < bestes[0]:
                    bestes = (schluessel, h)
            if bestes:
                wahl[p] = bestes[1]
        if len(wahl) == len(kand) and len(finde_loesungen(fall, list(wahl.values()))) == 1:
            break
    return wahl


def suche(fall: Fall, pos, rng: random.Random, ziel, schritte_max: int = 80):
    kand = alle_kandidaten(fall, pos)
    verdaechtige = list(kand)
    gross = fall.n >= 9
    max_form = 3 if gross else 2       # große Pläne brauchen mehr starke Hinweise

    def frei(p, h, wahl):
        """h passt, wenn (1) keine gleiche Aussage schon bei jemand anderem steht
        und (2) keine Satzform ("direkt neben", "weiter links", ...) dadurch
        öfter als zweimal vorkommt."""
        belegt, formen = set(), Counter()
        for q, hq in wahl.items():
            if q != p:
                belegt |= hq.bausteine()
                formen.update(satzformen(hq))
        if h.bausteine() & belegt:
            return False
        formen.update(satzformen(h))
        return max(formen.values()) <= max_form

    if gross:
        wahl = _gierig(fall, kand, rng, frei, runden=3, grenze=3000)
        if len(wahl) < len(kand):
            return wahl, 999.0, 0
        # nur feinjustieren, wenn der gierige Start schon eindeutig ist
        if len(finde_loesungen(fall, list(wahl.values()))) != 1:
            return wahl, 999.0, 0
        schritte_max = 15
    else:
        wahl = {}
        for p in rng.sample(verdaechtige, len(verdaechtige)):
            moeglich = [h for h in kand[p] if frei(p, h, wahl)]
            if not moeglich:
                return wahl, 999.0, 0
            wahl[p] = rng.choices(moeglich, weights=[_gewicht(h) for h in moeglich])[0]
    kosten, proben = _kosten(fall, wahl, ziel)
    bestes_bisher, ohne_fortschritt = kosten, 0
    for _ in range(schritte_max):
        if kosten == 0.0 or ohne_fortschritt >= (6 if gross else 25):
            break
        p = rng.choice(verdaechtige)
        passend = [h for h in kand[p] if frei(p, h, wahl)]
        if not passend:
            continue
        optionen = rng.sample(passend, min(6 if gross else 14, len(passend)))
        bestes = None
        for h in optionen:
            neu = dict(wahl)
            neu[p] = h
            k, pr = _kosten(fall, neu, ziel)
            schluessel = (k, -_gewicht(h) * rng.random())
            if bestes is None or schluessel < bestes[0]:
                bestes = (schluessel, neu, k, pr)
        if bestes[2] <= kosten:
            _, wahl, kosten, proben = bestes
        if kosten < bestes_bisher:
            bestes_bisher, ohne_fortschritt = kosten, 0
        else:
            ohne_fortschritt += 1
    return wahl, kosten, proben


def erzeuge(fall: Fall, versuche: int = 12, log=print) -> Raetsel:
    ziel = ZIELE[fall.schwierigkeit]
    rng = random.Random(fall.seed)
    aufstellungen = alle_aufstellungen(fall)
    if not aufstellungen:
        raise ValueError("Mit diesem Plan und diesen Bereichen gibt es keine gültige "
                         "Aufstellung (jede Zeile/Spalte genau eine Person).")
    log(f"  {len(aufstellungen)} mögliche Aufstellungen")
    bestes = None
    if fall.n >= 9:
        versuche = min(versuche, 20)       # große Pläne: jeder Versuch dauert länger
    for i in range(versuche):
        pos = rng.choice(aufstellungen)
        # Aufstellungen, die selbst mit ALLEN wahren Aussagen nicht eindeutig
        # werden, gar nicht erst versuchen.
        alle = [h for liste in alle_kandidaten(fall, pos).values() for h in liste]
        if len(finde_loesungen(fall, alle)) != 1:
            log(f"  Versuch {i + 1:2d}: Aufstellung grundsätzlich mehrdeutig")
            continue
        import time as _zeit
        _start = _zeit.time()
        wahl, kosten, proben = suche(fall, pos, rng, ziel)
        if fall.n >= 9:
            log(f"  Versuch {i + 1:2d}: {_zeit.time() - _start:.0f} s")
        if kosten >= 1.0:
            log(f"  Versuch {i + 1:2d}: nicht eindeutig/lösbar")
            continue
        hinweise = [wahl[p] for p in sorted(wahl)]
        _, _, schritte = loese_logisch(fall, hinweise, protokoll=True)
        note = kosten * 10 + _note(hinweise) + 0.8 * max(0, len(schritte) - 10)
        log(f"  Versuch {i + 1:2d}: {proben} Proben, {len(schritte)} Schritte, Note {note:.1f}")
        if bestes is None or note < bestes[0]:
            bestes = (note, pos, hinweise)
    if bestes is None:
        tipp = "" if fall.opfer_hinweis else " Tipp: opfer_hinweis = true in der Fall-Datei."
        raise RuntimeError("Kein lösbares Rätsel gefunden – mehr Versuche oder Plan ändern." + tipp)
    _, pos, hinweise = bestes
    loesung, proben, schritte = loese_logisch(fall, hinweise, protokoll=True)
    assert loesung == pos
    return Raetsel(fall, pos, hinweise, proben, schritte)
