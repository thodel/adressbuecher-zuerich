"""merge_zurich1945.py — Nachlesung der 20 Seiten von Zürich 1945 (retry_zurich1945.sh) nach results/ übernehmen.

Je Seite die erste Runde mit Schlusszeile (x2, x2.2, x1.8, x2.5). Zwei Sonderfälle, je mit `ended_note` in der JSON:
- S. 74: fünf Runden ohne Schlusszeile, alle enden mit dem letzten Eintrag der Seite (am Seitenbild geprüft).
- S. 1195: alle Runden brechen im Eintrag «Strimmer, Georg» ab (elf Einträge vor dem Seitenende). Linke Spalte
  aus der Seitenlesung x2, rechte Spalte aus einer eigenen Lesung des Spaltenausschnitts (retry/col_x2).
Die alten Dateien wandern nach results_unended/ (nichts wird gelöscht).
"""
import json, shutil
from pathlib import Path

D = Path("/home/dh/adressbuch_qwen/full/zurich1945"); R = D / "retry"; RES = D / "results"
OLD = D / "results_unended"; OLD.mkdir(exist_ok=True)
PAGES = [58, 67, 74, 222, 246, 262, 373, 494, 501, 576, 603, 646, 723, 742, 1186, 1195, 1506, 1516, 1562, 1598]

def load(x, p, sub=None):
    stem = f"zurich1945_p{p:03d}_x{x}"
    d = R / (sub or f"x{x}")
    if not (d / f"{stem}.json").exists():
        return None, None
    return json.loads((d / f"{stem}.json").read_text()), [json.loads(l) for l in (d / f"{stem}.jsonl").read_text().splitlines() if l.strip()]

for p in PAGES:
    meta = rows = None
    for x in ("2", "2.2", "1.8", "2.5", "1.6"):
        m, r = load(x, p)
        if m and m["ended"]:
            meta, rows = m, r; break
    if p == 74:
        meta, rows = load("2", p)
        assert rows[-1]["text"].startswith("☎ Albert (Winterhalder)")
        meta["ended"] = True
        meta["ended_note"] = "ohne Schlusszeile; letzter Eintrag der Seite am Seitenbild geprüft (20.11.2026), fünf Runden gleich"
    if p == 1195:
        meta, full = load("2", p)
        cm, col = load("2", p, "col_x2")
        assert cm["ended"]
        first = next(e for e in col if e.get("type") == "entry")
        cut = next(i for i, e in enumerate(full) if e.get("type") == "entry" and e["text"][:25] == first["text"][:25])
        rows = full[:cut] + [e for e in col if e.get("type") != "pageheader"]
        meta["ended"] = True
        meta["ended_note"] = (f"Seitenlesung bricht bei «Strimmer, Georg» ab; linke Spalte ({cut} Zeilen) aus der Seitenlesung, "
                              "rechte Spalte aus der Lesung des Spaltenausschnitts (retry/col_x2), 20.11.2026")
    assert meta and meta["ended"], p
    meta["retry"] = f"upscale {meta['upscale']}, max_tokens 32000 (retry_zurich1945.sh)"
    stem = f"zurich1945_p{p:03d}_x2"
    for suf in (".json", ".jsonl"):
        if (RES / (stem + suf)).exists() and not (OLD / (stem + suf)).exists():
            shutil.move(RES / (stem + suf), OLD / (stem + suf))
    (RES / f"{stem}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (RES / f"{stem}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(p, "x" + str(meta["upscale"]), sum(r.get("type") == "entry" for r in rows), meta.get("ended_note", "")[:40])
