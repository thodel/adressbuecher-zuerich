"""82_normdaten.py — Kandidaten für Normdaten (HLS, Wikidata, GND) je Eintrag.

    python scripts/82_normdaten.py --vs ~/Repos/vernetzte-schweiz [--commit <sha>]

Quelle sind die Personenlisten von «Vernetzte Schweiz» am angegebenen Commit (Standard: HEAD):
- data/norm/hls_coverage.csv.gz: HLS-Personen mit Orten und Jahren (Wirkungs-, Wohn-, Sterbeort),
- data/ref/wikidata_persons.csv.gz: Wikidata-Personen mit Lebensdaten, GND, HLS-Nummer und Orten (BFS-Nummer),
- data/ref/municipalities_1914.csv: Gemeinde → BFS-Nummer.

Eine Person kommt für einen Eintrag in Frage, wenn sie mit der Gemeinde des Eintrags verbunden ist, im Jahr des
Bandes lebte und mindestens 18 war (soweit die Daten das sagen), der Familienname gleich ist und der Vorname passt
(gleich, Abkürzung oder Initiale). Stufen:
- **wahrscheinlich**: Vorname gleich oder Abkürzung, und im selben Verzeichnis des Bandes passt kein zweiter Eintrag
  ebenso gut (Einwohner und Berufsregister zählen getrennt, weil dieselbe Person in beiden steht);
  dazu muss der Beruf im Adressbuch zum Feld der Person passen (Politik, Bildung, Wirtschaft, Kunst; Stichwörter
  in FIT) oder der Familienname im Band selten sein (höchstens 3 Einträge);
- **möglich**: sonst, wenn Beruf oder Seltenheit passen (also auch bei blosser Initiale oder mehreren Einträgen).

Das sind **ungeprüfte Kandidaten**; die Seite zeigt sie so an. Ergebnis: web/normdaten.csv.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib
import io
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
b = importlib.import_module("81_baende")
fold, forename_score = b.fold, b.forename_score

CSV_DIR = Path("data/csv")
OUT = Path("web/normdaten.csv")


def git_show(vs: Path, commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(vs), "show", f"{commit}:{path}"], check=True, capture_output=True).stdout


FIT = {  # Stichwörter im Beruf des Adressbuchs → passt zu diesen Feldern/Berufen der Normdaten
    "polit": r"rat|räth|ammann|präsident|fürspr|advokat|richter|regierung|depart|bundes|kanzler|sekretär|statthalter|oberst|major"
             r"|juge|conseill|syndic|député|avocat|notaire|préfet|municip|colonel|fédéral|chancel",
    "bildung": r"prof|dr\.|lehrer|rektor|biblioth|archiv|schul|pfarrer|seminar|chemiker|arzt|doktor"
               r"|docteur|médecin|instituteur|pasteur|recteur|collège|académ|universit",
    "wirtschaft": r"fabrik|kaufm|direktor|ingenieur|ingen|bank|verlag|buchdruck|handl|brauerei|hotel|gasthof|unternehm|inhaber|fabrikant|agent"
                  r"|banquier|négoc|fabricant|directeur|ingénieur|imprim|éditeur|hôtel|entrepren|commerç",
    "kunst": r"maler|musik|architekt|bildhauer|kunst|schriftst|redakt|photogr|sänger|komponist|theater"
             r"|peintre|musicien|architecte|sculpteur|rédact|photograph|chanteur|composit|théâtre|écrivain",
}
FIELD = {"polit": r"politi|juriste|avocat|richter|juge", "bildung": r"bildung|wissenschaft|religion|lehrer|enseign|médecin|arzt|universit",
         "wirtschaft": r"wirtschaft|beruf|ingénieur|ingenieur|entrepreneur|unternehm|banq", "kunst": r"künste|kunst|architect|archit|musi|peintre|maler|literat"}


def fits(occupation: str, field: str) -> bool:
    occ, fld = occupation.lower(), field.lower()
    return any(re.search(FIT[k], occ) and re.search(FIELD[k], fld) for k in FIT)


def full_given(w: dict) -> str:
    """Alle Vornamen aus dem Label («Johann Ludwig Spyri» → «Johann Ludwig»), Bindestrich als Trenner («Charles-Juste»
    passt zu «Charles»). Das Feld given nennt oft nur den ersten, und «Johann» passte zu «Joh. Bernhard» Spyri."""
    first = w["given"].split("|")[0]
    for fam in sorted(set(w["family"].split("|")), key=len, reverse=True):
        if fam and w["label"].endswith(" " + fam):
            g = w["label"][: -len(fam)].strip()
            if first and fold(g).startswith(fold(first)):
                return g.replace("-", " ")
    return first


def year(s: str) -> int | None:
    m = re.match(r"-?\d{3,4}", s or "")
    return int(m.group(0)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vs", type=Path, required=True)
    ap.add_argument("--commit", default="HEAD")
    args = ap.parse_args()
    commit = subprocess.run(["git", "-C", str(args.vs), "rev-parse", args.commit], check=True,
                            capture_output=True, text=True).stdout.strip()

    entries = []
    for f in sorted(p.name for p in CSV_DIR.glob("04_*.csv") if "probe" not in p.name):  # Einwohner, Berufe, ggf. Gemeinden
        entries += [r for r in csv.DictReader((CSV_DIR / f).open(encoding="utf-8")) if r["entry_type"] == "person"]
    for r in entries:
        r["municipality"] = r.get("municipality") or Path.cwd().name.removeprefix("adressbuecher-").capitalize()
    munis = {r["municipality"] for r in entries if r["municipality"]}
    bfs = {}
    for r in csv.DictReader(io.StringIO(git_show(args.vs, commit, "data/ref/municipalities_1914.csv").decode())):
        # Bern und Zürich haben 1914 keine eigene BFS-Nummer in der Tabelle (leer); dann gilt die heutige, aber nur für
        # die Gemeinde, die heute so heisst (sonst nähme Höngg, 1934 eingemeindet, die 261 von Zürich).
        code = r["bfs"] or (r["bfs_today"] if r["name"] == r["name_today"] else "")
        if r["name"] in munis and code:
            bfs.setdefault(code, r["name"])
    vols = sorted({int(r["volume"]) for r in entries})

    # Personen je (Gemeinde, Familienname): [(Quelle, id, Vorname, Name, geb., gest., Jahre am Ort, qid, hls, gnd, Feld)]
    people = defaultdict(list)
    from_hls = defaultdict(list)  # (HLS-Nummer, Gemeinde) → ihre Einträge in people
    wd_by_hls = {}
    with gzip.open(io.BytesIO(git_show(args.vs, commit, "data/ref/wikidata_persons.csv.gz")), "rt", encoding="utf-8") as fh:
        wd = list(csv.DictReader(fh))
    for w in wd:
        if w["hls_id"]:
            wd_by_hls[w["hls_id"]] = w
    with gzip.open(io.BytesIO(git_show(args.vs, commit, "data/norm/hls_coverage.csv.gz")), "rt", encoding="utf-8") as fh:
        for h in csv.DictReader(fh):
            for p in h["places"].split(";"):
                parts = p.split("|")
                if len(parts) >= 3 and parts[0] in munis:
                    toks = h["name"].split()
                    if len(toks) < 2:
                        continue
                    w = wd_by_hls.get(h["hls_id"], {})
                    people[(parts[0], fold(toks[-1]))].append(hp := {
                        "src": "hls", "given": " ".join(toks[:-1]), "name": h["name"], "birth": year(h["birth"]),
                        "death": year(h["death"]), "from": int(parts[1]), "to": int(parts[2]), "hls": h["hls_id"],
                        "qid": w.get("qid", ""), "gnd": w.get("gnd", ""), "field": h["fields"]})
                    from_hls[(h["hls_id"], parts[0])].append(hp)
    for w in wd:
        places = {x.split(":")[1] for x in w["places"].split("|") if ":" in x}
        for code in places & set(bfs):
            given = full_given(w)
            occ = w["occupations"].split("|")[-1] if w["occupations"] else ""
            if hps := from_hls.get((w["hls_id"], bfs[code])):
                # dieselbe Person an diesem Ort auch im HLS: Beruf aus beiden (Francis Isoz: HLS «Wirtschaft und Beruf»,
                # Wikidata «architect»). Die Wikidata-Kopie bleibt, weil sie ohne Jahre am Ort gilt (Otto Dorer, Baden).
                for hp in hps:
                    if occ and occ not in hp["field"]:
                        hp["field"] = f"{hp['field']}|{occ}" if hp["field"] else occ
                occ = hps[0]["field"]
            for fam in set(w["family"].split("|")):
                if fam and given:
                    people[(bfs[code], fold(fam))].append({
                        "src": "wikidata", "given": given, "name": w["label"], "birth": year(w["birth"]),
                        "death": year(w["death"]), "from": None, "to": None, "hls": w["hls_id"], "qid": w["qid"],
                        "gnd": w["gnd"], "field": occ})

    n_sur = Counter((e["volume"], e["municipality"], fold(e["surname"])) for e in entries)
    cand = defaultdict(list)  # (Person-Schlüssel, Band) → [(Punkte, Eintrag)]
    for e in entries:
        vol = int(e["volume"])
        for p in people.get((e["municipality"], fold(e["surname"]).replace(" ", "")), []):
            if p["birth"] and vol - p["birth"] < 18 or p["death"] and p["death"] < vol:
                continue
            if p["from"] and not (p["from"] - 5 <= vol <= p["to"] + 5):
                continue
            fs = forename_score(e["forename"], p["given"])
            if not fs:
                continue
            key = p["hls"] or p["qid"]
            if any(c[1] is e for c in cand[(key, vol)]):
                continue  # dieselbe Person aus HLS und Wikidata: ein Eintrag zählt nur einmal (HLS zuerst)
            cand[(key, vol)].append((fs, e, p))
    out, stats = {}, Counter()
    for (key, vol), cs in cand.items():
        cs.sort(key=lambda c: -c[0])
        best = cs[0][0]
        top = [c for c in cs if c[0] == best]
        per_sec = Counter(e["section"] for _fs, e, _p in top)
        for fs, e, p in top:
            # dieselbe Person steht oft im Einwohnerverzeichnis und im Berufsregister: eindeutig je Verzeichnis genügt
            occ = " ".join((e["title"], e["occupation_raw"], e["heading"]))
            fit = fits(occ, p["field"])
            rare = n_sur[(e["volume"], e["municipality"], fold(e["surname"]))] <= 3
            if fs >= 2 and per_sec[e["section"]] == 1 and (fit or rare):
                t = "wahrscheinlich"
            elif fit or rare:
                t = "möglich"
            else:
                continue  # häufiger Name und der Beruf passt nicht: zu unsicher
            prev = out.get(e["entry_id"])
            if prev and (prev["tier"] == "wahrscheinlich" or t == "möglich"):
                if prev["hls_id"] != p["hls"] or prev["qid"] != p["qid"]:
                    prev["tier"] = "möglich"; prev["note"] = "mehrere Personen möglich"
                continue
            out[e["entry_id"]] = {"entry_id": e["entry_id"], "tier": t, "label": p["name"],
                                  "life": f"{p['birth'] or ''}–{p['death'] or ''}", "hls_id": p["hls"], "qid": p["qid"],
                                  "gnd": p["gnd"], "field": p["field"][:80], "source": p["src"], "note": ""}
    for r in out.values():
        stats[r["tier"]] += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        fields = ["entry_id", "tier", "label", "life", "hls_id", "qid", "gnd", "field", "source", "note"]
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(out.values(), key=lambda r: r["entry_id"]))
    (OUT.parent / "normdaten_source.txt").write_text(
        f"web/normdaten.csv aus thodel/vernetzte-schweiz @ {commit}\n(data/norm/hls_coverage.csv.gz, "
        "data/ref/wikidata_persons.csv.gz, data/ref/municipalities_1914.csv) mit scripts/82_normdaten.py; "
        "ungeprüfte Kandidaten\n", encoding="utf-8")
    print(f"{len(entries)} Personen-Einträge, {sum(len(v) for v in people.values())} Normdaten-Personen an "
          f"{len(munis)} Gemeinden → {len(out)} Einträge mit Kandidat: " + ", ".join(f"{k} {v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
