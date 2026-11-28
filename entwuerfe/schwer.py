"""Sucht zu einer festen Aufstellung einen Satz SCHWACHER, verzahnter Hinweise:
jeder Hinweis lässt allein viele Felder offen, zusammen gibt es genau eine Lösung,
und der logische Löser braucht mehrere "Angenommen ..."-Proben.

    python3 entwuerfe/schwer.py faelle/04_piste.toml "Calzi=A5,Hosen=C8,..." [seed]
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from werkzeug import H, Logik, finde_loesungen, lade_fall, zelle  # noqa: E402
from krimi import loeser  # noqa: E402
from krimi.loeser import Zeitueberschreitung  # noqa: E402


def atome_fuer(f, pos, p, opfer=False):
    z = pos[p]
    b = f.bereich(z)
    o = f.objekt(z)
    un, bi = [], []
    arten = {f.objekt(x).kuerzel for x in f.zellen() if f.objekt(x)}
    besetzbare = {k for k in arten if f.katalog[k].besetzbar}
    if not opfer:
        un.append(H.ImBereich(p, b))
        un += [H.NichtImBereich(p, a) for a in f.bereiche if a != b
               and not f.bereiche[a].gesperrt]
    if o:
        un.append(H.AufObjekt(p, o.kuerzel))
    un += [H.NichtAufObjekt(p, k) for k in sorted(besetzbare) if not o or k != o.kuerzel]
    neben = f.arten_neben(z)
    un += [H.NebenObjekt(p, k) for k in sorted(neben)]
    un += [H.NichtNebenObjekt(p, k) for k in sorted(arten - neben)]
    for k in sorted(neben):
        n = H.NebenAnzahl.zaehle(f, z, k)
        if n >= 2:
            un.append(H.NebenAnzahl(p, k, n))
    for achse in "zs":
        for k in sorted(arten):
            h = H.InLinieMit(p, k, achse)
            un.append(h if h.erlaubt(f, p, z) else H.InLinieMit(p, k, achse, 0))
    rand = z[0] in (0, f.n - 1) or z[1] in (0, f.n - 1)
    un.append(H.AmRand(p, rand))
    if opfer:
        return un, []
    for q in pos:
        if q in (p, f.opfer_index):
            continue
        zq = pos[q]
        bi.append(H.Oben(p, q) if z[0] < zq[0] else H.Oben(q, p, umgekehrt=True))
        bi.append(H.Links(p, q) if z[1] < zq[1] else H.Links(q, p, umgekehrt=True))
        bi.append(H.Abstand(p, q, "z", zq[0] - z[0]))
        bi.append(H.Abstand(p, q, "s", zq[1] - z[1]))
        bi.append(H.GleicherBereich(p, q) if f.bereich(zq) == b else H.AndererBereich(p, q))
        if abs(z[0] - zq[0]) == 1 and abs(z[1] - zq[1]) == 1 and f.bereich(zq) == b:
            bi.append(H.Schraeg(p, q))
    for h in un + bi:
        assert h.gilt(f, pos), h
    return un, bi


def felder(f, p, teile):
    un = [t for t in teile if t.paar() is None]
    return [z for z in f.zellen() if f.besetzbar(z) and all(t.erlaubt(f, p, z) for t in un)]


THEMA = (H.AufObjekt, H.NebenObjekt, H.NebenAnzahl, H.InLinieMit, H.ImBereich)


def kandidaten(f, pos, p, rng, min_felder, anzahl=400):
    """Jeder Hinweis: ein thematischer Teil (Gegenstand/Bereich) und meist noch
    ein zweiter Teil (Verneinung, Rand oder eine kurze Lagebeziehung)."""
    opfer = p == f.opfer_index
    un, bi = atome_fuer(f, pos, p, opfer)
    def selten(t):   # "in seiner Zeile gab es auch X" nur bei seltenen Gegenständen
        linien = {(x[0] if t.achse == "z" else x[1]) for x in f.zellen()
                  if f.objekt(x) and f.objekt(x).kuerzel == t.k}
        return len(linien) <= f.n // 3
    thema = [t for t in un if isinstance(t, THEMA)
             and not (isinstance(t, H.InLinieMit) and (t.anzahl == 0 or not selten(t)))]
    rest = [t for t in un if t not in thema]
    bi = [t for t in bi if not (isinstance(t, H.Abstand) and not 1 <= abs(t.d) <= 3)]
    aus, gesehen = [], set()
    for _ in range(anzahl * 4):
        teile = [rng.choice(thema)]
        r = rng.random()
        if r < 0.25 or not bi:
            if rng.random() < 0.5:
                teile.append(rng.choice(rest + thema))
        elif not opfer:
            teile.append(rng.choice(bi))
        if len(teile) == 2 and teile[0] is teile[1]:
            continue
        if len(felder(f, p, teile)) < min_felder:
            continue
        sch = tuple(sorted(str(t.schluessel()) for t in teile))
        if sch in gesehen:
            continue
        gesehen.add(sch)
        aus.append(H.Und(teile, p))
        if len(aus) >= anzahl:
            break
    return aus


FORM = {"Oben": "Lage", "Links": "Lage", "NebenAnzahl": "Neben", "NebenObjekt": "Neben",
        "NichtImBereich": "Nicht", "NichtAufObjekt": "Nicht", "NichtNebenObjekt": "Nicht",
        "GleicherBereich": "Bereich2", "AndererBereich": "Bereich2"}


def formen(h):
    return {FORM.get(type(t).__name__, type(t).__name__) for t in h.teile}


def passt(wahl, p, h, grenze=2):
    """Vielfalt: keine Hinweisform öfter als `grenze`-mal im ganzen Rätsel."""
    from collections import Counter
    c = Counter()
    for q, hq in wahl.items():
        if q != p:
            c.update(formen(hq))
    c.update(formen(h))
    return max(c.values()) <= grenze


def anzahl(f, hs, limit=40):
    return len(finde_loesungen(f, hs, limit=limit))


def suche(f, pos, seed, min_felder=3, frist=240):
    rng = random.Random(seed)
    loeser.FRIST = time.time() + frist
    try:
        kand = {p: kandidaten(f, pos, p, rng, min_felder) for p in pos}
        wahl = {}
        for p in rng.sample(list(pos), len(pos)):
            gut = [h for h in kand[p] if passt(wahl, p, h)]
            if not gut:
                return None
            wahl[p] = rng.choice(gut)
        n = anzahl(f, list(wahl.values()))
        for _ in range(400):
            if n == 1:
                break
            p = rng.choice(list(pos))
            best = None
            gut = [h for h in kand[p] if passt(wahl, p, h)]
            for h in rng.sample(gut, min(12, len(gut))):
                w = dict(wahl); w[p] = h
                m = anzahl(f, list(w.values()))
                if m >= 1 and (best is None or m < best[0]):
                    best = (m, h)
            if best and best[0] <= n:
                n, wahl[p] = best[0], best[1]
        if n != 1:
            return None
        hs = list(wahl.values())
        l = Logik(f, hs, protokoll=False)
        if not l.loese() or not 2 <= l.proben <= 6 or l.max_kette > 3:
            return None
        return wahl, l.proben, l.max_kette
    except Zeitueberschreitung:
        return None
    finally:
        loeser.FRIST = None


if __name__ == "__main__":
    f = lade_fall(sys.argv[1])
    namen = {p.name: i for i, p in enumerate(f.personen)}
    pos = {namen[k]: zelle(v) for k, v in (x.split("=") for x in sys.argv[2].split(","))}
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    for seed in range(start, start + 400):
        t = time.time()
        r = suche(f, pos, seed)
        if r is None:
            print(f"seed {seed}: –  ({time.time() - t:.0f}s)", flush=True)
            continue
        wahl, proben, kette = r
        import pickle
        ordner = Path(__file__).resolve().parent / "treffer"
        ordner.mkdir(exist_ok=True)
        with open(ordner / f"{Path(sys.argv[1]).stem}_{seed}.pkl", "wb") as d:
            pickle.dump(wahl, d)
        print(f"seed {seed}: Proben {proben}, Kette {kette} ({time.time() - t:.0f}s)", flush=True)
        for p, h in wahl.items():
            print(f"     {f.personen[p].name:<11} [{len(felder(f, p, H.atome(h)))}] "
                  f"{' | '.join(type(t).text(t, f) for t in h.teile)}", flush=True)
