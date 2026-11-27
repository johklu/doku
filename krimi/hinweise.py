"""Hinweis-Typen.

Jeder Hinweis kann
  * prüfen, ob er für eine vollständige Lösung stimmt (gilt),
  * als Einschränkung für den Löser dienen (erlaubt / ok2 / allein),
  * sich als deutscher Satz ausgeben (text).

`prio` steuert den Generator: Hinweise mit niedriger Priorität (z. B. "X war
auf der Tribüne") werden zuerst gestrichen, damit am Ende möglichst
interessante, indirekte Hinweise übrig bleiben.
"""

from __future__ import annotations

from .fall import Fall, Zelle

Stellung = dict[int, Zelle]


class Hinweis:
    prio = 1
    personen: tuple[int, ...] = ()
    allein: int | None = None        # nur für Allein-Hinweise

    # Einschränkung für genau eine Person (unär)
    def erlaubt(self, fall: Fall, p: int, z: Zelle) -> bool:
        return True

    # Einschränkung zwischen zwei Personen (binär), sonst None
    def paar(self) -> tuple[int, int] | None:
        return None

    def ok2(self, fall: Fall, za: Zelle, zb: Zelle) -> bool:
        return True

    def gilt(self, fall: Fall, pos: Stellung) -> bool:
        raise NotImplementedError

    def text(self, fall: Fall) -> str:
        raise NotImplementedError

    def schluessel(self):
        return (type(self).__name__,) + tuple(
            v for k, v in sorted(vars(self).items()))

    def __repr__(self):
        return f"<{self.schluessel()}>"


def _name(fall: Fall, p: int) -> str:
    return fall.personen[p].name


# --- unäre Hinweise ---------------------------------------------------------

class ImBereich(Hinweis):
    prio = 1

    def __init__(self, p: int, b: str):
        self.p, self.b = p, b
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        return p != self.p or fall.bereich(z) == self.b

    def gilt(self, fall, pos):
        return fall.bereich(pos[self.p]) == self.b

    def text(self, fall):
        return f"{_name(fall, self.p)} war {fall.bereiche[self.b].praep}."


class NichtImBereich(Hinweis):
    prio = 2

    def __init__(self, p: int, b: str):
        self.p, self.b = p, b
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        return p != self.p or fall.bereich(z) != self.b

    def gilt(self, fall, pos):
        return fall.bereich(pos[self.p]) != self.b

    def text(self, fall):
        return f"{_name(fall, self.p)} war nicht {fall.bereiche[self.b].praep}."


class AufObjekt(Hinweis):
    prio = 5

    def __init__(self, p: int, k: str):
        self.p, self.k = p, k
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        if p != self.p:
            return True
        o = fall.objekt(z)
        return o is not None and o.kuerzel == self.k

    def gilt(self, fall, pos):
        return self.erlaubt(fall, self.p, pos[self.p])

    def text(self, fall):
        from .katalog import KATALOG
        o = KATALOG[self.k]
        phrase = o.auf_best if fall.anzahl_objekt(self.k) == 1 else o.auf_unbest
        return f"{_name(fall, self.p)} {phrase}."


class NebenObjekt(Hinweis):
    prio = 4

    def __init__(self, p: int, k: str):
        self.p, self.k = p, k
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        if p != self.p:
            return True
        return any(fall.objekt(nz) is not None and fall.objekt(nz).kuerzel == self.k
                   for nz in fall.nachbarn4(z))

    def gilt(self, fall, pos):
        return self.erlaubt(fall, self.p, pos[self.p])

    def text(self, fall):
        from .katalog import KATALOG
        o = KATALOG[self.k]
        art = o.dat_best if fall.anzahl_objekt(self.k) == 1 else o.dat_unbest
        return f"{_name(fall, self.p)} befand sich direkt neben {art}."


class NichtNebenObjekt(Hinweis):
    prio = 3

    def __init__(self, p: int, k: str):
        self.p, self.k = p, k
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        if p != self.p:
            return True
        return not any(fall.objekt(nz) is not None and fall.objekt(nz).kuerzel == self.k
                       for nz in fall.nachbarn4(z))

    def gilt(self, fall, pos):
        return self.erlaubt(fall, self.p, pos[self.p])

    def text(self, fall):
        from .katalog import KATALOG
        o = KATALOG[self.k]
        art = o.dat_best if fall.anzahl_objekt(self.k) == 1 else o.dat_unbest
        return f"{_name(fall, self.p)} befand sich nicht neben {art}."


class AmRand(Hinweis):
    prio = 2

    def __init__(self, p: int, ja: bool = True):
        self.p, self.ja = p, ja
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        if p != self.p:
            return True
        rand = z[0] in (0, fall.n - 1) or z[1] in (0, fall.n - 1)
        return rand == self.ja

    def gilt(self, fall, pos):
        return self.erlaubt(fall, self.p, pos[self.p])

    def text(self, fall):
        if self.ja:
            return f"{_name(fall, self.p)} befand sich am äußeren Rand des Plans."
        return f"{_name(fall, self.p)} befand sich nicht am äußeren Rand des Plans."


class Niemand(Hinweis):
    """Kein Mensch (auch nicht das Opfer) stand auf einem bestimmten Objekt."""
    prio = 3

    def __init__(self, k: str, n_personen: int):
        self.k = k
        self.personen = tuple(range(n_personen))

    def erlaubt(self, fall, p, z):
        o = fall.objekt(z)
        return o is None or o.kuerzel != self.k

    def gilt(self, fall, pos):
        return all(self.erlaubt(fall, p, z) for p, z in pos.items())

    def text(self, fall):
        from .katalog import KATALOG
        return KATALOG[self.k].niemand

    def schluessel(self):
        return ("Niemand", self.k)


# --- Bereichs-Hinweis mit Sonderbehandlung im Löser -------------------------

class Allein(Hinweis):
    prio = 4

    def __init__(self, p: int):
        self.p = p
        self.allein = p
        self.personen = (p,)

    def gilt(self, fall, pos):
        b = fall.bereich(pos[self.p])
        return all(fall.bereich(z) != b for q, z in pos.items() if q != self.p)

    def text(self, fall):
        return f"{_name(fall, self.p)} hatte den ganzen Bereich für sich allein."


# --- binäre Hinweise --------------------------------------------------------

class _Binaer(Hinweis):
    def __init__(self, p: int, q: int):
        self.p, self.q = p, q
        self.personen = (p, q)

    def paar(self):
        return (self.p, self.q)

    def gilt(self, fall, pos):
        return self.ok2(fall, pos[self.p], pos[self.q])


class GleicherBereich(_Binaer):
    prio = 3

    def ok2(self, fall, za, zb):
        return fall.bereich(za) == fall.bereich(zb)

    def text(self, fall):
        return f"{_name(fall, self.p)} und {_name(fall, self.q)} waren im selben Bereich."


class AndererBereich(_Binaer):
    prio = 2

    def ok2(self, fall, za, zb):
        return fall.bereich(za) != fall.bereich(zb)

    def text(self, fall):
        return (f"{_name(fall, self.p)} und {_name(fall, self.q)} "
                f"waren in verschiedenen Bereichen.")


class Links(_Binaer):
    """p steht in einer Spalte weiter links als q."""
    prio = 3

    def __init__(self, p, q, umgekehrt=False):
        super().__init__(p, q)
        self.umgekehrt = umgekehrt   # nur für die Formulierung

    def ok2(self, fall, za, zb):
        return za[1] < zb[1]

    def text(self, fall):
        if self.umgekehrt:
            return f"{_name(fall, self.q)} befand sich weiter rechts als {_name(fall, self.p)}."
        return f"{_name(fall, self.p)} befand sich weiter links als {_name(fall, self.q)}."


class Oben(_Binaer):
    """p steht in einer Zeile weiter oben als q."""
    prio = 3

    def __init__(self, p, q, umgekehrt=False):
        super().__init__(p, q)
        self.umgekehrt = umgekehrt

    def ok2(self, fall, za, zb):
        return za[0] < zb[0]

    def text(self, fall):
        if self.umgekehrt:
            return f"{_name(fall, self.q)} befand sich weiter unten als {_name(fall, self.p)}."
        return f"{_name(fall, self.p)} befand sich weiter oben als {_name(fall, self.q)}."


class Schraeg(_Binaer):
    prio = 5

    def ok2(self, fall, za, zb):
        return abs(za[0] - zb[0]) == 1 and abs(za[1] - zb[1]) == 1

    def text(self, fall):
        return (f"{_name(fall, self.p)} und {_name(fall, self.q)} "
                f"befanden sich schräg nebeneinander.")
