"""Setzt Rätsel als druckfertige HTML-Seiten (A4) – daraus wird das PDF.

Seiten:  Spielregeln · je Fall eine Rätselseite · Lösungen (mit Lösungsweg).

Farben und Schriften kommen aus der Tabelle [stil] des jeweiligen Falls, so
dass jedes Rätsel seinen eigenen Look haben kann.
"""

from __future__ import annotations

import html
from pathlib import Path

from .fall import Fall
from .generator import Raetsel
from .katalog import Objekt

ZELLE = 100
RAND = 56   # Platz für die Koordinaten A–H / 1–8
SCHRIFT_ORDNER = Path(__file__).resolve().parent.parent / "schriften"

# Verfügbare Schriften: Name -> [(Datei, Gewicht, Stil)]
SCHRIFTEN = {
    "Special Elite": [("SpecialElite-Regular.ttf", 400, "normal")],
    "Crimson Pro": [("CrimsonPro-Regular.ttf", 400, "normal"),
                    ("CrimsonPro-SemiBold.ttf", 600, "normal"),
                    ("CrimsonPro-Italic.ttf", 400, "italic")],
}

STANDARD_STIL = {
    "akzent": "#b3261e",          # Farbe für Überschriften-Details und das "Opfer"
    "tinte": "#231d17",           # Text- und Linienfarbe
    "titelschrift": "Special Elite",
    "textschrift": "Crimson Pro",
}


def _e(s: str) -> str:
    return html.escape(s, quote=True)


def stil_von(fall: Fall | None) -> dict:
    s = dict(STANDARD_STIL)
    if fall is not None:
        s.update(fall.stil)
    return s


def _stil_attr(fall: Fall | None) -> str:
    s = stil_von(fall)
    return (f'style="--akzent:{s["akzent"]};--tinte:{s["tinte"]};'
            f"--titel:'{s['titelschrift']}';--text:'{s['textschrift']}'\"")


# ---------------------------------------------------------------------------
# Plan als SVG
# ---------------------------------------------------------------------------

def plan_svg(fall: Fall, loesung: dict | None = None) -> str:
    n = fall.n
    breite = RAND + n * ZELLE + 12
    teile = [f'<svg class="plan" viewBox="0 0 {breite} {breite}" '
             f'xmlns="http://www.w3.org/2000/svg">']

    for r in range(n):
        for c in range(n):
            bereich = fall.bereiche[fall.plan[r][c]]
            x, y = RAND + c * ZELLE, RAND + r * ZELLE
            teile.append(f'<rect x="{x}" y="{y}" width="{ZELLE}" height="{ZELLE}" '
                         f'fill="{bereich.farbe}"/>')
            if bereich.streifen and c % 2 == 0:
                teile.append(f'<rect x="{x}" y="{y}" width="{ZELLE}" height="{ZELLE}" '
                             f'fill="#000" fill-opacity="0.045"/>')

    for i in range(1, n):
        p = RAND + i * ZELLE
        teile.append(f'<line x1="{p}" y1="{RAND}" x2="{p}" y2="{RAND + n * ZELLE}" class="raster"/>')
        teile.append(f'<line x1="{RAND}" y1="{p}" x2="{RAND + n * ZELLE}" y2="{p}" class="raster"/>')

    for kuerzel, zellen, richtung, drehung in fall.stuecke:
        o = fall.katalog[kuerzel]
        r, c = zellen[0]
        x, y = RAND + c * ZELLE, RAND + r * ZELLE
        teile.append(objekt_svg(o, x, y, richtung, drehung))

    for r in range(n):
        for c in range(n):
            x, y = RAND + c * ZELLE, RAND + r * ZELLE
            if c + 1 < n and fall.plan[r][c] != fall.plan[r][c + 1]:
                teile.append(f'<line x1="{x + ZELLE}" y1="{y}" x2="{x + ZELLE}" '
                             f'y2="{y + ZELLE}" class="grenze"/>')
            if r + 1 < n and fall.plan[r][c] != fall.plan[r + 1][c]:
                teile.append(f'<line x1="{x}" y1="{y + ZELLE}" x2="{x + ZELLE}" '
                             f'y2="{y + ZELLE}" class="grenze"/>')
    teile.append(f'<rect x="{RAND}" y="{RAND}" width="{n * ZELLE}" height="{n * ZELLE}" '
                 f'class="aussen"/>')

    for i in range(n):
        teile.append(f'<text x="{RAND + i * ZELLE + ZELLE / 2}" y="{RAND - 16}" '
                     f'class="koord">{"ABCDEFGHIJKL"[i]}</text>')
        teile.append(f'<text x="{RAND - 24}" y="{RAND + i * ZELLE + ZELLE / 2 + 11}" '
                     f'class="koord">{i + 1}</text>')

    if loesung:
        for p, (r, c) in loesung.items():
            person = fall.personen[p]
            cx, cy = RAND + c * ZELLE + ZELLE / 2, RAND + r * ZELLE + ZELLE / 2
            klasse = "kreis opfer" if person.opfer else "kreis"
            teile.append(f'<circle cx="{cx}" cy="{cy}" r="34" class="{klasse}"/>')
            teile.append(f'<text x="{cx}" y="{cy + 11}" class="marke">{_e(person.kurz)}</text>')

    teile.append("</svg>")
    return "".join(teile)


def objekt_svg(o: Objekt, x: float, y: float, richtung: str | None, drehung: int = 0) -> str:
    """Ein Stück auf dem Plan; (x, y) = linke obere Ecke des ersten Felds.
    drehung = Vierteldrehungen im Uhrzeigersinn (große Stücke: 0 oder 2)."""
    klasse = "obj frei" if o.besetzbar else "obj fest"
    if richtung is None:
        trafo = (f"translate({x + 50} {y + 50}) rotate({90 * drehung}) "
                 f"translate(-36 -36) scale(0.72)")
        return f'<g class="{klasse}" transform="{trafo}">{o.icon}</g>'
    # breites Icon (200 x 100), leicht eingerückt; senkrecht = um 90° gedreht
    if richtung == "h":
        mitte = (x + 100, y + 50)
        trafo = f"translate({x + 6} {y + 10}) scale(0.94 0.8)"
    else:
        mitte = (x + 50, y + 100)
        trafo = f"translate({x + 90} {y + 6}) rotate(90) scale(0.94 0.8)"
    if drehung:
        trafo = f"rotate({90 * drehung} {mitte[0]} {mitte[1]}) " + trafo
    return f'<g class="{klasse}" transform="{trafo}">{o.icon2}</g>'


def icon_svg(o: Objekt) -> str:
    klasse = "obj frei" if o.besetzbar else "obj fest"
    return f'<svg class="icon" viewBox="0 0 100 100"><g class="{klasse}">{o.icon}</g></svg>'


def _chip(person) -> str:
    klasse = "chip rot" if person.opfer else "chip"
    return f'<span class="{klasse}">{_e(person.kurz)}</span>'


# ---------------------------------------------------------------------------
# Seiten
# ---------------------------------------------------------------------------

def _seite_regeln(fall: Fall | None) -> str:
    return f"""
<section class="seite regeln" {_stil_attr(fall)}>
  <div class="kopf"><div class="akte">Vor dem ersten Fall</div>
  <h1>So wird ermittelt</h1></div>
  <p class="intro">In jedem Fall ist einem „Opfer“ etwas zugestoßen – mal ein Becher
  Kölsch, mal ein verschwundenes Plätzchen. Alle Beteiligten befanden sich in diesem
  Moment irgendwo auf dem Plan. Deine Aufgabe: Setze jede Person an ihren Platz und
  entlarve so den Übeltäter.</p>

  <h2>Die Regeln</h2>
  <ol class="regelliste">
    <li><b>Eine Person pro Zeile und Spalte.</b> In jeder Zeile und in jeder Spalte
        des Plans befindet sich genau eine Person – auch das „Opfer“.</li>
    <li><b>Wo man stehen kann.</b> Personen stehen auf freien Feldern oder auf
        Gegenständen mit <span class="ok">✓</span> (z.&nbsp;B. Sitz, Sessel, Bank). Felder mit
        Gegenständen mit <span class="nein">✕</span> (z.&nbsp;B. Tisch, Spind, Tor) sind blockiert.
        Die Legende auf jeder Fallseite zeigt, was was ist.</li>
    <li><b>Bereiche.</b> Dicke Linien teilen den Plan in Bereiche. Ein Bereich zählt
        als ein Raum – egal wie groß er ist.</li>
    <li><b>Der Übeltäter.</b> Es war die <i>einzige</i> Person, die sich mit dem
        „Opfer“ im selben Bereich befand. Im Bereich des „Opfers“ ist also genau eine
        weitere Person.</li>
    <li><b>Ein Hinweis pro Person.</b> Zu jeder verdächtigen Person gibt es genau
        einen Hinweis, und kein Hinweis kommt doppelt vor. Alle Hinweise sind wahr.
        Jeder Fall hat genau eine Lösung, und sie lässt sich ohne Raten finden.</li>
  </ol>

  <h2>Kleines Wörterbuch</h2>
  <dl class="woerter">
    <dt>direkt neben</dt><dd>auf einem Nachbarfeld links, rechts, darüber oder darunter
      – nicht schräg – und <i>im selben Bereich</i>. Bereichsgrenzen sind Wände:
      Wer auf der Tribüne steht, ist nie „neben dem Tor“.</dd>
    <dt>schräg nebeneinander</dt><dd>zwei Personen auf diagonal benachbarten Feldern im
      selben Bereich.</dd>
    <dt>weiter links / rechts</dt><dd>in irgendeiner Spalte weiter links bzw. rechts
      auf dem Plan – nicht unbedingt direkt daneben.</dd>
    <dt>weiter oben / unten</dt><dd>in irgendeiner Zeile weiter oben bzw. unten auf dem Plan.</dd>
    <dt>äußerer Rand</dt><dd>die äußerste Zeile oder Spalte des Plans.</dd>
    <dt>allein im Bereich</dt><dd>sonst niemand – auch nicht das „Opfer“ – war in diesem Bereich.</dd>
  </dl>

  <h2>Tipps</h2>
  <ul class="tipps">
    <li>Schreib die Kürzel der Personen mit Bleistift in die Felder und streiche
        Felder durch, die nicht in Frage kommen.</li>
    <li>Ist eine Person gesetzt, sind ihre ganze Zeile und Spalte für alle anderen tabu.</li>
    <li>Schau dir die Bereiche an: Zwei Personen, die beide in einen Bereich über
        nur zwei Zeilen müssen, belegen genau diese beiden Zeilen.</li>
    <li>Das „Opfer“ wird in keinem Hinweis erwähnt – es steht am Ende auf dem
        einzigen Feld, das noch übrig bleibt.</li>
    <li>Wer nicht weiterkommt, findet hinten im Buch zu jedem Fall einen kurzen
        Lösungsweg.</li>
  </ul>
</section>"""


def _seite_fall(r: Raetsel) -> str:
    f = r.fall
    verdaechtige = [p for p in f.personen if not p.opfer]
    opfer = f.personen[f.opfer_index]

    personen_html = "".join(f"<li>{_chip(p)}{_e(p.name)}</li>" for p in verdaechtige)
    personen_html += (f'<li class="opfer">{_chip(opfer)}{_e(opfer.name)} '
                      f'<small>(„Opfer“)</small></li>')

    bereiche_html = "".join(
        f'<li class="bereich"><span class="farbfeld" style="background:{b.farbe}"></span>'
        f'<span>{_e(b.name)}</span></li>'
        for b in f.bereiche.values())

    arten = []
    for z in f.zellen():
        o = f.objekt(z)
        if o and o.kuerzel not in arten:
            arten.append(o.kuerzel)
    kat = f.katalog
    arten.sort(key=lambda k: (not kat[k].besetzbar, kat[k].name))
    legende_html = "".join(
        f'<li>{icon_svg(kat[k])}<span>{_e(kat[k].name)}</span>'
        f'<span class="{"ok" if kat[k].besetzbar else "nein"}">'
        f'{"✓" if kat[k].besetzbar else "✕"}</span></li>' for k in arten)

    hinweise_html = "".join(
        f"<li>{_chip(f.personen[h.subjekt])}<span>{_e(r.text(h))}</span></li>"
        for h in sorted(r.hinweise, key=lambda h: h.subjekt))

    return f"""
<section class="seite fall" {_stil_attr(f)}>
  <div class="kopf">
    <div class="akte">Fall {f.nummer:02d} · {_e(f.schwierigkeit)}</div>
    <h1>{_e(f.titel)}</h1>
    <div class="ort">{_e(f.ort)}</div>
  </div>
  <p class="intro">{_e(f.intro)}</p>
  <p class="frage">{_e(f.frage)}</p>
  <div class="haupt">
    <figure>{plan_svg(f)}</figure>
    <aside>
      <h3>Personen</h3><ul class="personen">{personen_html}</ul>
    </aside>
  </div>
  <ul class="legende">{bereiche_html}{legende_html}</ul>
  <h2>Hinweise</h2>
  <ul class="hinweise">{hinweise_html}</ul>
  <div class="urteil"><span>Wer war's?</span><span class="linie"></span></div>
</section>"""


def _block_loesung(r: Raetsel) -> str:
    f = r.fall
    t = f.personen[r.taeter]
    o = f.personen[f.opfer_index]
    bereich = f.bereiche[f.bereich(r.loesung[f.opfer_index])]
    schritte = "".join(f"<li>{_e(s)}</li>" for s in r.schritte)
    return f"""
  <div class="loesungsblock" {_stil_attr(f)}>
    <h2>Fall {f.nummer:02d} · {_e(f.titel)}</h2>
    <div class="aufloesung"><b>{_e(t.name)}</b> {_e(f.tat)} – als einzige Person mit
      {_e(o.name)} {_e(bereich.praep)}.</div>
    <div class="loesung-inhalt">
      <figure class="klein">{plan_svg(f, r.loesung)}</figure>
      <div><h3>Lösungsweg</h3><ol class="schritte">{schritte}</ol></div>
    </div>
  </div>"""


def _hoehe_mm(r: Raetsel) -> float:
    """Grobe Höhe eines Lösungsblocks: Kopf + max(Plan, Text)."""
    zeilen = sum(1 + len(s) // 62 for s in r.schritte)
    return 24 + max(76, 8 + zeilen * 4.9)


def _seiten_loesungen(raetsel: list[Raetsel]) -> list[str]:
    seiten, aktuell, rest = [], [], 0.0
    nutzbar, kopf_hoehe = 266.0, 30.0
    for r in raetsel:
        h = _hoehe_mm(r)
        if aktuell and h > rest:
            seiten.append(aktuell)
            aktuell, rest = [], nutzbar
        if not seiten and not aktuell:
            rest = nutzbar - kopf_hoehe
        aktuell.append(r)
        rest -= h
    if aktuell:
        seiten.append(aktuell)
    html_seiten = []
    for i, gruppe in enumerate(seiten):
        kopf = ('<div class="kopf"><div class="akte">Akten geschlossen</div>'
                '<h1>Lösungen</h1></div>') if i == 0 else ""
        bloecke = "".join(_block_loesung(r) for r in gruppe)
        html_seiten.append(f'<section class="seite loesung" {_stil_attr(gruppe[0].fall)}>'
                           f'{kopf}{bloecke}</section>')
    return html_seiten


def _font_faces() -> str:
    regeln = []
    for name, dateien in SCHRIFTEN.items():
        for datei, gewicht, stil in dateien:
            pfad = SCHRIFT_ORDNER / datei
            if pfad.exists():
                regeln.append(f'@font-face {{ font-family: "{name}"; src: url("{pfad.as_uri()}"); '
                              f'font-weight: {gewicht}; font-style: {stil}; }}')
    return "\n".join(regeln)


def buch_html(raetsel: list[Raetsel], mit_regeln: bool = True) -> str:
    seiten = []
    if mit_regeln:
        seiten.append(_seite_regeln(raetsel[0].fall if raetsel else None))
    seiten += [_seite_fall(r) for r in raetsel]
    seiten += _seiten_loesungen(raetsel)
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Rätselbuch</title>
<style>
{_font_faces()}
{CSS}
</style></head><body>
{''.join(seiten)}
</body></html>"""


CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.seite { width: 210mm; height: 297mm; padding: 15mm 17mm 13mm; position: relative;
         overflow: hidden; page-break-after: always; break-after: page;
         font-family: var(--text), Georgia, serif; color: var(--tinte); font-size: 12.5pt;
         line-height: 1.32; }
.kopf { border-bottom: 2px solid var(--tinte); padding-bottom: 2.5mm; margin-bottom: 4mm; }
.akte { font-family: var(--titel), monospace; color: var(--akzent); letter-spacing: .12em;
        text-transform: uppercase; font-size: 10.5pt; }
h1 { font-family: var(--titel), monospace; font-weight: 400; font-size: 27pt;
     margin: 1mm 0 0; line-height: 1.1; }
.ort { font-style: italic; font-size: 12pt; margin-top: 1mm; }
h2 { font-family: var(--titel), monospace; font-weight: 400; font-size: 14pt;
     margin: 5mm 0 2mm; letter-spacing: .04em; }
h3 { font-family: var(--titel), monospace; font-weight: 400; font-size: 11pt;
     margin: 0 0 1.5mm; letter-spacing: .06em; text-transform: uppercase; }
.intro { font-style: italic; margin: 0 0 2mm; font-size: 12.5pt; }
.frage { font-family: var(--titel), monospace; color: var(--akzent); font-size: 13.5pt;
         margin: 0 0 4mm; }

.haupt { display: flex; gap: 6mm; align-items: flex-start; }
.haupt figure { margin: 0; width: 102mm; flex: none; }
.haupt aside { flex: 1; min-width: 0; }
.haupt aside ul { list-style: none; padding: 0; margin: 0 0 4mm; }
.plan { width: 100%; height: auto; display: block; }
.plan .raster { stroke: var(--tinte); stroke-opacity: .22; stroke-width: 1.6; }
.plan .grenze { stroke: var(--tinte); stroke-width: 7; stroke-linecap: round; }
.plan .aussen { fill: none; stroke: var(--tinte); stroke-width: 9; }
.plan .koord { font-family: var(--titel), monospace; font-size: 30px; fill: var(--tinte);
               text-anchor: middle; }
.plan .kreis { fill: var(--tinte); stroke: #fff; stroke-width: 5; }
.plan .kreis.opfer { fill: var(--akzent); }
.plan .marke { font-family: var(--titel), monospace; font-size: 31px; fill: #fff;
               text-anchor: middle; }
.obj path, .obj rect, .obj circle { fill: none; stroke: var(--tinte); stroke-width: 5;
               stroke-linejoin: round; stroke-linecap: round; }
.obj .f { fill: #ffffff; fill-opacity: .85; }
.obj .k { fill: var(--tinte); fill-opacity: .85; }
.obj .w { stroke: #f4efe6; stroke-width: 4; fill: none; }
.obj .n { stroke-width: 2.4; stroke-opacity: .8; }

.personen li { display: flex; align-items: center; gap: 2.2mm; margin-bottom: 1.3mm; }
.personen li.opfer { color: var(--akzent); }
.personen small { font-style: italic; }
.chip { display: inline-flex; align-items: center; justify-content: center; width: 7.2mm;
        height: 7.2mm; border-radius: 50%; background: var(--tinte); color: #fff; flex: none;
        font-family: var(--titel), monospace; font-size: 9.5pt; }
.chip.rot { background: var(--akzent); }
.bereiche li { display: flex; align-items: center; gap: 2.2mm; margin-bottom: 1mm; }
.farbfeld { width: 6mm; height: 4.2mm; border: 1.3px solid var(--tinte); display: inline-block; }
.legende { list-style: none; padding: 0; margin: 3mm 0 0; display: grid;
           grid-template-columns: repeat(4, 1fr); gap: .6mm 3mm; font-size: 11pt; }
.legende li { display: grid; grid-template-columns: 7mm 1fr auto; align-items: center;
              gap: 1.5mm; }
.legende li > span:last-child { margin-right: 2mm; }
.legende li.bereich { grid-template-columns: 7mm 1fr; }
.legende li.bereich .farbfeld { width: 7mm; height: 4.6mm; }
.icon { width: 7mm; height: 7mm; }
.ok { color: #2f6b2f; font-weight: 600; }
.nein { color: var(--akzent); font-weight: 600; }

.hinweise { list-style: none; margin: 0; padding: 0; }
.hinweise li { display: flex; align-items: center; gap: 3mm; margin-bottom: 1.3mm; }
.urteil { margin-top: 5mm; display: flex;
          gap: 3mm; align-items: baseline; font-family: var(--titel), monospace;
          font-size: 13pt; }
.urteil .linie { flex: 1; border-bottom: 1.5px dashed var(--tinte); max-width: 75mm; }

.regelliste li, .tipps li { margin-bottom: 2mm; }
.regelliste { padding-left: 6mm; }
.woerter { display: grid; grid-template-columns: 48mm 1fr; gap: 1.6mm 4mm; margin: 0; }
.woerter dt { font-weight: 600; }
.woerter dd { margin: 0; }

.loesungsblock { margin-bottom: 6mm; }
.loesungsblock h2 { margin-top: 2mm; }
.aufloesung { font-size: 13pt; margin: 0 0 3mm; }
.aufloesung b { color: var(--akzent); }
.loesung-inhalt { display: flex; gap: 6mm; align-items: flex-start; }
.loesung-inhalt figure.klein { margin: 0; width: 72mm; flex: none; }
.schritte { margin: 0; padding-left: 5.5mm; font-size: 10.5pt; line-height: 1.28; }
.schritte li { margin-bottom: 1mm; }
.schritte li::marker { font-family: var(--titel), monospace; color: var(--akzent); }
"""
