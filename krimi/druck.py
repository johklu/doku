"""Setzt Rätsel als druckfertige HTML-Seiten (A4) – daraus wird das PDF.

Seiten:  Spielregeln · je Fall eine Rätselseite · Lösungsseiten am Ende.
"""

from __future__ import annotations

import html
from pathlib import Path

from .fall import Fall
from .generator import Raetsel
from .katalog import KATALOG

TINTE = "#231d17"
ROT = "#b3261e"
ZELLE = 100
RAND = 56   # Platz für die Koordinaten A–H / 1–8


def _e(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------------------
# Plan als SVG
# ---------------------------------------------------------------------------

def plan_svg(fall: Fall, loesung: dict | None = None, opfer_rot: bool = True) -> str:
    n = fall.n
    breite = RAND + n * ZELLE + 12
    teile = [f'<svg class="plan" viewBox="0 0 {breite} {breite}" '
             f'xmlns="http://www.w3.org/2000/svg">']

    # Bereichsfarben
    for r in range(n):
        for c in range(n):
            farbe = fall.bereiche[fall.plan[r][c]].farbe
            teile.append(f'<rect x="{RAND + c * ZELLE}" y="{RAND + r * ZELLE}" '
                         f'width="{ZELLE}" height="{ZELLE}" fill="{farbe}"/>')
            if fall.bereiche[fall.plan[r][c]].streifen and c % 2 == 0:
                # Rasen-Mähstreifen
                teile.append(f'<rect x="{RAND + c * ZELLE}" y="{RAND + r * ZELLE}" '
                             f'width="{ZELLE}" height="{ZELLE}" fill="#000" '
                             f'fill-opacity="0.045"/>')

    # feines Raster
    for i in range(1, n):
        p = RAND + i * ZELLE
        teile.append(f'<line x1="{p}" y1="{RAND}" x2="{p}" y2="{RAND + n * ZELLE}" class="raster"/>')
        teile.append(f'<line x1="{RAND}" y1="{p}" x2="{RAND + n * ZELLE}" y2="{p}" class="raster"/>')

    # Gegenstände
    for r in range(n):
        for c in range(n):
            o = fall.objekte[r][c]
            if o is None:
                continue
            x, y = RAND + c * ZELLE + 14, RAND + r * ZELLE + 14
            klasse = "obj frei" if o.besetzbar else "obj fest"
            teile.append(f'<g class="{klasse}" transform="translate({x} {y}) scale(0.72)">'
                         f'{o.icon}</g>')

    # Bereichsgrenzen (dicke Linien)
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

    # Koordinaten
    for i in range(n):
        teile.append(f'<text x="{RAND + i * ZELLE + ZELLE / 2}" y="{RAND - 16}" '
                     f'class="koord">{"ABCDEFGHIJKL"[i]}</text>')
        teile.append(f'<text x="{RAND - 24}" y="{RAND + i * ZELLE + ZELLE / 2 + 11}" '
                     f'class="koord">{i + 1}</text>')

    # Lösung eintragen
    if loesung:
        for p, (r, c) in loesung.items():
            person = fall.personen[p]
            cx, cy = RAND + c * ZELLE + ZELLE / 2, RAND + r * ZELLE + ZELLE / 2
            farbe = ROT if (person.opfer and opfer_rot) else TINTE
            teile.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="{farbe}" '
                         f'stroke="#fff" stroke-width="5"/>')
            teile.append(f'<text x="{cx}" y="{cy + 11}" class="marke">{_e(person.kurz)}</text>')

    teile.append("</svg>")
    return "".join(teile)


def icon_svg(kuerzel: str) -> str:
    o = KATALOG[kuerzel]
    klasse = "obj frei" if o.besetzbar else "obj fest"
    return (f'<svg class="icon" viewBox="0 0 100 100"><g class="{klasse}">{o.icon}</g></svg>')


# ---------------------------------------------------------------------------
# Seiten
# ---------------------------------------------------------------------------

def _seite_regeln() -> str:
    return f"""
<section class="seite regeln">
  <div class="kopf"><div class="akte">Vor dem ersten Fall</div>
  <h1>So wird ermittelt</h1></div>
  <p class="intro">In jedem Fall ist ein Mensch zu Tode gekommen. Alle Beteiligten
  standen zur Tatzeit irgendwo auf dem Plan – deine Aufgabe ist es, jede Person an
  ihren Platz zu setzen und so den Täter zu entlarven.</p>

  <h2>Die Regeln</h2>
  <ol class="regelliste">
    <li><b>Eine Person pro Zeile und Spalte.</b> In jeder Zeile und in jeder Spalte
        des Plans befindet sich genau eine Person – auch das Opfer.</li>
    <li><b>Wo man stehen kann.</b> Personen stehen auf freien Feldern oder auf
        Gegenständen mit <span class="ok">✓</span> (z.&nbsp;B. Sitz, Sessel, Bank). Felder mit
        Gegenständen mit <span class="nein">✕</span> (z.&nbsp;B. Tisch, Spind, Tor) sind blockiert.
        Die Legende auf jeder Fallseite zeigt, was was ist.</li>
    <li><b>Bereiche.</b> Dicke Linien teilen den Plan in Bereiche. Ein Bereich zählt
        als ein Raum – egal wie groß er ist.</li>
    <li><b>Der Täter.</b> Der Täter ist die <i>einzige</i> Person, die sich mit dem
        Opfer im selben Bereich befand. Im Bereich des Opfers ist also genau eine
        weitere Person.</li>
    <li><b>Die Hinweise sind alle wahr.</b> Jeder Fall hat genau eine Lösung, und
        sie lässt sich ohne Raten finden.</li>
  </ol>

  <h2>Kleines Wörterbuch</h2>
  <dl class="woerter">
    <dt>direkt neben</dt><dd>auf einem Nachbarfeld links, rechts, darüber oder darunter
      – nicht schräg.</dd>
    <dt>schräg nebeneinander</dt><dd>zwei Personen auf diagonal benachbarten Feldern.</dd>
    <dt>weiter links / rechts</dt><dd>in irgendeiner Spalte weiter links bzw. rechts
      auf dem Plan – nicht unbedingt direkt daneben.</dd>
    <dt>weiter oben / unten</dt><dd>in irgendeiner Zeile weiter oben bzw. unten auf dem Plan.</dd>
    <dt>äußerer Rand</dt><dd>die äußerste Zeile oder Spalte des Plans.</dd>
    <dt>allein im Bereich</dt><dd>sonst niemand – auch nicht das Opfer – war in diesem Bereich.</dd>
  </dl>

  <h2>Tipps</h2>
  <ul class="tipps">
    <li>Schreib die Kürzel der Personen mit Bleistift in die Felder und streiche
        Felder durch, die nicht in Frage kommen.</li>
    <li>Ist eine Person gesetzt, sind ihre ganze Zeile und Spalte für alle anderen tabu.</li>
    <li>Das Opfer wird in keinem Hinweis erwähnt – es steht am Ende auf dem
        einzigen Feld, das noch übrig bleibt.</li>
  </ul>
</section>"""


def _seite_fall(r: Raetsel) -> str:
    f = r.fall
    verdaechtige = [p for p in f.personen if not p.opfer]
    opfer = f.personen[f.opfer_index]

    personen_html = "".join(
        f'<li><span class="chip">{_e(p.kurz)}</span>{_e(p.name)}</li>' for p in verdaechtige)
    personen_html += (f'<li class="opfer"><span class="chip rot">{_e(opfer.kurz)}</span>'
                      f'{_e(opfer.name)} <small>(Opfer)</small></li>')

    bereiche_html = "".join(
        f'<li><span class="farbfeld" style="background:{b.farbe}"></span>{_e(b.name)}</li>'
        for b in f.bereiche.values())

    arten = []
    for z in f.zellen():
        o = f.objekt(z)
        if o and o.kuerzel not in arten:
            arten.append(o.kuerzel)
    arten.sort(key=lambda k: (not KATALOG[k].besetzbar, KATALOG[k].name))
    legende_html = "".join(
        f'<li>{icon_svg(k)}<span>{_e(KATALOG[k].name)}</span>'
        f'<span class="{"ok" if KATALOG[k].besetzbar else "nein"}">'
        f'{"✓" if KATALOG[k].besetzbar else "✕"}</span></li>' for k in arten)

    hinweise_html = "".join(f"<li>{_e(h.text(f))}</li>" for h in r.hinweise)
    spalten = " zweispaltig" if len(r.hinweise) > 9 else ""

    return f"""
<section class="seite fall">
  <div class="kopf">
    <div class="akte">Fall {f.nummer:02d} · {_e(f.schwierigkeit)}</div>
    <h1>{_e(f.titel)}</h1>
    <div class="ort">{_e(f.ort)}</div>
  </div>
  <p class="intro">{_e(f.intro)}</p>
  <div class="haupt">
    <figure>{plan_svg(f)}</figure>
    <aside>
      <h3>Personen</h3><ul class="personen">{personen_html}</ul>
      <h3>Bereiche</h3><ul class="bereiche">{bereiche_html}</ul>
    </aside>
  </div>
  <ul class="legende">{legende_html}</ul>
  <h2>Hinweise</h2>
  <ol class="hinweise{spalten}">{hinweise_html}</ol>
  <div class="urteil"><span>Täter:</span><span class="linie"></span></div>
</section>"""


def _block_loesung(r: Raetsel) -> str:
    f = r.fall
    t = f.personen[r.taeter]
    o = f.personen[f.opfer_index]
    bereich = f.bereiche[f.bereich(r.loesung[f.opfer_index])]
    zeilen = "".join(
        f"<tr><td><span class='chip{' rot' if p.opfer else ''}'>{_e(p.kurz)}</span>{_e(p.name)}</td>"
        f"<td>{f.koordinate(r.loesung[i])}</td>"
        f"<td>{_e(f.bereiche[f.bereich(r.loesung[i])].name)}</td></tr>"
        for i, p in enumerate(f.personen))
    return f"""
  <div class="loesungsblock">
    <h2>Fall {f.nummer:02d} · {_e(f.titel)}</h2>
    <div class="aufloesung">Es war <b>{_e(t.name)}</b> – als einzige Person mit
      {_e(o.name)} {_e(bereich.praep)}.</div>
    <div class="haupt">
      <figure class="klein">{plan_svg(f, r.loesung)}</figure>
      <aside><table class="positionen"><tbody>{zeilen}</tbody></table></aside>
    </div>
  </div>"""


def _seiten_loesungen(raetsel: list[Raetsel], je_seite: int = 2) -> list[str]:
    seiten = []
    for i in range(0, len(raetsel), je_seite):
        bloecke = "".join(_block_loesung(r) for r in raetsel[i:i + je_seite])
        kopf = ('<div class="kopf"><div class="akte">Akten geschlossen</div>'
                '<h1>Lösungen</h1></div>') if i == 0 else ""
        seiten.append(f'<section class="seite loesung">{kopf}{bloecke}</section>')
    return seiten


def buch_html(raetsel: list[Raetsel], mit_regeln: bool = True) -> str:
    schriften = (Path(__file__).resolve().parent.parent / "schriften").as_uri()
    seiten = []
    if mit_regeln:
        seiten.append(_seite_regeln())
    seiten += [_seite_fall(r) for r in raetsel]
    seiten += _seiten_loesungen(raetsel)
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Mordsrätsel</title>
<style>
@font-face {{ font-family: "Special Elite"; src: url("{schriften}/SpecialElite-Regular.ttf"); }}
@font-face {{ font-family: "Crimson Pro"; src: url("{schriften}/CrimsonPro-Regular.ttf"); font-weight: 400; }}
@font-face {{ font-family: "Crimson Pro"; src: url("{schriften}/CrimsonPro-SemiBold.ttf"); font-weight: 600; }}
@font-face {{ font-family: "Crimson Pro"; src: url("{schriften}/CrimsonPro-Italic.ttf"); font-style: italic; }}
{CSS}
</style></head><body>
{''.join(seiten)}
</body></html>"""


CSS = f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
body {{ font-family: "Crimson Pro", Georgia, serif; color: {TINTE}; font-size: 12.5pt;
        line-height: 1.32; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.seite {{ width: 210mm; height: 297mm; padding: 15mm 17mm 13mm; position: relative;
          overflow: hidden; page-break-after: always; break-after: page; }}
.kopf {{ border-bottom: 2px solid {TINTE}; padding-bottom: 2.5mm; margin-bottom: 4mm; }}
.akte {{ font-family: "Special Elite", monospace; color: {ROT}; letter-spacing: .12em;
         text-transform: uppercase; font-size: 10.5pt; }}
h1 {{ font-family: "Special Elite", monospace; font-weight: 400; font-size: 27pt;
      margin: 1mm 0 0; line-height: 1.1; }}
.ort {{ font-style: italic; font-size: 12pt; margin-top: 1mm; }}
h2 {{ font-family: "Special Elite", monospace; font-weight: 400; font-size: 14pt;
      margin: 5mm 0 2mm; letter-spacing: .04em; }}
h3 {{ font-family: "Special Elite", monospace; font-weight: 400; font-size: 11pt;
      margin: 0 0 1.5mm; letter-spacing: .06em; text-transform: uppercase; }}
.intro {{ font-style: italic; margin: 0 0 4mm; font-size: 12.5pt; }}

.haupt {{ display: flex; gap: 6mm; align-items: flex-start; }}
.haupt figure {{ margin: 0; width: 116mm; flex: none; }}
.haupt aside {{ flex: 1; min-width: 0; }}
.haupt aside ul {{ list-style: none; padding: 0; margin: 0 0 4mm; }}
.plan {{ width: 100%; height: auto; display: block; }}
.plan .raster {{ stroke: {TINTE}; stroke-opacity: .22; stroke-width: 1.6; }}
.plan .grenze {{ stroke: {TINTE}; stroke-width: 7; stroke-linecap: round; }}
.plan .aussen {{ fill: none; stroke: {TINTE}; stroke-width: 9; }}
.plan .koord {{ font-family: "Special Elite", monospace; font-size: 30px; fill: {TINTE};
               text-anchor: middle; }}
.plan .marke {{ font-family: "Special Elite", monospace; font-size: 31px; fill: #fff;
               text-anchor: middle; }}
.obj path, .obj rect, .obj circle {{ fill: none; stroke: #3a3129; stroke-width: 5;
               stroke-linejoin: round; stroke-linecap: round; }}
.obj .f {{ fill: #ffffff; fill-opacity: .85; }}
.obj .k {{ fill: #4a4037; }}
.obj .w {{ stroke: #f4efe6; stroke-width: 4; fill: none; }}
.obj .n {{ stroke-width: 2.4; stroke-opacity: .8; }}

.personen li {{ display: flex; align-items: center; gap: 2.2mm; margin-bottom: 1.3mm; }}
.personen li.opfer {{ color: {ROT}; }}
.personen small {{ font-style: italic; }}
.chip {{ display: inline-flex; align-items: center; justify-content: center; width: 7.2mm;
         height: 7.2mm; border-radius: 50%; background: {TINTE}; color: #fff; flex: none;
         font-family: "Special Elite", monospace; font-size: 9.5pt; margin-right: 2mm; }}
.personen .chip {{ margin-right: 0; }}
.chip.rot {{ background: {ROT}; }}
.bereiche li {{ display: flex; align-items: center; gap: 2.2mm; margin-bottom: 1mm; }}
.farbfeld {{ width: 6mm; height: 4.2mm; border: 1.3px solid {TINTE}; display: inline-block; }}
.legende {{ list-style: none; padding: 0; margin: 3mm 0 0; display: grid;
            grid-template-columns: repeat(4, 1fr); gap: .6mm 3mm; font-size: 11pt; }}
.legende li {{ display: grid; grid-template-columns: 7mm 1fr auto; align-items: center;
               gap: 1.5mm; }}
.legende li > span:last-child {{ margin-right: 2mm; }}
.icon {{ width: 7mm; height: 7mm; }}
.ok {{ color: #2f6b2f; font-weight: 600; }}
.nein {{ color: {ROT}; font-weight: 600; }}

.hinweise {{ margin: 0; padding-left: 6mm; }}
.hinweise li {{ margin-bottom: 1.4mm; padding-left: 1mm; break-inside: avoid; }}
.hinweise li::marker {{ font-family: "Special Elite", monospace; color: {ROT}; }}
.hinweise.zweispaltig {{ columns: 2; column-gap: 9mm; }}
.urteil {{ position: absolute; left: 17mm; right: 17mm; bottom: 14mm; display: flex;
           gap: 3mm; align-items: baseline; font-family: "Special Elite", monospace;
           font-size: 13pt; }}
.urteil .linie {{ flex: 1; border-bottom: 1.5px dashed {TINTE}; max-width: 75mm; }}

.regelliste li, .tipps li {{ margin-bottom: 2.2mm; }}
.regelliste {{ padding-left: 6mm; }}
.woerter {{ display: grid; grid-template-columns: 48mm 1fr; gap: 1.6mm 4mm; margin: 0; }}
.woerter dt {{ font-weight: 600; }}
.woerter dd {{ margin: 0; }}

.loesungsblock {{ margin-bottom: 7mm; }}
.loesungsblock h2 {{ margin-top: 2mm; }}
.aufloesung {{ font-size: 13pt; margin: 0 0 3mm; }}
.aufloesung b {{ color: {ROT}; }}
.haupt figure.klein {{ width: 88mm; }}
.positionen {{ border-collapse: collapse; width: 100%; font-size: 11.5pt; white-space: nowrap; }}
.positionen td {{ padding: 1mm 1.5mm; border-bottom: 1px solid #d8d0c4; vertical-align: middle; }}
.positionen td:first-child {{ display: flex; align-items: center; }}
.positionen .chip {{ width: 6.4mm; height: 6.4mm; font-size: 8.5pt; }}
"""
