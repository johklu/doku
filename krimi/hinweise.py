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
VERB_MEHRZAHL = {"befand": "befanden", "stand": "standen", "saß": "saßen",
                 "lag": "lagen", "war": "waren", "hatte": "hatten"}


class Hinweis:
    prio = 1
    personen: tuple[int, ...] = ()
    allein: int | None = None        # nur für Allein-Hinweise

    @property
    def subjekt(self) -> int:
        """Die Person, "zu der" der Hinweis gehört (steht am Satzanfang)."""
        return self.personen[0]

    # Für kombinierte Hinweise: "saß auf einem Sitz" + ", direkt neben ..."
    def praedikat(self, fall: Fall) -> str | None:
        return None

    def zusatz(self, fall: Fall) -> str | None:
        return None

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

    def _text(self, fall: Fall) -> str:
        raise NotImplementedError

    def text(self, fall: Fall) -> str:
        """Der fertige Satz. Ist das Subjekt ein "Opfer" mit eigenen Formen
        ("die Ovomaltine"), beginnt der Satz damit; bei Mehrzahl ("die Oliven")
        wird das Verb angepasst."""
        s = self._text(fall)
        person = fall.personen[self.subjekt]
        if person.nominativ and s.startswith(person.name + " "):
            rest = s[len(person.name) + 1:]
            if person.mehrzahl:
                verb, _, danach = rest.partition(" ")
                rest = VERB_MEHRZAHL.get(verb, verb) + " " + danach
            s = person.nominativ[:1].upper() + person.nominativ[1:] + " " + rest
        return s

    def schluessel(self):
        return (type(self).__name__,) + tuple(
            v for k, v in sorted(vars(self).items()))

    def bausteine(self) -> set[str]:
        """Kennungen der Aussage – zwei Hinweise mit gemeinsamer Kennung wären
        "derselbe Hinweis" und dürfen nicht zusammen in einem Rätsel stehen.
        Gegenstands-Hinweise zählen je Gegenstand ("neben einer Kamera"),
        alle anderen je Satzform ("schräg nebeneinander")."""
        k = getattr(self, "k", None)
        return {type(self).__name__ + (f":{k}" if k else "")}

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

    def praedikat(self, fall):
        return f"war {fall.bereiche[self.b].praep}"

    def _text(self, fall):
        return f"{_name(fall, self.p)} {self.praedikat(fall)}."


class NichtImBereich(Hinweis):
    prio = 2

    def __init__(self, p: int, b: str):
        self.p, self.b = p, b
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        return p != self.p or fall.bereich(z) != self.b

    def gilt(self, fall, pos):
        return fall.bereich(pos[self.p]) != self.b

    def _text(self, fall):
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

    def praedikat(self, fall):
        o = fall.katalog[self.k]
        return o.auf_best if fall.anzahl_objekt(self.k) == 1 else o.auf_unbest

    def _text(self, fall):
        return f"{_name(fall, self.p)} {self.praedikat(fall)}."


class NebenObjekt(Hinweis):
    prio = 4

    def __init__(self, p: int, k: str):
        self.p, self.k = p, k
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        if p != self.p:
            return True
        return self.k in fall.arten_neben(z)

    def gilt(self, fall, pos):
        return self.erlaubt(fall, self.p, pos[self.p])

    def zusatz(self, fall):
        o = fall.katalog[self.k]
        art = o.dat_best if fall.anzahl_objekt(self.k) == 1 else o.dat_unbest
        return f"direkt neben {art}"

    def _text(self, fall):
        return f"{_name(fall, self.p)} befand sich {self.zusatz(fall)}."


class NichtNebenObjekt(Hinweis):
    prio = 3

    def __init__(self, p: int, k: str):
        self.p, self.k = p, k
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        if p != self.p:
            return True
        return self.k not in fall.arten_neben(z)

    def gilt(self, fall, pos):
        return self.erlaubt(fall, self.p, pos[self.p])

    def _art(self, fall):
        o = fall.katalog[self.k]
        return o.dat_best if fall.anzahl_objekt(self.k) == 1 else o.dat_unbest

    def zusatz(self, fall):
        return f"aber nicht neben {self._art(fall)}"

    def _text(self, fall):
        return f"{_name(fall, self.p)} befand sich nicht neben {self._art(fall)}."


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

    def zusatz(self, fall):
        return "am äußeren Rand des Plans" if self.ja else "nicht am äußeren Rand des Plans"

    def _text(self, fall):
        return f"{_name(fall, self.p)} befand sich {self.zusatz(fall)}."


class InSpalte(Hinweis):
    """Person stand in einer bestimmten Spalte (Buchstabe am Planrand)."""
    prio = 2.5
    komma = False        # "saß auf einem Stuhl in Spalte C"

    def __init__(self, p: int, s: int):
        self.p, self.s = p, s
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        return p != self.p or z[1] == self.s

    def gilt(self, fall, pos):
        return pos[self.p][1] == self.s

    def zusatz(self, fall):
        return f"in Spalte {'ABCDEFGHIJKL'[self.s]}"

    def _text(self, fall):
        return f"{_name(fall, self.p)} befand sich {self.zusatz(fall)}."

    def bausteine(self):
        return {f"InSpalte:{self.s}"}


class InZeile(Hinweis):
    """Person stand in einer bestimmten Zeile (Zahl am Planrand)."""
    prio = 2.5
    komma = False

    def __init__(self, p: int, r: int):
        self.p, self.r = p, r
        self.personen = (p,)

    def erlaubt(self, fall, p, z):
        return p != self.p or z[0] == self.r

    def gilt(self, fall, pos):
        return pos[self.p][0] == self.r

    def zusatz(self, fall):
        return f"in Zeile {self.r + 1}"

    def _text(self, fall):
        return f"{_name(fall, self.p)} befand sich {self.zusatz(fall)}."

    def bausteine(self):
        return {f"InZeile:{self.r}"}


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

    def _text(self, fall):
        return fall.katalog[self.k].niemand

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

    def _text(self, fall):
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

    def _text(self, fall):
        return f"{_name(fall, self.p)} und {_name(fall, self.q)} waren im selben Bereich."


class AndererBereich(_Binaer):
    prio = 2

    def ok2(self, fall, za, zb):
        return fall.bereich(za) != fall.bereich(zb)

    def _text(self, fall):
        return (f"{_name(fall, self.p)} und {_name(fall, self.q)} "
                f"waren in verschiedenen Bereichen.")


class Links(_Binaer):
    @property
    def subjekt(self):
        return self.q if self.umgekehrt else self.p

    """p steht in einer Spalte weiter links als q."""
    prio = 3

    def __init__(self, p, q, umgekehrt=False):
        super().__init__(p, q)
        self.umgekehrt = umgekehrt   # nur für die Formulierung

    def ok2(self, fall, za, zb):
        return za[1] < zb[1]

    def zusatz(self, fall):
        if self.umgekehrt:
            return f"weiter rechts als {_name(fall, self.p)}"
        return f"weiter links als {_name(fall, self.q)}"

    def _text(self, fall):
        if self.umgekehrt:
            return f"{_name(fall, self.q)} befand sich weiter rechts als {_name(fall, self.p)}."
        return f"{_name(fall, self.p)} befand sich weiter links als {_name(fall, self.q)}."


class Oben(_Binaer):
    @property
    def subjekt(self):
        return self.q if self.umgekehrt else self.p

    """p steht in einer Zeile weiter oben als q."""
    prio = 3

    def __init__(self, p, q, umgekehrt=False):
        super().__init__(p, q)
        self.umgekehrt = umgekehrt

    def ok2(self, fall, za, zb):
        return za[0] < zb[0]

    def zusatz(self, fall):
        if self.umgekehrt:
            return f"weiter unten als {_name(fall, self.p)}"
        return f"weiter oben als {_name(fall, self.q)}"

    def _text(self, fall):
        if self.umgekehrt:
            return f"{_name(fall, self.q)} befand sich weiter unten als {_name(fall, self.p)}."
        return f"{_name(fall, self.p)} befand sich weiter oben als {_name(fall, self.q)}."


class Schraeg(_Binaer):
    prio = 5

    def ok2(self, fall, za, zb):
        return (abs(za[0] - zb[0]) == 1 and abs(za[1] - zb[1]) == 1
                and fall.bereich(za) == fall.bereich(zb))

    def _text(self, fall):
        return (f"{_name(fall, self.p)} und {_name(fall, self.q)} "
                f"befanden sich schräg nebeneinander.")


class Kombi(Hinweis):
    """Zwei Aussagen über dieselbe Person in einem Satz:
    "Leah saß auf einem Sitz, direkt neben einer Kamera."
    "Pete saß auf einem Stuhl, weiter oben als Leah." (zweiter Teil zweistellig)
    "Calzi saß auf einem Sessel in Spalte D." """
    prio = 3.5

    def __init__(self, a: Hinweis, b: Hinweis):
        self.a, self.b = a, b
        self.personen = a.personen

    def erlaubt(self, fall, p, z):
        return self.a.erlaubt(fall, p, z) and self.b.erlaubt(fall, p, z)

    def paar(self):
        return self.b.paar()

    def ok2(self, fall, za, zb):
        return self.b.ok2(fall, za, zb)

    def gilt(self, fall, pos):
        return self.a.gilt(fall, pos) and self.b.gilt(fall, pos)

    def _text(self, fall):
        trenner = ", " if getattr(self.b, "komma", True) else " "
        return f"{_name(fall, self.a.p)} {self.a.praedikat(fall)}{trenner}{self.b.zusatz(fall)}."

    def schluessel(self):
        return ("Kombi", self.a.schluessel(), self.b.schluessel())

    def bausteine(self):
        # Die Teile zählen einzeln: "saß auf einem Sitz, direkt neben einer Kamera"
        # schließt ein weiteres "direkt neben einer Kamera" aus.
        return self.a.bausteine() | self.b.bausteine()
