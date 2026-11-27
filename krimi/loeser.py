"""Löser.

1. `finde_loesungen`: exakte Suche (Backtracking). Damit wird garantiert, dass
   jedes Rätsel genau EINE Lösung hat.

2. `loese_logisch`: löst so, wie ein Mensch es tun würde – nur durch
   Ausschließen (Zeilen/Spalten, Hinweise, Bereichs-Regeln). Kommt er nicht
   weiter, probiert er eine Annahme und schaut, ob sie *sofort* zu einem
   Widerspruch führt ("Wenn Leah hier stünde, ..."). Die Zahl solcher Proben
   ist unser Maß für die Schwierigkeit.

Spielregeln, die der Löser kennt:
  * In jeder Zeile und jeder Spalte steht genau eine Person.
  * Personen stehen nur auf freien oder besetzbaren Feldern.
  * Im Bereich des Opfers war genau eine weitere Person: der Täter.
"""

from __future__ import annotations

from itertools import combinations

from .fall import Fall, Zelle
from .hinweise import Hinweis


class Widerspruch(Exception):
    pass


def _vorbereiten(fall: Fall, hinweise: list[Hinweis]):
    P = len(fall.personen)
    unaer = [h for h in hinweise if h.paar() is None and h.allein is None]
    binaer = [h for h in hinweise if h.paar() is not None]
    allein = {h.allein for h in hinweise if h.allein is not None}
    dom = []
    for p in range(P):
        dom.append([z for z in fall.zellen()
                    if fall.besetzbar(z) and all(h.erlaubt(fall, p, z) for h in unaer)])
    return P, dom, binaer, allein


def finde_loesungen(fall: Fall, hinweise: list[Hinweis], limit: int = 2):
    """Liefert bis zu `limit` Lösungen als Liste von {person: zelle}."""
    P, dom, binaer, allein = _vorbereiten(fall, hinweise)
    v = fall.opfer_index
    bin_von: list[list[tuple[Hinweis, int, bool]]] = [[] for _ in range(P)]
    for h in binaer:
        a, b = h.paar()
        bin_von[a].append((h, b, True))
        bin_von[b].append((h, a, False))

    pos: list[Zelle | None] = [None] * P
    zeilen, spalten = set(), set()
    loesungen = []

    def passt(p: int, z: Zelle) -> bool:
        for h, q, p_zuerst in bin_von[p]:
            zq = pos[q]
            if zq is not None:
                if not (h.ok2(fall, z, zq) if p_zuerst else h.ok2(fall, zq, z)):
                    return False
        b = fall.bereich(z)
        im_bereich = [q for q in range(P) if pos[q] is not None and fall.bereich(pos[q]) == b]
        if im_bereich and (p in allein or any(q in allein for q in im_bereich)):
            return False
        # Opfer-Regel: höchstens eine weitere Person im Bereich des Opfers
        if p == v:
            if len(im_bereich) > 1:
                return False
        elif pos[v] is not None and fall.bereich(pos[v]) == b:
            if len(im_bereich) > 1:      # Opfer + schon ein Täter
                return False
        return True

    def suche():
        if len(loesungen) >= limit:
            return
        offen = [p for p in range(P) if pos[p] is None]
        if not offen:
            b = fall.bereich(pos[v])
            if sum(1 for z in pos if fall.bereich(z) == b) == 2:
                loesungen.append({p: pos[p] for p in range(P)})
            return
        bester, beste_kand = None, None
        for p in offen:
            kand = [z for z in dom[p]
                    if z[0] not in zeilen and z[1] not in spalten and passt(p, z)]
            if bester is None or len(kand) < len(beste_kand):
                bester, beste_kand = p, kand
                if not kand:
                    return
        for z in beste_kand:
            pos[bester] = z
            zeilen.add(z[0]); spalten.add(z[1])
            suche()
            zeilen.discard(z[0]); spalten.discard(z[1])
            pos[bester] = None
            if len(loesungen) >= limit:
                return

    suche()
    # Sicherheitsnetz: jede gefundene Lösung muss alle Hinweise erfüllen.
    for l in loesungen:
        assert all(h.gilt(fall, l) for h in hinweise), "Löser-Inkonsistenz"
    return loesungen


# ---------------------------------------------------------------------------
# Logischer ("menschlicher") Löser
# ---------------------------------------------------------------------------

def _propagiere(fall: Fall, D: list[set[Zelle]], binaer, allein):
    P = len(D)
    v = fall.opfer_index
    n = fall.n
    geaendert = True

    def setze(p, neu):
        nonlocal geaendert
        if not neu:
            raise Widerspruch
        if neu != D[p]:
            D[p] = neu
            geaendert = True

    while geaendert:
        geaendert = False

        # 1) Zeilen und Spalten: Hall-Regel ("k Personen passen nur in k
        #    Zeilen -> diese Zeilen sind für alle anderen tabu") und
        #    umgekehrt ("in diese Zeile passt nur noch eine Person").
        for achse in (0, 1):
            maske = [0] * P
            for p in range(P):
                for z in D[p]:
                    maske[p] |= 1 << z[achse]
            for k in range(1, P):
                for gruppe in combinations(range(P), k):
                    vereinigt = 0
                    for p in gruppe:
                        vereinigt |= maske[p]
                    anzahl = vereinigt.bit_count()
                    if anzahl < k:
                        raise Widerspruch
                    if anzahl == k:
                        for q in range(P):
                            if q not in gruppe and maske[q] & vereinigt:
                                setze(q, {z for z in D[q]
                                          if not (vereinigt >> z[achse]) & 1})
                                maske[q] &= ~vereinigt
            for linie in range(n):
                wer = [p for p in range(P) if any(z[achse] == linie for z in D[p])]
                if not wer:
                    raise Widerspruch
                if len(wer) == 1:
                    p = wer[0]
                    setze(p, {z for z in D[p] if z[achse] == linie})

        # 2) Hinweise zwischen zwei Personen
        for h in binaer:
            a, b = h.paar()
            setze(a, {za for za in D[a]
                      if any(za[0] != zb[0] and za[1] != zb[1] and h.ok2(fall, za, zb)
                             for zb in D[b])})
            setze(b, {zb for zb in D[b]
                      if any(za[0] != zb[0] and za[1] != zb[1] and h.ok2(fall, za, zb)
                             for za in D[a])})

        bereich_von = [{fall.bereich(z) for z in D[p]} for p in range(P)]
        sicher_in = [next(iter(bb)) if len(bb) == 1 else None for bb in bereich_von]

        # 3) "hatte den Bereich für sich allein"
        for p in allein:
            setze(p, {z for z in D[p]
                      if not any(sicher_in[q] == fall.bereich(z) for q in range(P) if q != p)})
            if sicher_in[p] is not None:
                for q in range(P):
                    if q != p:
                        setze(q, {z for z in D[q] if fall.bereich(z) != sicher_in[p]})

        # 4) Opfer-Regel: genau eine weitere Person im Bereich des Opfers
        def pruefe_opferzelle(z):
            b = fall.bereich(z)
            sicher = [q for q in range(P) if q != v and sicher_in[q] == b]
            moeglich = [q for q in range(P) if q != v and b in bereich_von[q]]
            return len(sicher) <= 1 and len(moeglich) >= 1

        setze(v, {z for z in D[v] if pruefe_opferzelle(z)})
        if sicher_in[v] is not None:
            b = sicher_in[v]
            sicher = [q for q in range(P) if q != v and sicher_in[q] == b]
            moeglich = [q for q in range(P) if q != v and b in bereich_von[q]]
            if len(sicher) == 1:
                for q in range(P):
                    if q != v and q != sicher[0]:
                        setze(q, {z for z in D[q] if fall.bereich(z) != b})
            if len(moeglich) == 1:
                q = moeglich[0]
                setze(q, {z for z in D[q] if fall.bereich(z) == b})
        # Zwei Personen, die sicher im selben Bereich sind, schließen das Opfer
        # dort aus (steckt bereits in pruefe_opferzelle).

    return D


def loese_logisch(fall: Fall, hinweise: list[Hinweis], max_proben: int = 99):
    """Gibt (Lösung, Anzahl Proben) zurück oder (None, Proben), wenn der
    logische Löser stecken bleibt."""
    P, dom, binaer, allein = _vorbereiten(fall, hinweise)
    D = [set(d) for d in dom]
    try:
        _propagiere(fall, D, binaer, allein)
    except Widerspruch:
        return None, 0

    proben = 0
    while any(len(d) > 1 for d in D):
        fortschritt = False
        # Kandidaten in einer "natürlichen" Reihenfolge probieren:
        # Personen mit wenigen Möglichkeiten zuerst.
        for p in sorted(range(P), key=lambda p: len(D[p])):
            if len(D[p]) == 1:
                continue
            for z in sorted(D[p]):
                D2 = [set(d) for d in D]
                D2[p] = {z}
                try:
                    _propagiere(fall, D2, binaer, allein)
                    if all(len(d) == 1 for d in D2):
                        stellung = {q: next(iter(D2[q])) for q in range(P)}
                        if not _vollstaendig_ok(fall, hinweise, stellung):
                            raise Widerspruch
                    continue
                except Widerspruch:
                    D[p].discard(z)
                    proben += 1
                    fortschritt = True
                    try:
                        _propagiere(fall, D, binaer, allein)
                    except Widerspruch:
                        return None, proben
                    break
            if fortschritt:
                break
        if not fortschritt or proben > max_proben:
            return None, proben

    stellung = {p: next(iter(D[p])) for p in range(P)}
    if not _vollstaendig_ok(fall, hinweise, stellung):
        return None, proben
    return stellung, proben


def _vollstaendig_ok(fall: Fall, hinweise, stellung) -> bool:
    zs = list(stellung.values())
    if len({z[0] for z in zs}) != len(zs) or len({z[1] for z in zs}) != len(zs):
        return False
    v = fall.opfer_index
    b = fall.bereich(stellung[v])
    if sum(1 for z in zs if fall.bereich(z) == b) != 2:
        return False
    return all(h.gilt(fall, stellung) for h in hinweise)
