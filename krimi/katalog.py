"""Katalog aller Gegenstände, die auf einem Plan stehen können.

Jeder Gegenstand hat
  * ein Kürzel (zwei Zeichen), mit dem er im Fall-File im Objekt-Raster steht,
  * die deutschen Formen, die die Hinweistexte brauchen,
  * die Angabe, ob eine Person auf dem Feld stehen/sitzen kann (besetzbar),
  * ein kleines SVG-Icon (viewBox 0 0 100 100, Strichfarbe = currentColor).

Neue Gegenstände für neue Schauplätze einfach unten in KATALOG ergänzen.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Objekt:
    kuerzel: str
    name: str                 # "Sitz"
    besetzbar: bool
    dat_unbest: str           # "einem Sitz"   (für "neben einem Sitz")
    dat_best: str             # "dem Sitz"     (wenn es nur einen davon gibt)
    auf_unbest: str | None    # "saß auf einem Sitz"  (nur besetzbare)
    auf_best: str | None      # "saß auf dem Sitz"
    niemand: str | None       # "Kein Sitz war besetzt."
    icon: str
    icon2: str | None = None  # breites Icon (200x100) -> darf 2 Felder groß sein


def _o(kuerzel, name, besetzbar, dat_unbest, dat_best, auf_unbest=None,
       auf_best=None, niemand=None, icon=""):
    return Objekt(kuerzel, name, besetzbar, dat_unbest, dat_best, auf_unbest,
                  auf_best, niemand, icon)


# --- Icons -----------------------------------------------------------------
# Besetzbare Gegenstände: Umriss + helle Füllung.  Blockierende: kräftiger.

_SITZ = """
<path class="f" d="M31 16h38a7 7 0 0 1 7 7v31H24V23a7 7 0 0 1 7-7z"/>
<path class="f" d="M16 54h68v11a5 5 0 0 1-5 5H21a5 5 0 0 1-5-5z"/>
<path d="M28 70v16M72 70v16"/>"""

_SESSEL = """
<path class="f" d="M27 18h46a7 7 0 0 1 7 7v27H20V25a7 7 0 0 1 7-7z"/>
<rect class="f" x="9" y="42" width="18" height="34" rx="7"/>
<rect class="f" x="73" y="42" width="18" height="34" rx="7"/>
<rect class="f" x="27" y="54" width="46" height="22" rx="4"/>
<path d="M18 76v10M82 76v10"/>"""

_BANK = """
<rect class="f" x="6" y="40" width="88" height="13" rx="3"/>
<rect class="f" x="6" y="22" width="88" height="10" rx="3"/>
<path d="M14 32v8M86 32v8M18 53v28M82 53v28M12 81h12M76 81h12"/>"""

_DUSCHE = """
<path d="M20 90V24a12 12 0 0 1 12-12h16a12 12 0 0 1 12 12v8"/>
<path class="f" d="M44 32h32l-5 9H49z"/>
<path d="M51 50l-3 9M60 50v9M69 50l3 9M47 66l-3 9M60 66v9M73 66l3 9"/>"""

_BALL = """
<circle class="f" cx="50" cy="50" r="34"/>
<path class="k" d="M50 37l12.4 9-4.7 14.6H42.3L37.6 46z"/>
<path d="M50 37V16M62.4 46l19.5-6.3M57.7 60.6l12 16.6M42.3 60.6l-12 16.6M37.6 46l-19.5-6.3"/>"""

_TISCH = """
<rect class="k" x="8" y="32" width="84" height="12" rx="3"/>
<path d="M18 44v42M82 44v42M30 44l-6 20M70 44l6 20"/>"""

_PFLANZE = """
<path class="k" d="M33 64h34l-6 24H39z"/>
<path d="M50 64V30"/>
<path class="k" d="M50 50C37 49 27 39 24 24c15 2 24 12 26 26z"/>
<path class="k" d="M50 42c13-1 23-11 26-26-15 2-24 12-26 26z"/>
<path class="k" d="M50 60c-10 0-18-5-22-13 11-1 19 5 22 13z"/>"""

_BUFFET = """
<path class="k" d="M20 66a30 30 0 0 1 60 0z"/>
<circle class="k" cx="50" cy="31" r="5"/>
<path d="M10 66h80M16 76h68"/>"""

_SPIND = """
<rect class="k" x="27" y="8" width="46" height="84" rx="3"/>
<path class="w" d="M36 20h28M36 27h28M36 34h28M63 52v12"/>"""

_TOR = """
<path d="M10 84V20h80v64" stroke-width="7"/>
<path class="n" d="M10 20l12 12h56l12-12M22 32v52M78 32v52M36 32v52M50 32v52M64 32v52M22 47h56M22 62h56M22 77h56"/>"""

_KAMERA = """
<rect class="k" x="14" y="26" width="48" height="30" rx="4"/>
<path class="k" d="M62 33l22-9v34l-22-9z"/>
<rect class="k" x="20" y="15" width="16" height="11" rx="2"/>
<path d="M38 56L22 90M38 56v34M38 56l16 34"/>"""

_KOELSCH = """
<path class="k" d="M10 34L20 12h60l10 22z"/>
<path class="w" d="M30 13l-4 20M50 13v20M70 13l4 20"/>
<path d="M10 34c0 7 10 7 10 0c0 7 10 7 10 0c0 7 10 7 10 0c0 7 10 7 10 0c0 7 10 7 10 0c0 7 10 7 10 0c0 7 10 7 10 0c0 7 10 7 10 0"/>
<rect class="k" x="14" y="58" width="72" height="30" rx="2"/>
<path d="M22 41v17M78 41v17"/>
<path class="f" d="M44 36h12v20H44z"/>"""

_STUHL = """
<rect class="f" x="26" y="10" width="13" height="50" rx="3"/>
<rect class="f" x="26" y="50" width="50" height="11" rx="3"/>
<path d="M31 61v28M71 61v28"/>"""

_SOFA = """
<rect class="f" x="12" y="24" width="76" height="30" rx="7"/>
<rect class="f" x="4" y="42" width="17" height="32" rx="7"/>
<rect class="f" x="79" y="42" width="17" height="32" rx="7"/>
<rect class="f" x="21" y="54" width="29" height="20" rx="3"/>
<rect class="f" x="50" y="54" width="29" height="20" rx="3"/>
<path d="M14 74v12M86 74v12"/>"""

_BETT = """
<rect class="f" x="18" y="6" width="64" height="88" rx="6"/>
<rect class="f" x="28" y="13" width="44" height="17" rx="6"/>
<path d="M18 40h64M18 50h64"/>"""

_TEPPICH = """
<rect class="f" x="12" y="20" width="76" height="60" rx="2"/>
<rect x="22" y="30" width="56" height="40" rx="2"/>
<path d="M4 28h8M4 40h8M4 52h8M4 64h8M4 76h0M88 28h8M88 40h8M88 52h8M88 64h8"/>
<path d="M50 38l10 12-10 12-10-12z"/>"""

_BADEWANNE = """
<path class="f" d="M6 44h88v10a26 26 0 0 1-26 26H32A26 26 0 0 1 6 54z"/>
<path d="M82 44V22a8 8 0 0 0-16 0"/>
<path d="M24 80l-5 10M76 80l5 10"/>"""

_SCHRANK = """
<rect class="k" x="16" y="6" width="68" height="84" rx="3"/>
<path class="w" d="M50 6v84"/>
<path class="w" d="M43 44v10M57 44v10"/>
<path d="M22 90v6M78 90v6"/>"""

_KAMIN = """
<rect class="k" x="12" y="18" width="76" height="72"/>
<rect class="k" x="4" y="10" width="92" height="10" rx="2"/>
<path class="w" d="M28 90V58a22 22 0 0 1 44 0v32"/>
<path class="f" d="M50 86c-11 0-15-9-10-17 2 5 6 5 6 1 0-7 4-11 9-15 0 7 8 11 8 20 0 7-6 11-13 11z"/>"""

_WEIHNACHTSBAUM = """
<path class="k" d="M50 6L26 38h11L19 62h15L11 86h78L66 62h15L63 38h11z"/>
<rect class="k" x="43" y="86" width="14" height="10"/>
<circle class="w" cx="42" cy="50" r="3"/><circle class="w" cx="60" cy="70" r="3"/>
<circle class="w" cx="36" cy="76" r="3"/><circle class="w" cx="56" cy="32" r="3"/>"""

_HERD = """
<rect class="k" x="10" y="10" width="80" height="80" rx="4"/>
<circle class="w" cx="32" cy="32" r="11"/><circle class="w" cx="68" cy="32" r="11"/>
<circle class="w" cx="32" cy="68" r="11"/><circle class="w" cx="68" cy="68" r="11"/>"""

_FERNSEHER = """
<rect class="k" x="6" y="14" width="88" height="58" rx="4"/>
<rect class="f" x="14" y="22" width="72" height="42" rx="2"/>
<path d="M50 72v12M30 88h40"/>"""

_KUEHLSCHRANK = """
<rect class="k" x="24" y="4" width="52" height="90" rx="5"/>
<path class="w" d="M24 36h52M64 14v14M64 46v18"/>"""

_SCHREIBTISCH = """
<rect class="k" x="4" y="40" width="92" height="9" rx="2"/>
<rect class="k" x="58" y="49" width="32" height="40"/>
<path class="w" d="M63 62h22M63 76h22"/>
<path d="M12 49v40M22 40V24l14-8M36 16l6 6"/>"""

_WASCHBECKEN = """
<path class="k" d="M10 40h80c0 22-18 34-40 34S10 62 10 40z"/>
<path d="M50 40V22h16v8"/>
<rect class="k" x="43" y="74" width="14" height="20"/>"""

_REGAL = """
<path d="M14 4v92M86 4v92M14 30h72M14 56h72M14 82h72"/>
<rect class="k" x="20" y="10" width="8" height="20"/><rect class="k" x="30" y="14" width="7" height="16"/>
<rect class="k" x="40" y="8" width="9" height="22"/><rect class="k" x="56" y="38" width="8" height="18"/>
<rect class="k" x="66" y="40" width="9" height="16"/><rect class="k" x="22" y="64" width="18" height="18"/>
<rect class="k" x="64" y="62" width="8" height="20"/>"""

_INKUBATOR = """
<rect class="k" x="8" y="14" width="84" height="70" rx="6"/>
<rect class="w" x="18" y="24" width="46" height="50" rx="3"/>
<circle class="w" cx="78" cy="34" r="6"/>
<path class="w" d="M72 54h12M72 64h12"/>
<path d="M18 84v10M82 84v10"/>"""

_MIKROSKOP = """
<rect class="k" x="18" y="84" width="60" height="10" rx="2"/>
<path d="M68 84V58a26 26 0 0 0-24-26"/>
<path class="k" d="M30 8l12-5 16 40-12 5z"/>
<path d="M26 66h40M46 48l2 16"/>
<rect class="k" x="26" y="2" width="14" height="7" rx="2"/>"""

_THEKE = """
<rect class="k" x="2" y="34" width="96" height="9" rx="2"/>
<rect class="k" x="8" y="43" width="84" height="49"/>
<path class="w" d="M30 52v30M50 52v30M70 52v30"/>
<path class="f" d="M70 14h12l-2 20h-8z"/>"""

_FAHRRAD = """
<circle cx="24" cy="66" r="18"/><circle cx="78" cy="66" r="18"/>
<path d="M24 66l18-30h30l6 30M42 36l14 30h22M56 66L36 26M30 26h14M72 36l-4-12h10"/>
<circle class="k" cx="56" cy="66" r="4"/>"""

_TOILETTE = """
<rect class="f" x="60" y="8" width="26" height="34" rx="4"/>
<path class="f" d="M14 42h72v8c0 18-14 28-34 28h-6C24 78 14 66 14 50z"/>
<path class="f" d="M34 76h28l4 16H30z"/>
<path d="M14 42h50"/>"""

# --- Breite Icons für Gegenstände über zwei Felder (200 x 100, waagrecht) ---

_BETT2 = """
<rect class="f" x="14" y="16" width="174" height="68" rx="8"/>
<rect class="k" x="8" y="10" width="12" height="80" rx="3"/>
<rect class="f" x="28" y="26" width="32" height="48" rx="9"/>
<path d="M80 16v68M80 16l18 18v50"/>"""

_SOFA2 = """
<rect class="f" x="10" y="14" width="180" height="72" rx="10"/>
<rect class="f" x="10" y="14" width="180" height="22" rx="8"/>
<rect class="f" x="10" y="14" width="22" height="72" rx="8"/>
<rect class="f" x="168" y="14" width="22" height="72" rx="8"/>
<path d="M100 36v50"/>"""

_TISCH2 = """
<rect class="k" x="12" y="20" width="176" height="60" rx="6"/>
<rect class="w" x="22" y="30" width="156" height="40" rx="3"/>"""

_TEPPICH2 = """
<rect class="f" x="18" y="16" width="164" height="68" rx="2"/>
<rect x="30" y="28" width="140" height="44" rx="2"/>
<path d="M72 50l14-14 14 14-14 14zM114 50l14-14 14 14-14 14z"/>
<path d="M8 24h10M8 38h10M8 52h10M8 66h10M8 80h0M182 24h10M182 38h10M182 52h10M182 66h10"/>"""


KATALOG: dict[str, Objekt] = {o.kuerzel: o for o in [
    # besetzbar
    _o("Si", "Sitz", True, "einem Sitz", "dem Sitz",
       "saß auf einem Sitz", "saß auf dem Sitz",
       "Kein einziger Sitz war besetzt.", _SITZ),
    _o("Se", "Sessel", True, "einem Sessel", "dem Sessel",
       "saß in einem Sessel", "saß im Sessel",
       "Kein Sessel war besetzt.", _SESSEL),
    _o("Ba", "Bank", True, "einer Bank", "der Bank",
       "saß auf einer Bank", "saß auf der Bank",
       "Niemand saß auf einer Bank.", _BANK),
    _o("Du", "Dusche", True, "einer Dusche", "der Dusche",
       "stand unter einer Dusche", "stand unter der Dusche",
       "Niemand stand unter einer Dusche.", _DUSCHE),
    _o("Bl", "Ball", True, "einem Ball", "dem Ball",
       "stand am Ball", "stand am Ball",
       "Niemand stand am Ball.", _BALL),
    _o("St", "Stuhl", True, "einem Stuhl", "dem Stuhl",
       "saß auf einem Stuhl", "saß auf dem Stuhl", "Kein Stuhl war besetzt.", _STUHL),
    _o("So", "Sofa", True, "einem Sofa", "dem Sofa",
       "saß auf einem Sofa", "saß auf dem Sofa", "Niemand saß auf einem Sofa.", _SOFA),
    _o("Be", "Bett", True, "einem Bett", "dem Bett",
       "lag in einem Bett", "lag im Bett", "Niemand lag in einem Bett.", _BETT),
    _o("Te", "Teppich", True, "einem Teppich", "dem Teppich",
       "stand auf einem Teppich", "stand auf dem Teppich",
       "Niemand stand auf einem Teppich.", _TEPPICH),
    _o("Bw", "Badewanne", True, "einer Badewanne", "der Badewanne",
       "saß in einer Badewanne", "saß in der Badewanne",
       "Niemand saß in einer Badewanne.", _BADEWANNE),
    # blockierend
    _o("Ti", "Tisch", False, "einem Tisch", "dem Tisch", icon=_TISCH),
    _o("Pf", "Pflanze", False, "einer Pflanze", "der Pflanze", icon=_PFLANZE),
    _o("Bu", "Buffet", False, "einem Buffet", "dem Buffet", icon=_BUFFET),
    _o("Sp", "Spind", False, "einem Spind", "dem Spind", icon=_SPIND),
    _o("To", "Tor", False, "einem Tor", "dem Tor", icon=_TOR),
    _o("Ka", "Kamera", False, "einer Kamera", "der Kamera", icon=_KAMERA),
    _o("Kö", "Kölschstand", False, "einem Kölschstand", "dem Kölschstand",
       icon=_KOELSCH),
    _o("Sr", "Schrank", False, "einem Schrank", "dem Schrank", icon=_SCHRANK),
    _o("Km", "Kamin", False, "einem Kamin", "dem Kamin", icon=_KAMIN),
    _o("Wb", "Weihnachtsbaum", False, "einem Weihnachtsbaum", "dem Weihnachtsbaum",
       icon=_WEIHNACHTSBAUM),
    _o("He", "Herd", False, "einem Herd", "dem Herd", icon=_HERD),
    _o("Fe", "Fernseher", False, "einem Fernseher", "dem Fernseher", icon=_FERNSEHER),
    _o("Kü", "Kühlschrank", False, "einem Kühlschrank", "dem Kühlschrank", icon=_KUEHLSCHRANK),
    _o("Sd", "Schreibtisch", False, "einem Schreibtisch", "dem Schreibtisch", icon=_SCHREIBTISCH),
    _o("Wa", "Waschbecken", False, "einem Waschbecken", "dem Waschbecken", icon=_WASCHBECKEN),
    _o("Rg", "Regal", False, "einem Regal", "dem Regal", icon=_REGAL),
    _o("In", "Inkubator", False, "einem Inkubator", "dem Inkubator", icon=_INKUBATOR),
    _o("Mi", "Mikroskop", False, "einem Mikroskop", "dem Mikroskop", icon=_MIKROSKOP),
    _o("Th", "Theke", False, "einer Theke", "der Theke", icon=_THEKE),
    # besetzbar (hier unten, damit die Reihenfolge oben stabil bleibt)
    _o("Fa", "Fahrrad", True, "einem Fahrrad", "dem Fahrrad",
       "saß auf einem Fahrrad", "saß auf dem Fahrrad", "Niemand saß auf einem Fahrrad.", _FAHRRAD),
    _o("Wc", "Toilette", True, "einer Toilette", "der Toilette",
       "saß auf einer Toilette", "saß auf der Toilette", "Niemand saß auf einer Toilette.", _TOILETTE),
]}

# Diese Gegenstände dürfen 1 oder 2 Felder groß sein
for _k, _breit in {"Be": _BETT2, "So": _SOFA2, "Ti": _TISCH2, "Te": _TEPPICH2}.items():
    KATALOG[_k] = replace(KATALOG[_k], icon2=_breit)


def eigenes_objekt(kuerzel: str, name: str, genus: str = "m", besetzbar: bool = False,
                   verb: str = "stand auf") -> Objekt:
    """Gegenstand, der nur in einem Fall vorkommt (Tabelle [gegenstaende]).

    genus: "m" (der), "f" (die) oder "n" (das)
    verb:  wie man darauf/darin ist, z. B. "saß auf", "lag in", "stand an"
    Bis ein eigenes Icon gezeichnet ist, zeigt der Plan das Kürzel.
    """
    weiblich = genus == "f"
    unbest = "einer" if weiblich else "einem"
    best = "der" if weiblich else "dem"
    auf_unbest = auf_best = None
    if besetzbar:
        auf_unbest = f"{verb} {unbest} {name}"
        auf_best = f"{verb} {best} {name}"
        if not weiblich:   # in dem -> im, an dem -> am
            auf_best = auf_best.replace(" in dem ", " im ").replace(" an dem ", " am ")
    icon = (f'<rect class="f" x="8" y="8" width="84" height="84" rx="14"/>'
            f'<text x="50" y="63" text-anchor="middle" font-size="40" '
            f'font-family="sans-serif" fill="#231d17">{kuerzel}</text>')
    return Objekt(kuerzel, name, besetzbar, f"{unbest} {name}", f"{best} {name}",
                  auf_unbest, auf_best, None, icon)
