"""Ein Fall = Plan (Bereiche), Gegenstände, Personen, Opfer und Geschichte.

Wird aus einer TOML-Datei unter faelle/ geladen.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .katalog import KATALOG, Objekt, eigenes_objekt

Zelle = tuple[int, int]   # (zeile, spalte), beide ab 0


@dataclass
class Bereich:
    kuerzel: str
    name: str
    praep: str      # "auf der Tribüne", "in der Kabine", ...
    farbe: str
    streifen: bool = False   # z. B. Rasen-Mähstreifen
    gesperrt: bool = False   # gehört nicht zum Rätsel (z. B. Nachbarwohnung): niemand war dort


@dataclass
class Person:
    name: str
    kurz: str
    bereich: str    # Kürzel des Bereichs, in dem die Person laut Lösung war
    opfer: bool = False
    # Formen für Sätze – wichtig, wenn das "Opfer" keine Person ist ("die Oliven")
    nominativ: str = ""
    dativ: str = ""
    akkusativ: str = ""
    mehrzahl: bool = False

    @property
    def nom(self) -> str:
        return self.nominativ or self.name

    @property
    def dat(self) -> str:
        return self.dativ or self.name

    @property
    def akk(self) -> str:
        return self.akkusativ or self.name


@dataclass
class Fall:
    nummer: int
    titel: str
    ort: str
    intro: str
    seed: int
    n: int
    bereiche: dict[str, Bereich]
    plan: list[str]                         # Bereichs-Kürzel je Zelle
    objekte: list[list[Objekt | None]]
    personen: list[Person]                  # Verdächtige zuerst, Opfer zuletzt
    schwierigkeit: str = "mittel"
    quelle: Path | None = None
    stil: dict = field(default_factory=dict)
    # Gegenstands-Stücke: ein Stück belegt 1 oder 2 Felder.
    # stueck_von[r][c] = Nummer des Stücks;
    # stuecke[i] = (kuerzel, [zellen], richtung "h"/"v"/None, drehung 0–3 Vierteldrehungen)
    stueck_von: list[list[int | None]] = field(default_factory=list)
    stuecke: list[tuple[str, list, str | None, int]] = field(default_factory=list)
    frage: str = ""      # "Wer hat Okon-Engstler mit Kölsch beworfen?"
    tat: str = ""        # "hat Okon-Engstler mit Kölsch beworfen"
    katalog: dict[str, Objekt] = field(default_factory=dict)

    # --- Geometrie -------------------------------------------------------
    @property
    def opfer_index(self) -> int:
        return len(self.personen) - 1

    def zellen(self):
        return [(r, c) for r in range(self.n) for c in range(self.n)]

    def bereich(self, z: Zelle) -> str:
        return self.plan[z[0]][z[1]]

    def objekt(self, z: Zelle) -> Objekt | None:
        return self.objekte[z[0]][z[1]]

    def besetzbar(self, z: Zelle) -> bool:
        if self.bereiche[self.bereich(z)].gesperrt:
            return False
        o = self.objekt(z)
        return o is None or o.besetzbar

    def nachbarn4(self, z: Zelle):
        r, c = z
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.n and 0 <= cc < self.n:
                yield (rr, cc)

    def nachbarn_im_bereich(self, z: Zelle):
        """Nachbarfelder (nicht schräg), die im selben Bereich liegen."""
        return [nz for nz in self.nachbarn4(z) if self.bereich(nz) == self.bereich(z)]

    def bereichs_zellen(self, b: str) -> set[Zelle]:
        return {z for z in self.zellen() if self.bereich(z) == b}

    def anzahl_objekt(self, kuerzel: str) -> int:
        """Anzahl der Stücke (ein 2-Felder-Bett zählt als ein Bett)."""
        return sum(1 for k, *_ in self.stuecke if k == kuerzel)

    def arten_neben(self, z: Zelle) -> set[str]:
        """Gegenstandsarten direkt neben z im selben Bereich – ohne das Stück,
        auf dem man selbst steht (die andere Hälfte des eigenen Betts zählt nicht)."""
        eigenes = self.stueck_von[z[0]][z[1]]
        return {self.objekt(nz).kuerzel for nz in self.nachbarn_im_bereich(z)
                if self.objekt(nz) and self.stueck_von[nz[0]][nz[1]] != eigenes}

    @staticmethod
    def koordinate(z: Zelle) -> str:
        return f"{'ABCDEFGHIJKL'[z[1]]}{z[0] + 1}"


def _kurzname(name: str, vergeben: set[str]) -> str:
    sauber = [ch for ch in name if ch.isalpha()]
    kandidaten = [sauber[0].upper() + sauber[1].lower()]
    kandidaten += [sauber[0].upper() + ch.lower() for ch in sauber[2:]]
    kandidaten += [sauber[0].upper() + str(i) for i in range(1, 10)]   # Notlösung: "P1"
    for k in kandidaten:
        if k not in vergeben:
            return k
    raise ValueError(f"Kein eindeutiges Kürzel für {name} – bitte 'kurz' angeben.")


def lade_fall(pfad: str | Path) -> Fall:
    pfad = Path(pfad)
    daten = tomllib.loads(pfad.read_text(encoding="utf-8"))

    bereiche = {
        k: Bereich(k, v["name"], v["praep"], v.get("farbe", "#eeeeee"),
                   v.get("streifen", False), v.get("gesperrt", False))
        for k, v in daten["bereiche"].items()
    }

    plan = [zeile.strip() for zeile in daten["plan"].strip().splitlines()]
    n = len(plan)
    if any(len(z) != n for z in plan):
        raise ValueError("Der Plan muss quadratisch sein.")
    for zeile in plan:
        for ch in zeile:
            if ch not in bereiche:
                raise ValueError(f"Unbekannter Bereich '{ch}' im Plan.")

    # Gegenstände: fester Katalog + eigene Gegenstände dieses Falls
    katalog = dict(KATALOG)
    for k, v in daten.get("gegenstaende", {}).items():
        katalog[k] = eigenes_objekt(k, v["name"], v.get("genus", "m"),
                                    v.get("besetzbar", False), v.get("verb", "stand auf"))

    # Schreibweise im Objekt-Raster:
    #   "Be"          Bett auf einem Feld
    #   "Be>" "Be<"   Bett über zwei Felder waagrecht (> zeigt zum Partner rechts)
    #   "Bev" / "Be^" Bett über zwei Felder senkrecht (Partner darunter)
    #   "@1" "@2" "@3" hinter dem (ersten) Kürzel dreht um 90°/180°/270° im
    #   Uhrzeigersinn, z. B. "Sd@1"; große Stücke lassen sich nur wenden ("Be>@2")
    zeilen = [z.split() for z in daten["objekte"].strip().splitlines()]
    if len(zeilen) != n or any(len(z) != n for z in zeilen):
        raise ValueError(f"Das Objekt-Raster muss {n} Zeilen mit je {n} Einträgen haben.")
    objekte: list[list[Objekt | None]] = [[None] * n for _ in range(n)]
    stueck_von: list[list[int | None]] = [[None] * n for _ in range(n)]
    stuecke: list[tuple[str, list, str | None, int]] = []
    partner = {">": (0, 1, "<"), "v": (1, 0, "^")}
    for r, zeile in enumerate(zeilen):
        for c, tok in enumerate(zeile):
            drehung = 0
            if "@" in tok:
                tok, d = tok.split("@", 1)
                if d not in ("1", "2", "3"):
                    raise ValueError(f"Drehung '@{d}' in {Fall.koordinate((r, c))}: "
                                     f"erlaubt sind @1, @2, @3.")
                drehung = int(d)
            if tok == ".." or tok[-1] in "<^":
                continue
            basis, suffix = (tok[:-1], tok[-1]) if tok[-1] in ">v" and len(tok) == 3 else (tok, "")
            if basis not in katalog:
                raise ValueError(f"Unbekannter Gegenstand '{tok}' in {Fall.koordinate((r, c))}. "
                                 f"Bitte in [gegenstaende] definieren oder Kürzel aus "
                                 f"krimi/katalog.py nehmen.")
            o = katalog[basis]
            zellen = [(r, c)]
            richtung = None
            if suffix:
                if o.icon2 is None:
                    raise ValueError(f"{o.name} kann nicht zwei Felder groß sein "
                                     f"({Fall.koordinate((r, c))}).")
                dr, dc, gegen = partner[suffix]
                rr, cc = r + dr, c + dc
                if rr >= n or cc >= n or zeilen[rr][cc] != basis + gegen:
                    raise ValueError(f"{o.name} in {Fall.koordinate((r, c))}: zweite Hälfte "
                                     f"'{basis + gegen}' fehlt daneben.")
                if plan[r][c] != plan[rr][cc]:
                    raise ValueError(f"{o.name} in {Fall.koordinate((r, c))} liegt über zwei "
                                     f"Bereichen – ein Gegenstand muss in einem Bereich liegen.")
                zellen.append((rr, cc))
                richtung = "h" if suffix == ">" else "v"
                if drehung in (1, 3):
                    raise ValueError(f"{o.name} in {Fall.koordinate((r, c))}: große Stücke "
                                     f"lassen sich nur wenden (@2), die Richtung legt > bzw. v fest.")
            for zr, zc in zellen:
                objekte[zr][zc] = o
                stueck_von[zr][zc] = len(stuecke)
            stuecke.append((basis, zellen, richtung, drehung))
    for r, zeile in enumerate(zeilen):
        for c, tok in enumerate(zeile):
            if tok != ".." and tok[-1] in "<^" and len(tok) == 3 and stueck_von[r][c] is None:
                raise ValueError(f"Halbes Stück '{tok}' in {Fall.koordinate((r, c))} ohne Anfang.")

    vergeben: set[str] = set()
    personen = []
    for p in daten["personen"]:
        kurz = p.get("kurz") or _kurzname(p["name"], vergeben)
        vergeben.add(kurz)
        personen.append(Person(p["name"], kurz, p["bereich"]))
    o = daten["opfer"]
    kurz = o.get("kurz") or _kurzname(o["name"], vergeben)
    personen.append(Person(o["name"], kurz, o["bereich"], opfer=True,
                           nominativ=o.get("nominativ", ""), dativ=o.get("dativ", ""),
                           akkusativ=o.get("akkusativ", ""), mehrzahl=o.get("mehrzahl", False)))
    for p in personen:
        if bereiche[p.bereich].gesperrt:
            raise ValueError(f"{p.name} steht im gesperrten Bereich "
                             f"„{bereiche[p.bereich].name}“ – dort darf niemand sein.")
    if len(personen) != n:
        raise ValueError(f"Bei einem {n}x{n}-Plan braucht es genau {n} Personen "
                         f"(inkl. Opfer), gefunden: {len(personen)}.")

    return Fall(
        nummer=daten.get("nummer", 1),
        titel=daten["titel"],
        ort=daten.get("ort", ""),
        intro=daten.get("intro", "").strip(),
        seed=daten.get("seed", 1),
        n=n,
        bereiche=bereiche,
        plan=plan,
        objekte=objekte,
        personen=personen,
        schwierigkeit=daten.get("schwierigkeit", "mittel"),
        quelle=pfad,
        stil=daten.get("stil", {}),
        frage=daten.get("frage", f"Wer war mit {o['name']} allein?"),
        tat=daten.get("tat", "war es").strip().rstrip(".!").strip(),
        katalog=katalog,
        stueck_von=stueck_von,
        stuecke=stuecke,
    )
