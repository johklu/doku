"""Ein Fall = Plan (Bereiche), Gegenstände, Personen, Opfer und Geschichte.

Wird aus einer TOML-Datei unter faelle/ geladen.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .katalog import KATALOG, Objekt

Zelle = tuple[int, int]   # (zeile, spalte), beide ab 0


@dataclass
class Bereich:
    kuerzel: str
    name: str
    praep: str      # "auf der Tribüne", "in der Kabine", ...
    farbe: str
    streifen: bool = False   # z. B. Rasen-Mähstreifen


@dataclass
class Person:
    name: str
    kurz: str
    bereich: str    # Kürzel des Bereichs, in dem die Person laut Lösung war
    opfer: bool = False


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
        o = self.objekt(z)
        return o is None or o.besetzbar

    def nachbarn4(self, z: Zelle):
        r, c = z
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.n and 0 <= cc < self.n:
                yield (rr, cc)

    def bereichs_zellen(self, b: str) -> set[Zelle]:
        return {z for z in self.zellen() if self.bereich(z) == b}

    def anzahl_objekt(self, kuerzel: str) -> int:
        return sum(1 for z in self.zellen()
                   if self.objekt(z) and self.objekt(z).kuerzel == kuerzel)

    @staticmethod
    def koordinate(z: Zelle) -> str:
        return f"{'ABCDEFGHIJKL'[z[1]]}{z[0] + 1}"


def _kurzname(name: str, vergeben: set[str]) -> str:
    sauber = [ch for ch in name if ch.isalpha()]
    kandidaten = [sauber[0].upper() + sauber[1].lower()]
    kandidaten += [sauber[0].upper() + ch.lower() for ch in sauber[2:]]
    for k in kandidaten:
        if k not in vergeben:
            return k
    raise ValueError(f"Kein eindeutiges Kürzel für {name}")


def lade_fall(pfad: str | Path) -> Fall:
    pfad = Path(pfad)
    daten = tomllib.loads(pfad.read_text(encoding="utf-8"))

    bereiche = {
        k: Bereich(k, v["name"], v["praep"], v.get("farbe", "#eeeeee"),
                   v.get("streifen", False))
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

    objekte: list[list[Objekt | None]] = []
    for zeile in daten["objekte"].strip().splitlines():
        teile = zeile.split()
        if len(teile) != n:
            raise ValueError(f"Objektzeile hat nicht {n} Einträge: {zeile!r}")
        objekte.append([None if t == ".." else KATALOG[t] for t in teile])
    if len(objekte) != n:
        raise ValueError("Objekt-Raster hat falsche Zeilenzahl.")

    vergeben: set[str] = set()
    personen = []
    for p in daten["personen"]:
        kurz = p.get("kurz") or _kurzname(p["name"], vergeben)
        vergeben.add(kurz)
        personen.append(Person(p["name"], kurz, p["bereich"]))
    o = daten["opfer"]
    kurz = o.get("kurz") or _kurzname(o["name"], vergeben)
    personen.append(Person(o["name"], kurz, o["bereich"], opfer=True))
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
    )
