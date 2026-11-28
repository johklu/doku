"""Fall 4 – Puder auf der Piste: von Hand entworfen.

Aufruf:  python3 entwuerfe/04_piste.py          (prüfen)
         python3 entwuerfe/04_piste.py --speichern   (einfrieren -> faelle/04_piste.raetsel.json)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from werkzeug import H, finde_loesungen, friere_ein, lade_fall, pruefe  # noqa: E402

FALL = Path(__file__).resolve().parent.parent / "faelle" / "04_piste.toml"
f = lade_fall(FALL)
Ca, Ho, Pe, Le, Jo, Eq, Tr, Ra, Ov = range(9)

HINWEISE = [
    (H.Und([H.ImBereich(Ca, "D"), H.AmRand(Ca), H.InLinieMit(Ca, "Sk", "z")]),
     "Calzi saß im Lift, ganz außen am Rand des Plans – und in seiner Zeile stand "
     "auch eine Schneekanone."),
    (H.Und([H.ImBereich(Ho, "E"), H.AufObjekt(Ho, "Si"), H.NichtNebenObjekt(Ho, "Km")]),
     "Hosen saß im Rufalipark auf einem Sitz, aber nicht direkt neben dem Kamin."),
    (H.Und([H.AufObjekt(Pe, "Bk"), H.NichtImBereich(Pe, "B")]),
     "Pete stand auf einem Buckel – allerdings nicht auf der roten Piste."),
    (H.Und([H.AufObjekt(Le, "Ts"), H.Abstand(Le, Pe, "z", 5)]),
     "Leah stand im Tiefschnee, genau fünf Zeilen über Pete."),
    (H.Und([H.AufObjekt(Jo, "Sn"), H.Oben(Jo, Tr), H.Links(Ho, Jo)], Jo),
     "Johann stand im Schnee, weiter oben als Trilling, aber weiter rechts als Hosen."),
    (H.Und([H.ImBereich(Eq, "B"), H.Abstand(Tr, Eq, "z", 2)], Eq),
     "Auch Equi war auf der roten Piste – genau zwei Zeilen unter Trilling."),
    (H.Und([H.AufObjekt(Tr, "Sn"), H.NebenObjekt(Tr, "Fs")]),
     "Trilling stand im Schnee, direkt neben einem Felsen."),
    (H.Und([H.ImBereich(Ra, "F"), H.NichtAufObjekt(Ra, "Sn")]),
     "Ranges saß auf dem Stein – aber nicht im Schnee."),
    (H.Und([H.AufObjekt(Ov, "Sn"), H.InLinieMit(Ov, "Sm", "z")]),
     "Die Ovomaltine lag im Schnee, in derselben Zeile wie ein Schneemann."),
]

LOESUNGSWEG = [
    "Tiefschnee gibt es nur in Spalte I – dort steht Leah. Pete steht auf einem Buckel, "
    "aber nicht auf der roten Piste, also irgendwo auf H3 bis H7. Weil Leah genau fünf "
    "Zeilen über Pete steht, kommt für Pete nur Zeile 6 oder 7 infrage (H6 oder H7) und "
    "für Leah I1 oder I2.",
    "Calzi sitzt im Lift. Schneekanonen gibt es nur in Zeile 1 und Zeile 5 – im Lift "
    "bleibt damit nur Zeile 5. Ganz außen am Rand ist dort nur A5: Calzi sitzt auf A5.",
    "Der Stein liegt ganz in Zeile 1. Ranges sitzt dort nicht im Schnee, also auf A1, B1 "
    "oder C1 – Spalte A gehört schon Calzi, bleibt B1 oder C1. Jedenfalls ist Zeile 1 "
    "vergeben: Leah steht auf I2, und Pete genau fünf Zeilen tiefer auf H7.",
    "Hosen sitzt auf einem Sitz im Rufalipark: D7, C8 oder C9. C9 liegt direkt neben dem "
    "Kamin, D7 in Petes Zeile 7 – also sitzt Hosen auf C8. Damit ist Spalte C belegt, "
    "und Ranges sitzt auf B1.",
    "Trilling steht im Schnee direkt neben einem Felsen. Neben dem Felsen auf der "
    "schwarzen Piste (I6) liegt kein Schnee; neben dem Felsen F4 zählen nur F3, G4 und "
    "F5 (E4 gehört zur blauen Piste). Equi steht zwei Zeilen tiefer, ebenfalls auf der "
    "roten Piste. Trilling auf F3? Dann müsste Equi in Zeile 5 stehen – F5 ist Trillings "
    "Spalte, G5 die Schneekanone. Trilling auf F5? Dann müsste Equi in Zeile 7 stehen – "
    "dort steht schon Pete. Also steht Trilling auf G4 und Equi auf F6 (G6 wäre wieder "
    "Trillings Spalte).",
    "Schneemänner stehen in Zeile 1 und Zeile 9. Zeile 1 ist vergeben, also lag die "
    "Ovomaltine in Zeile 9 im Schnee: E9, F9 oder G9. Die Spalten F und G sind schon "
    "belegt – die Ovomaltine lag auf E9.",
    "Übrig sind nur noch Zeile 3 und Spalte D: Johann stand auf D3 – im Schnee, weiter "
    "oben als Trilling und weiter rechts als Hosen, genau wie sein Hinweis sagt.",
    "Die Ovomaltine lag auf der blauen Piste, und dort war sonst nur Johann. "
    "Also: Johann hat die Ovomaltine geklaut!",
]

if __name__ == "__main__":
    hinweise = [h for h, _ in HINWEISE]
    for h, t in HINWEISE:
        print(" -", t)
    pruefe(f, hinweise)
    if "--speichern" in sys.argv:
        print("Gespeichert:", friere_ein(FALL, f, hinweise, [t for _, t in HINWEISE], LOESUNGSWEG))
