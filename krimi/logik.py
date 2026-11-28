"""Logischer Löser mit Protokoll – löst wie ein Mensch und schreibt mit.

Regeln (immer die einfachste zuerst):
  1. Zeilen/Spalten bereits gesetzter Personen sind für alle anderen tabu.
  2. Hinweise zwischen zwei Personen (weiter links, schräg neben, ...).
  3. "Bereich für sich allein".
  4. Opfer-Regel: im Bereich des Opfers ist genau eine weitere Person.
  5. In eine Zeile/Spalte passt nur noch eine Person.
  6. k Personen passen zusammen nur in k Zeilen/Spalten -> dort niemand sonst.
  7. Probe: "Angenommen X stünde auf Feld F ..." führt sofort zum Widerspruch.

Die Anzahl der Proben ist das Maß für die Schwierigkeit.
"""

from __future__ import annotations

from itertools import combinations

from .fall import Fall, Zelle
from .hinweise import Hinweis, atome


class Widerspruch(Exception):
    def __init__(self, grund: str = ""):
        super().__init__(grund)
        self.grund = grund


def _ohne_punkt(s: str) -> str:
    return s[:-1] if s.endswith(".") else s


def _linie(achse: int, i: int) -> str:
    return f"Zeile {i + 1}" if achse == 0 else f"Spalte {'ABCDEFGHIJKL'[i]}"


def _aufzaehlung(namen: list[str]) -> str:
    return namen[0] if len(namen) == 1 else ", ".join(namen[:-1]) + " und " + namen[-1]


class Logik:
    def __init__(self, fall: Fall, hinweise: list[Hinweis], protokoll: bool = True):
        self.fall = fall
        self.hinweise = hinweise
        self.P = len(fall.personen)
        self.v = fall.opfer_index
        self.protokoll = protokoll
        einzeln = [a for h in hinweise for a in atome(h)]
        unaer = list(einzeln)   # zweistellige Hinweise erlauben einzeln alles – außer Kombis
        self.binaer = [h for h in einzeln if h.paar() is not None]
        self.allein = {h.allein: h for h in einzeln if h.allein is not None}
        self.hinweis_von: dict[int, Hinweis] = {}
        for h in hinweise:
            self.hinweis_von.setdefault(h.subjekt, h)
        self.D: list[set[Zelle]] = [
            {z for z in fall.zellen()
             if fall.besetzbar(z) and all(h.erlaubt(fall, p, z) for h in unaer)}
            for p in range(self.P)]
        self.grund: list[tuple | None] = [None] * self.P
        self.gemeldet: set[int] = set()
        self.schritte: list[str] = []
        self.proben = 0
        self.max_kette = 0      # längste Folgerungskette einer Probe
        self.bekannt: dict[int, frozenset] = {}   # bereits genannte Kandidaten
        self.reihenfolge: list[int] = []         # wer wann feststand

    # --- Hilfen ----------------------------------------------------------
    def name(self, p: int) -> str:
        return self.fall.personen[p].nom

    def akk(self, p: int) -> str:
        return self.fall.personen[p].akk

    def dat(self, p: int) -> str:
        return self.fall.personen[p].dat

    def verb(self, p: int, einzahl: str, mehrzahl: str) -> str:
        return mehrzahl if self.fall.personen[p].mehrzahl else einzahl

    def kopie(self) -> "Logik":
        k = Logik.__new__(Logik)
        k.__dict__.update(self.__dict__)
        k.D = [set(d) for d in self.D]
        k.grund = list(self.grund)
        k.gemeldet = set(self.gemeldet)
        k.reihenfolge = list(self.reihenfolge)
        k.schritte = []
        k.protokoll = False
        return k

    def _entferne(self, p: int, weg, grund: tuple) -> bool:
        weg = self.D[p] & set(weg)
        if not weg:
            return False
        self.D[p] -= weg
        self.grund[p] = grund
        if len(self.D[p]) == 1:
            self.reihenfolge.append(p)
        if not self.D[p]:
            raise Widerspruch(self._warum_leer(p, grund))
        return True

    def _warum_leer(self, p: int, grund: tuple) -> str:
        name = self.name(p)
        if grund[0] in ("binaer", "allein"):
            return (f"könnte {name} den Hinweis „{_ohne_punkt(grund[1].text(self.fall))}“ "
                    f"nicht mehr erfüllen")
        if grund[0] == "opfer":
            return (f"wäre außer {self.dat(p)} nicht genau eine weitere Person im selben "
                    f"Bereich (dann gäbe es keinen eindeutigen Übeltäter)")
        return f"bliebe für {self.akk(p)} kein Feld mehr übrig"

    def _felder(self, zellen) -> str:
        return _aufzaehlung([self.fall.koordinate(z) for z in sorted(zellen)]).replace(" und ", " oder ")

    def _behalte(self, p: int, bleibt, grund: tuple) -> bool:
        return self._entferne(p, self.D[p] - set(bleibt), grund)

    def fest(self, p: int) -> Zelle | None:
        return next(iter(self.D[p])) if len(self.D[p]) == 1 else None

    # --- Regeln ----------------------------------------------------------
    def r_linien(self) -> bool:
        weiter = False
        for q in range(self.P):
            zq = self.fest(q)
            if zq is None:
                continue
            for p in range(self.P):
                if p != q:
                    weiter |= self._entferne(
                        p, {z for z in self.D[p] if z[0] == zq[0] or z[1] == zq[1]},
                        ("linien",))
        return weiter

    def r_binaer(self) -> bool:
        weiter = False
        f = self.fall
        for h in self.binaer:
            a, b = h.paar()
            weiter |= self._behalte(a, {za for za in self.D[a] if any(
                za[0] != zb[0] and za[1] != zb[1] and h.ok2(f, za, zb) for zb in self.D[b])},
                ("binaer", h, b))
            weiter |= self._behalte(b, {zb for zb in self.D[b] if any(
                za[0] != zb[0] and za[1] != zb[1] and h.ok2(f, za, zb) for za in self.D[a])},
                ("binaer", h, a))
        return weiter

    def _bereiche(self):
        f = self.fall
        moeglich = [{f.bereich(z) for z in self.D[p]} for p in range(self.P)]
        sicher = [next(iter(m)) if len(m) == 1 else None for m in moeglich]
        return moeglich, sicher

    def r_allein(self) -> bool:
        weiter = False
        f = self.fall
        _, sicher = self._bereiche()
        for p, h in self.allein.items():
            weiter |= self._behalte(p, {z for z in self.D[p] if not any(
                sicher[q] == f.bereich(z) for q in range(self.P) if q != p)}, ("allein", h))
            if sicher[p] is not None:
                for q in range(self.P):
                    if q != p:
                        weiter |= self._entferne(
                            q, {z for z in self.D[q] if f.bereich(z) == sicher[p]},
                            ("allein", h))
        return weiter

    def r_opfer(self) -> bool:
        f, v, P = self.fall, self.v, self.P
        moeglich, sicher = self._bereiche()
        weiter = False

        def ok(z):
            b = f.bereich(z)
            s = [q for q in range(P) if q != v and sicher[q] == b]
            m = [q for q in range(P) if q != v and b in moeglich[q]]
            return len(s) <= 1 and len(m) >= 1

        weiter |= self._behalte(v, {z for z in self.D[v] if ok(z)}, ("opfer",))
        if sicher[v] is not None:
            b = sicher[v]
            s = [q for q in range(P) if q != v and sicher[q] == b]
            m = [q for q in range(P) if q != v and b in moeglich[q]]
            if len(s) == 1:
                for q in range(P):
                    if q not in (v, s[0]):
                        weiter |= self._entferne(
                            q, {z for z in self.D[q] if f.bereich(z) == b}, ("opfer_voll",))
            if len(m) == 1:
                q = m[0]
                weiter |= self._behalte(q, {z for z in self.D[q] if f.bereich(z) == b},
                                        ("opfer_taeter",))
        return weiter

    def r_einzig(self) -> bool:
        for achse in (0, 1):
            for i in range(self.fall.n):
                wer = [p for p in range(self.P) if any(z[achse] == i for z in self.D[p])]
                if not wer:
                    raise Widerspruch(f"könnte in {_linie(achse, i)} niemand mehr stehen")
                if len(wer) == 1:
                    p = wer[0]
                    if self._behalte(p, {z for z in self.D[p] if z[achse] == i},
                                     ("einzig", achse, i)):
                        return True
        return False

    def r_hall(self) -> bool:
        P = self.P
        for k in range(1, P):
            for achse in (0, 1):
                maske = [0] * P
                for p in range(P):
                    for z in self.D[p]:
                        maske[p] |= 1 << z[achse]
                for gruppe in combinations(range(P), k):
                    if k == 1 and len(self.D[gruppe[0]]) == 1:
                        continue          # gesetzte Personen erledigt r_linien
                    vereinigt = 0
                    for p in gruppe:
                        vereinigt |= maske[p]
                    anzahl = vereinigt.bit_count()
                    if anzahl < k:
                        namen = _aufzaehlung([self.name(p) for p in gruppe])
                        raise Widerspruch(f"hätten {namen} zusammen nur {anzahl} "
                                          f"{'Zeile(n)' if achse == 0 else 'Spalte(n)'}")
                    if anzahl != k:
                        continue
                    linien = [i for i in range(self.fall.n) if (vereinigt >> i) & 1]
                    grund = ("hall", gruppe, achse, linien)
                    weiter = False
                    for q in range(P):
                        if q not in gruppe:
                            weiter |= self._entferne(
                                q, {z for z in self.D[q] if z[achse] in linien}, grund)
                    if weiter:
                        self._log_hall(gruppe, achse, linien)
                        return True
        return False

    REGELN = ("r_linien", "r_binaer", "r_allein", "r_opfer", "r_einzig", "r_hall")

    # --- Ablauf ----------------------------------------------------------
    def propagiere(self):
        while True:
            self._melde_gesetzte()
            for regel in self.REGELN:
                if getattr(self, regel)():
                    break
            else:
                break
        self._melde_gesetzte()
        if all(len(d) == 1 for d in self.D):
            self._pruefe_vollstaendig()

    def loese(self, max_proben: int = 99):
        if self.protokoll:
            for p in range(self.P):
                h = self.hinweis_von.get(p)
                if p != self.v and h is not None and h.paar() is None and 2 <= len(self.D[p]) <= 3:
                    self.schritte.append(f"{_ohne_punkt(h.text(self.fall))} – das geht nur auf "
                                         f"{self._felder(self.D[p])}.")
                    self.bekannt[p] = frozenset(self.D[p])
        try:
            self.propagiere()
            while any(len(d) > 1 for d in self.D):
                if self.proben >= max_proben or not self._probe():
                    return None
        except Widerspruch:
            return None
        self._log_ende()
        return {p: self.fest(p) for p in range(self.P)}

    def _probe(self) -> bool:
        for p in sorted(range(self.P), key=lambda p: (p == self.v, len(self.D[p]), p)):
            if len(self.D[p]) == 1:
                continue
            for z in sorted(self.D[p]):
                versuch = self.kopie()
                versuch.D[p] = {z}
                try:
                    versuch.propagiere()
                except Widerspruch as w:
                    self.proben += 1
                    folgen = [f"{self.name(q)} auf {self.fall.koordinate(next(iter(versuch.D[q])))}"
                              for q in range(self.P)
                              if q != p and len(versuch.D[q]) == 1 and len(self.D[q]) > 1]
                    self.max_kette = max(self.max_kette, len(folgen))
                    if self.protokoll:
                        kette = (f"Daraus folgt: {_aufzaehlung(folgen)} – und dann {w.grund}"
                                 if folgen else f"Dann {w.grund}")
                        self.schritte.append(
                            f"Angenommen, {self.name(p)} {self.verb(p, 'stünde', 'stünden')} "
                            f"auf {self.fall.koordinate(z)}. {kette}. Also scheidet "
                            f"{self.fall.koordinate(z)} für {self.akk(p)} aus.")
                    self._entferne(p, {z}, ("probe", z))
                    self.propagiere()
                    return True
        return False

    def _pruefe_vollstaendig(self):
        f = self.fall
        stellung = {p: self.fest(p) for p in range(self.P)}
        b = f.bereich(stellung[self.v])
        if sum(1 for z in stellung.values() if f.bereich(z) == b) != 2:
            raise Widerspruch("wäre im Bereich des Opfers nicht genau eine weitere Person")
        if not all(h.gilt(f, stellung) for h in self.hinweise):
            raise Widerspruch("wären nicht mehr alle Hinweise erfüllt")

    # --- Protokoll -------------------------------------------------------
    def _log_hall(self, gruppe, achse, linien):
        if not self.protokoll:
            return
        art = "Zeile" if achse == 0 else "Spalte"
        namen_l = [self.name(p) for p in gruppe]
        bez = [str(i + 1) if achse == 0 else "ABCDEFGHIJKL"[i] for i in linien]
        if len(gruppe) == 1:
            p = gruppe[0]
            if self.bekannt.get(p) == frozenset(self.D[p]):
                self.schritte.append(
                    f"Da {namen_l[0]} sicher in {art} {bez[0]} {self.verb(p, 'steht', 'stehen')}, "
                    f"ist {art} {bez[0]} "
                    f"für alle anderen tabu.")
            else:
                felder = (f" ({self._felder(self.D[p])})" if len(self.D[p]) <= 4 else "")
                self.schritte.append(
                    f"{namen_l[0]} {self.verb(p, 'kommt', 'kommen')} nur noch in {art} {bez[0]} "
                    f"in Frage{felder} – "
                    f"für alle anderen ist {art} {bez[0]} damit tabu.")
            self.bekannt[p] = frozenset(self.D[p])
        else:
            mit_feldern = [f"{self.name(p)} ({self._felder(self.D[p])})"
                           if len(self.D[p]) <= 3 else self.name(p) for p in gruppe]
            self.schritte.append(
                f"{_aufzaehlung(mit_feldern)} passen zusammen nur in die {art}n "
                f"{_aufzaehlung(bez)} – diese sind damit für alle anderen gesperrt.")

    def _melde_gesetzte(self):
        if not self.protokoll:
            return
        anfang = [p for p in range(self.P) if p not in self.reihenfolge]
        for p in anfang + self.reihenfolge:
            if p in self.gemeldet or len(self.D[p]) != 1:
                continue
            self.gemeldet.add(p)
            if p == self.v:
                continue      # das Opfer kommt im Schlusssatz
            self.schritte.append(self._satz(p, self.fest(p)))

    def _satz(self, p: int, z: Zelle) -> str:
        f = self.fall
        name, feld = self.name(p), f.koordinate(z)
        eigen = self.hinweis_von.get(p)
        eigen_txt = _ohne_punkt(eigen.text(f)) if eigen else None
        g = self.grund[p]
        art = g[0] if g else None
        if art is None:
            return f"{eigen_txt} – das ist nur auf {feld} möglich."
        if art == "linien":
            if eigen_txt:
                return f"{eigen_txt} – von den passenden Feldern ist nur noch {feld} frei."
            return f"Für {name} ist nur noch {feld} frei."
        if art == "binaer":
            h, anderer = g[1], g[2]
            if anderer in self.gemeldet:
                return (f"{_ohne_punkt(h.text(f))} – da {self.name(anderer)} schon feststeht, "
                        f"bleibt für {name} nur {feld}.")
            return f"{_ohne_punkt(h.text(f))} – damit bleibt für {name} nur {feld}."
        if art == "einzig":
            return f"In {_linie(g[1], g[2])} kann nur noch {name} stehen – also auf {feld}."
        if art == "hall":
            linien = _aufzaehlung([_linie(g[2], i) for i in g[3]])
            gesperrt = "gesperrt ist" if len(g[3]) == 1 else "gesperrt sind"
            if eigen_txt:
                return f"{eigen_txt} – da {linien} {gesperrt}, bleibt nur {feld}."
            return f"Da {linien} {gesperrt}, bleibt für {name} nur {feld}."
        if art == "allein":
            return f"{_ohne_punkt(g[1].text(f))} – also steht {name} auf {feld}."
        if art in ("opfer", "opfer_voll", "opfer_taeter"):
            return (f"Im Bereich des Opfers muss genau eine weitere Person sein – "
                    f"damit steht {name} auf {feld}.")
        if art == "probe":
            return f"Damit bleibt für {name} nur noch {feld}."
        return f"{name} steht auf {feld}."

    def _log_ende(self):
        if not self.protokoll:
            return
        f = self.fall
        zv = self.fest(self.v)
        b = f.bereich(zv)
        taeter = next(p for p in range(self.P) if p != self.v and f.bereich(self.fest(p)) == b)
        self.schritte.append(
            f"Übrig bleibt {f.koordinate(zv)}: Dort {self.verb(self.v, 'war', 'waren')} "
            f"{self.name(self.v)}. "
            f"{f.bereiche[b].praep[0].upper()}{f.bereiche[b].praep[1:]} war sonst nur "
            f"{self.name(taeter)} – also: {self.name(taeter)} {f.tat}!")


def loese_logisch(fall: Fall, hinweise: list[Hinweis], max_proben: int = 99,
                  protokoll: bool = False):
    """(Lösung | None, Anzahl Proben, Schritte)."""
    l = Logik(fall, hinweise, protokoll=protokoll)
    stellung = l.loese(max_proben=max_proben)
    schritte = [s[:1].upper() + s[1:] for s in l.schritte]   # "die Oliven …" am Satzanfang
    return stellung, l.proben, schritte


def bewerte(fall: Fall, hinweise: list[Hinweis], max_proben: int = 99) -> Logik:
    """Löst ohne Protokoll und gibt den Löser (proben, max_kette, D) zurück."""
    l = Logik(fall, hinweise, protokoll=False)
    l.ergebnis = l.loese(max_proben=max_proben)
    return l
