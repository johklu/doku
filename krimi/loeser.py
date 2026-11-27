"""Löser.

1. `finde_loesungen`: exakte Suche (Backtracking). Damit wird garantiert, dass
   jedes Rätsel genau EINE Lösung hat.

2. `loese_logisch` (in logik.py): löst wie ein Mensch, schreibt dabei den
   Lösungsweg mit und zählt die nötigen "Was wäre wenn"-Proben.

Spielregeln, die der Löser kennt:
  * In jeder Zeile und jeder Spalte steht genau eine Person.
  * Personen stehen nur auf freien oder besetzbaren Feldern.
  * Im Bereich des Opfers war genau eine weitere Person: der Täter.
"""

from __future__ import annotations

from .fall import Fall, Zelle
from .hinweise import Hinweis


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


# Der logische ("menschliche") Löser steht in logik.py.
from .logik import Widerspruch, loese_logisch  # noqa: E402,F401
