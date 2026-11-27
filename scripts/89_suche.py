"""89_suche.py — Startseite mit Suche über alle Bände und Eintragsseiten (scripts/site_search.py).

    python scripts/89_suche.py --out _site

Dieselben Quellen wie die Kontrollseite (scripts/90_seite.py, liegt unter korrektur/): data/csv/04_entries_<Band>.csv
und 04_berufe_<Band>.csv, web/telefon.csv, web/baende/<Jahr>.csv.gz, web/normdaten.csv, web/geo/ und
data/csv/01_iiif_pages.csv. Spalten, Beschriftungen, Gebiet (10_geo.area), Strassenschlüssel (10_geo.norm_street) und
Telefon-Zelle (90_seite.load_phone) kommen von dort.

90_seite.py wird nicht importiert: es lädt beim Import alle Treffer in anderen Bänden samt deren Text (OTHER, rund
1,7 Mio. Einträge, 3,6 GB Speicher und fast drei Minuten). Hier genügen [Band, Stufe, ID]; der Text des anderen Eintrags
steht auf dessen eigener Seite. Darum werden TABS, LABELS, IIIF_BASE usw. aus dem Quelltext gelesen (ast), ohne ihn
auszuführen. Die Einträge sind schlank gehalten (leere Felder fehlen, wiederkehrende Werte geteilt), damit der Bau auf
den 7 GB des GitHub-Runners Platz hat.
"""
from __future__ import annotations

import argparse
import ast
import csv
import gzip
import importlib
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import site_nav  # noqa: E402
import site_search  # noqa: E402

_geo = importlib.import_module("10_geo")


def _consts(path: Path, names: set[str]) -> dict:
    """Konstanten aus einem Skript lesen, ohne es auszuführen (90_seite.py lädt beim Import zu viel)."""
    out = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) in names:
            out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


K = _consts(Path(__file__).parent / "90_seite.py", {"TABS", "LABELS", "IIIF_BASE", "REPO_URL", "VOLUMES", "QA"})

CITY = {
    "key": "zuerich", "name": "Zürich", "span": "1859–1945", "lang": "de",
    "title": "Adressbücher der Stadt Zürich",
    "lead": "Einwohner und Berufsregister aus den Adressbüchern der Stadt Zürich 1859–1945, maschinell gelesen und in "
            "Felder zerlegt. Gesucht wird über alle Bände.",
    "tagline": "Adressbücher · Einwohner · Berufe",
    "repo": K["REPO_URL"], "center": [47.3717, 8.5423],
    "korr": "korrektur/?tab={part}&vol={vol}&q={id}",
    "nav": [["karte.html", "Karte: Einträge nach Strasse und Gemeinde"]],
    "note": "Quelle: Adressbücher der Stadt Zürich (Zentralbibliothek Zürich). Gelesen mit qwen3.8-27b (Universität Bern). "
            "«Gebiet»: 1859 Grosse/Kleine Stadt, 1867–1885 die alte Gemeinde, 1900–1945 der Stadtkreis.",
    "page_note": "Seitenbilder von der Zentralbibliothek Zürich (Zurich Open Platform, CC0), über IIIF direkt von der ZB "
                 "geladen; «Seite» ist die Seite im PDF der ZB.",
    "parts": {k: label for k, label, *_ in K["TABS"]},
    "volumes": {v: v for v in K["VOLUMES"]},  # kurz: das Jahr (die Titel stehen in der Kontrollseite)
}
KIND = {k: kind for k, _label, kind, _cols in K["TABS"]}
FIELD_COLS = ["civil_status", "entry_type", "phone_flag", "municipality", "origin_canton", "relation", "parse_confidence",
              "qa_flags"]  # weitere Angaben, nur wenn nicht leer (und nicht der Normalfall)
NORMAL = {"entry_type": "person", "municipality": "Zürich", "parse_confidence": "high"}


def load_phone() -> dict[str, str]:
    """entry_id → «Stufe|Jahr|Name|Strasse|Nummer|Einheit|Bild» wie 90_seite.load_phone (Format von std_links)."""
    p = Path("web/telefon.csv")
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        return {r["entry_id"]: "|".join(r[k].replace("|", "/") for k in ("how", "ptt_year", "ptt_name", "ptt_street",
                                                                        "ptt_phone", "entity_id", "image"))
                for r in csv.DictReader(fh)}


def load_auth() -> dict[str, list]:
    """web/normdaten.csv (82_normdaten.py) → entry_id → Links. Format nicht wie Aarau («Q…|HLS|…»), darum hier."""
    out = {}
    p = Path("web/normdaten.csv")
    if not p.exists():
        return out
    for r in csv.DictReader(p.open(encoding="utf-8")):
        note = " · ".join(x for x in (r["life"], r["field"].replace("|", ", "), f"ungeprüft, {r['tier']}", r["note"]) if x)
        ls = []
        if r["qid"]:
            ls.append(["wd", r["label"] or r["qid"], f"https://www.wikidata.org/wiki/{r['qid']}", f"Wikidata · {note}"])
        if r["hls_id"]:
            ls.append(["hls", f"HLS {r['hls_id']}", f"https://hls-dhs-dss.ch/de/articles/{r['hls_id']}/",
                       f"Historisches Lexikon der Schweiz · {r['label']}"])
        if r["gnd"]:
            ls.append(["ext", f"GND {r['gnd']}", f"https://d-nb.info/gnd/{r['gnd']}", "Gemeinsame Normdatei"])
        if ls:
            out[r["entry_id"]] = ls
    return out


def load_related(ids: dict[str, str]) -> dict[str, list]:
    """web/baende/<Jahr>.csv.gz (81_baende.py) → entry_id → [[Band, Stufe, entry_id], …], neuester Band zuerst.

    Nur diese drei Spalten; die Zelle der Kontrollseite trägt zusätzlich den ganzen Text des anderen Eintrags."""
    out = defaultdict(list)
    for gz in sorted(Path("web/baende").glob("*.csv.gz")):
        with gzip.open(gz, "rt", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh)
            h = next(rd)
            ie, iv, io, it = (h.index(c) for c in ("entry_id", "other_volume", "other_id", "tier"))
            for row in rd:
                oid = row[io].split("#")[0]
                out[ids.get(row[ie], row[ie])].append([sys.intern(row[iv]), sys.intern(row[it]), ids.get(oid, oid)])
    for v in out.values():
        v.sort(key=lambda x: x[0], reverse=True)
    return out


def load_points() -> dict[str, tuple[float, float]]:
    """«Gebiet|Strassenschlüssel» → (lat, lon) WGS84; Quelle von 90_seite.load_geo (das nach LV95 umrechnet)."""
    out = {}
    p = Path("web/geo/streets.csv")
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r["lat"]:
                out[r["area"] + "|" + r["street_norm"]] = (float(r["lat"]), float(r["lon"]))
    for (a, st), pt in _geo.manual_points().items():
        out[a + "|" + st] = pt
    return out


def page_urls() -> dict[str, list[str]]:
    """Band → IIIF-Bild-URL je Seite (Seite = Canvas), wie data/<Band>-iiif.json der Kontrollseite."""
    ids: dict[str, list[str]] = defaultdict(list)
    for r in csv.DictReader(Path("data/csv/01_iiif_pages.csv").open(encoding="utf-8")):
        assert int(r["page"]) == len(ids[r["volume"]]) + 1
        ids[r["volume"]].append(r["iiif_image"] + "/full/max/0/default.jpg")
    return ids


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--block", type=int, default=2000, help="Einträge je Datei in s/r/")
    args = ap.parse_args()
    labels = {**site_nav.LABELS["de"], **K["LABELS"]}
    phone, auth, pts, pages = load_phone(), load_auth(), load_points(), page_urls()
    S: dict[str, str] = {}  # wiederkehrende Werte nur einmal im Speicher
    sh = lambda x: S.setdefault(x, x)
    ids: dict[str, str] = {}
    files = [(key, f) for key, *_ in K["TABS"] for f in _geo.register_files(KIND[key])]
    for _key, f in files:  # zuerst nur die IDs, damit related dieselben Strings benutzt
        with f.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                ids[row["entry_id"]] = row["entry_id"]
    related = load_related(ids)
    recs = []
    for key, f in files:
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                vol = r["volume"]
                if not vol[:4].isdigit():
                    continue
                eid = ids[r["entry_id"]]
                area = _geo.area(r)
                street = _geo.norm_street(r["street_raw"]) if r["street_raw"] else ""
                g = pts.get(area + "|" + street) or pts.get("|" + street) if street else None
                occ = r["occupation_raw"] or (r["heading"].strip(" .") if key == "berufe" else "")
                rec = {"id": eid, "vol": sh(vol), "year": int(vol[:4]), "part": sh(key)}
                for k, v in (("name", r["surname"]), ("forename", sh(r["forename"])), ("alliance", r["alliance_name"]),
                             ("maiden", r["maiden_name"]), ("occupation", sh(occ)), ("street", sh(street)),
                             ("no", sh(r["building_no"])), ("area", sh(area)), ("origin", sh(r["origin_raw"])),
                             ("title", sh(r["title"])), ("heading", sh(r["heading"])), ("text", r["text"]),
                             ("page", sh(r["page"]))):
                    if v:
                        rec[k] = v
                pg = pages.get(vol, [])
                if r["page"].isdigit() and 0 < int(r["page"]) <= len(pg):
                    rec["page_url"] = pg[int(r["page"]) - 1]
                if g:
                    rec["lat"], rec["lon"] = g
                fields = []
                for c in FIELD_COLS:
                    v = r.get(c, "")
                    if v and v != NORMAL.get(c):
                        if c == "phone_flag":
                            v = "☏ im Adressbuch"
                        elif c == "qa_flags":
                            v = "; ".join(K["QA"].get(x, x) for x in v.replace(";", " ").split())
                        fields.append((c, sh(v)))
                if fields:
                    rec["fields"] = fields
                links = site_search.std_links({"telefon": phone.get(eid, "")})[0] + auth.get(eid, [])
                if links:
                    rec["links"] = links
                if eid in related:
                    rec["related"] = related.pop(eid)
                recs.append(rec)
    del ids, related
    S.clear()
    site_search.build(args.out, city=CITY, records=recs, labels=labels, block=args.block)


if __name__ == "__main__":
    main()
