"""90_seite.py — die Einträge als durchsuchbare statische Seite (GitHub Pages).

    python scripts/90_seite.py --out _site

Schreibt `index.html` und je Band und Reiter `data/<Band>-<Reiter>.json` nach --out. Die Seite lädt einen Band
erst, wenn er gebraucht wird (zuerst 1914), weil alle Bände zusammen über 50 MB wären.

Quellen: data/csv/04_entries_<Band>.csv, 04_berufe_<Band>.csv, data/review/flags.csv (falls vorhanden), web/telefon.csv,
web/baende.csv.gz, web/normdaten.csv, web/geo/ und data/csv/01_iiif_*.csv. Seitenbilder kommen über IIIF von der
Zentralbibliothek Zürich (Zurich Open Platform, CC0); «Seite» = Seite im PDF der ZB = Canvas, je Band
`data/<Band>-iiif.json` (Bild-IDs in Seitenfolge, lädt erst, wenn jemand eine Seite öffnet).

Spalte «Gebiet» (aus 10_geo.area): 1859 Grosse/Kleine Stadt, 1867–1885 die alte Gemeinde, 1900–1945 der Kreis.

Reiter, Suche, Filter und Flagging je Zeile wie bei Aarau, Basel und Baden: ein Flag wird im Browser
gespeichert und als CSV exportiert; `scripts/91_merge_flags.py` mischt ihn nach data/review/flags.csv.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib
import shutil
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
_geo = importlib.import_module("10_geo")
norm_street, area_of, manual_points = _geo.norm_street, _geo.area, _geo.manual_points
import site_nav  # noqa: E402  gemeinsame Navigation und Feldsuche aller Adressbuch-Seiten
import site_fonts  # noqa: E402  Schriften lokal (fonts/)

CSV_DIR = Path("data/csv")
REVIEW = Path("data/review/flags.csv")
TELEFON = Path("web/telefon.csv")  # aus scripts/80_telefon.py
IIIF_BASE = "https://zop.zb.uzh.ch/publiciiif/iiif/2/"
REPO_URL = "https://github.com/thodel/adressbuecher-zuerich"
VOLUMES = {"1914": "Adressbuch der Stadt Zürich 1914",  # zuerst: Standardband der Seite
           "1945": "Adressbuch der Stadt Zürich 1945", "1940": "Adressbuch der Stadt Zürich 1940", "1935": "Adressbuch der Stadt Zürich 1935", "1930": "Adressbuch der Stadt Zürich 1930", "1925": "Adressbuch der Stadt Zürich 1925", "1922": "Adressbuch der Stadt Zürich 1922", "1920": "Adressbuch der Stadt Zürich 1920",
           "1910": "Adressbuch der Stadt Zürich 1910", "1909": "Adressbuch der Stadt Zürich 1909", "1907": "Adressbuch der Stadt Zürich 1907", "1904": "Adressbuch der Stadt Zürich 1904", "1903": "Adressbuch der Stadt Zürich 1903", "1902": "Adressbuch der Stadt Zürich 1902", "1901": "Adressbuch der Stadt Zürich 1901", "1900": "Adressbuch der Stadt Zürich 1900",
           "1885": "Adressbuch Zürich 1885", "1875": "Adressbuch Zürich 1875",
           "1867": "Adressbuch der Stadt Zürich und Umgebung 1867",
           "1859": "Adressbuch der Stadt Zürich und Umgebung 1859"}

TABS = [
    ("einwohner", "Einwohner", "entries",
     ["entry_id", "volume", "page", "surname", "alliance_name", "forename", "title", "civil_status",
      "occupation_raw", "street_raw", "building_no", "area", "phone_flag", "telefon", "other_volume", "authority", "zeitreise", "entry_type",
      "parse_confidence", "qa_flags", "text", "street_key"]),
    ("berufe", "Berufsregister", "berufe",
     ["entry_id", "volume", "page", "heading", "surname", "alliance_name", "forename", "title", "civil_status",
      "occupation_raw", "origin_raw", "street_raw", "building_no", "area", "phone_flag", "telefon", "other_volume", "authority", "zeitreise", "entry_type",
      "parse_confidence", "qa_flags", "text", "street_key"]),
]

LABELS = {"entry_id": "ID", "volume": "Band", "page": "Seite", "surname": "Name", "alliance_name": "Allianz",
          "forename": "Vorname", "title": "Titel", "civil_status": "Stand", "occupation_raw": "Beruf",
          "origin_raw": "Zusatz", "street_raw": "Strasse", "building_no": "Nr.", "phone_flag": "Tel.",
          "entry_type": "Typ", "parse_confidence": "Konfidenz", "qa_flags": "Hinweise", "heading": "Rubrik",
          "text": "Gelesene Zeile", "telefon": "Telefonbuch", "area": "Gebiet",
          "other_volume": "Anderer Band", "authority": "Normdaten (ungeprüft)", "zeitreise": "Karte damals"}

QA = {"street_rare": "Strasse nur einmal im Band",
      "dehyphen": "Zeilenend-Trennung zusammengezogen",
      "hyphen": "Trennstrich mitten im Wort",
      "surname_split": "Familienname vom Allianznamen getrennt",
      "triple": "dreifacher Buchstabe gekürzt",
      "alliance_from_forename": "Allianzname stand im Vornamen",
      "alliance_from_text": "Allianzname aus dem Text ergänzt",
      "unreadable": "unleserliche Stelle [?]"}

REASONS = ["Lesefehler", "Feld falsch", "Eintrag falsch getrennt", "Rubrik falsch", "Quelle: Druckfehler",
           "Dublette", "Anderes"]


def load_phone() -> dict[str, str]:
    """entry_id → «Stufe|Jahr|Name|Strasse|Nummer|Einheit|Bild» aus web/telefon.csv."""
    if not TELEFON.exists():
        return {}
    with TELEFON.open(encoding="utf-8") as fh:
        return {r["entry_id"]: "|".join(r[k].replace("|", "/") for k in ("how", "ptt_year", "ptt_name", "ptt_street",
                                                                        "ptt_phone", "entity_id", "image"))
                for r in csv.DictReader(fh)}


PHONE = load_phone()


def load_simple(path: str, fields: tuple[str, ...]) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        return {r["entry_id"]: "|".join(r[k].replace("|", "/") for k in fields) for r in csv.DictReader(fh)}


def load_other() -> dict[str, str]:
    """entry_id → Treffer in den anderen Bänden, je «Stufe|Band|ID|Text|Belege», getrennt durch «;;».

    Im Repo liegt web/baende.csv.gz (ungepackt über 50 MB); 81_baende.py, das in allen adressbuecher-* gleich ist,
    schreibt web/baende.csv (nicht im Repo). Ist die .csv neuer, wird die .gz hier daraus neu gepackt."""
    p, gz = Path("web/baende.csv"), Path("web/baende.csv.gz")
    if p.exists() and (not gz.exists() or p.stat().st_mtime > gz.stat().st_mtime):
        with p.open("rb") as src, gzip.GzipFile(gz, "wb", mtime=0) as dst:
            shutil.copyfileobj(src, dst)
    out: dict[str, list[str]] = defaultdict(list)
    if gz.exists():
        with gzip.open(gz, "rt", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out[r["entry_id"]].append("|".join(r[k].replace("|", "/").replace(";;", ";")
                                                   for k in ("tier", "other_volume", "other_id", "other_text", "evidence")))
    return {k: ";;".join(sorted(v, key=lambda x: x.split("|")[1], reverse=True)) for k, v in out.items()}


OTHER = load_other()  # 81_baende.py
AUTH = load_simple("web/normdaten.csv", ("tier", "label", "life", "hls_id", "qid", "gnd", "field", "note"))  # 82_normdaten.py


def lv95(lat: float, lon: float) -> tuple[int, int]:
    """WGS84 → LV95 (Näherung von swisstopo, auf ~1 m genau)."""
    p, l = (lat * 3600 - 169028.66) / 10000, (lon * 3600 - 26782.5) / 10000
    e = 2600072.37 + 211455.93 * l - 10938.51 * l * p - 0.36 * l * p * p - 44.54 * l ** 3
    n = 1200147.07 + 308807.95 * p + 3745.25 * l * l + 76.63 * p * p - 194.56 * l * l * p + 119.79 * p ** 3
    return round(e), round(n)


def load_geo() -> dict[str, list[int]]:
    """«Gebiet|Strassenschlüssel» → [E, N] für den Link auf die Zeitreise von swisstopo; «|» = Stadtmitte."""
    out = {"|": list(lv95(47.3717, 8.5423))}  # Grossmünster / Limmat
    p = Path("web/geo/streets.csv")
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r["lat"]:
                out[r["area"] + "|" + r["street_norm"]] = list(lv95(float(r["lat"]), float(r["lon"])))
    for (a, st), pt in manual_points().items():  # von Hand; Gebiet leer = für jedes Gebiet
        out[a + "|" + st] = list(lv95(*pt))
    return out


GEO = load_geo()


def load_rows() -> dict[str, dict[str, list[list[str]]]]:
    """Band → Reiter → Zeilen."""
    out: dict[str, dict[str, list]] = defaultdict(lambda: {k: [] for k, *_ in TABS})
    for key, _label, kind, cols in TABS:
        csv_rows, fieldnames = [], []
        for f in _geo.register_files(kind):  # je Band eine Datei (convert.py)
            with f.open(encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                csv_rows += list(reader)
                fieldnames = fieldnames or reader.fieldnames
        cols += site_nav.extra_columns(csv_rows, fieldnames, cols + ["district"])  # district = Spalte «Gebiet»  # alle CSV-Angaben durchsuchbar
        for r in csv_rows:
            r["qa_flags"] = " ".join(r.get("qa_flags", "").replace(";", " ").split())
            r["telefon"] = PHONE.get(r["entry_id"], "")
            r["street_key"] = norm_street(r["street_raw"]) if r.get("street_raw") else ""
            r["area"] = area_of(r)
            r["other_volume"] = OTHER.get(r["entry_id"], "")
            r["authority"] = AUTH.get(r["entry_id"], "")
            r["zeitreise"] = ""  # im Browser aus GEO
            out[r["volume"]][key].append([r.get(c, "") for c in cols])
    return out


def load_flags() -> list[dict]:
    if not REVIEW.exists():
        return []
    with REVIEW.open(encoding="utf-8") as fh:
        return [{"table": r["table"], "id": r["id"], "reason": r["reason"], "note": r["note"]}
                for r in csv.DictReader(fh) if r.get("status", "open") != "fixed"]


TEMPLATE = r"""<!doctype html>
<html lang="de">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Adressbücher Zürich 1859–1945</title>
<meta name="description" content="Einträge der Adressbücher der Stadt Zürich 1859, 1867, 1875, 1885, 1900, 1901, 1902, 1903, 1904, 1907, 1909, 1910, 1914, 1920, 1922, 1925, 1930, 1935, 1940 und 1945, maschinell gelesen mit qwen3.8, durchsuchbar nach Name, Beruf, Strasse und Kreis, verknüpft mit dem Telefonbuch.">
<link rel="stylesheet" href="fonts/fonts.css">
<style>
/* Layout: Werkzeug wie Aarau/Basel/Baden — Kopf mit Hinweis und Filtern, darunter eine Tabelle, die den Rest füllt. */
:root {
  --bg: #f6f5f1; --paper: #ffffff; --fg: #1d2129; --muted: #5c6370; --line: #d9d7cf;
  --accent: #7a2e2e; --accent-soft: #f1e3e1; --ok: #2f6f4e; --warn: #9a6b11; --bad: #a33a2a; --flag: #fff3c4;
  --note-bg: #fbf4e2; --note-line: #e2cf9c;
  --font-body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --font-data: "Source Code Pro", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #15171b; --paper: #1d2026; --fg: #e8e6df; --muted: #a39f94; --line: #353942;
  --accent: #d08a84; --accent-soft: #3a2626; --ok: #7fc39d; --warn: #d9b35a; --bad: #e08a79; --flag: #3b3418;
  --note-bg: #2a2619; --note-line: #5a4d2a; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #15171b; --paper: #1d2026; --fg: #e8e6df; --muted: #a39f94; --line: #353942;
  --accent: #d08a84; --accent-soft: #3a2626; --ok: #7fc39d; --warn: #d9b35a; --bad: #e08a79; --flag: #3b3418;
  --note-bg: #2a2619; --note-line: #5a4d2a; color-scheme: dark }
[hidden] { display: none !important; }
html, body { height: 100%; }
body { background: var(--bg); color: var(--fg); font-family: var(--font-body); font-size: 15px; line-height: 1.4;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 16px; display: flex; flex-direction: column; gap: 10px; box-sizing: border-box; margin: 0; }
header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 20px; }
.nav { font-size: 0.9rem; color: var(--muted); }
.nav a, td a, .note a, .sub a, footer a { color: var(--accent); }
.nav a { font-weight: 600; text-decoration: none; }
.nav a:hover, .nav a:focus-visible { text-decoration: underline; }
h1 { font-size: 1.3rem; margin: 0; font-weight: 700; letter-spacing: -0.01em; text-wrap: balance; }
.sub { color: var(--muted); font-size: 0.88rem; margin: 0; }
.note { background: var(--note-bg); border: 1px solid var(--note-line); border-radius: 8px; padding: 8px 12px; font-size: 0.9rem; }
.note p { margin: 0; }
.note details { margin-top: 4px; }
.note summary { cursor: pointer; color: var(--accent); font-weight: 600; }
.note .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 4px 24px; margin-top: 6px; }
.note h2 { font-size: 0.95rem; margin: 6px 0 2px; }
.note ul { margin: 0; padding-left: 1.2em; }
.note li { margin: 2px 0; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
.tabs { display: flex; gap: 4px; flex-wrap: wrap; }
button { font: inherit; cursor: pointer; }
.tabs button { font-weight: 600; background: transparent; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px; }
.tabs button[aria-selected="true"] { background: var(--accent); border-color: var(--accent); color: #fff; }
button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
input[type="search"], select, input[type="text"] { font: inherit; padding: 5px 9px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper); color: var(--fg); min-width: 0; max-width: 100%; }
input#q { flex: 1 1 220px; }
input#street { flex: 0 1 180px; }
.chip { display: inline-flex; gap: 6px; align-items: center; background: var(--accent-soft); border: 1px solid var(--accent); border-radius: 999px; padding: 2px 4px 2px 10px; font-size: 0.88rem; }
.chip button { border: 0; background: transparent; color: var(--accent); font-weight: 700; padding: 0 6px; }
.count { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 0.9rem; }
.flagbar { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); font-size: 0.9rem; }
.flagbar .n { font-weight: 700; color: var(--accent); font-variant-numeric: tabular-nums; }
.btn { border: 1px solid var(--line); background: var(--paper); color: var(--fg); border-radius: 6px; padding: 4px 10px; }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.wrap { flex: 1 1 auto; min-height: 320px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); }
table { border-collapse: collapse; width: max-content; min-width: 100%; font-size: 13.5px; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--line); vertical-align: top; white-space: nowrap; max-width: 32ch; overflow: hidden; text-overflow: ellipsis; }
td.wide { white-space: normal; max-width: 48ch; }
th { position: sticky; top: 0; background: var(--paper); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); z-index: 1; }
td.num, td.id { font-family: var(--font-data); font-variant-numeric: tabular-nums; font-size: 12.5px; }
td button.st { border: 0; background: none; padding: 0; color: var(--fg); text-decoration: underline dotted; text-underline-offset: 2px; text-decoration-color: var(--muted); }
tr.flagged td { background: var(--flag); }
tr.reported td:first-child::before { content: "✓ "; color: var(--ok); font-weight: 700; }
.pill { display: inline-block; border-radius: 999px; padding: 0 8px; font-size: 0.74rem; font-weight: 600; line-height: 1.5; }
.pill.high { background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }
.pill.medium { background: color-mix(in srgb, var(--warn) 18%, transparent); color: var(--warn); }
.qa { display: inline-block; border: 1px solid var(--line); border-radius: 4px; padding: 0 5px; margin-right: 3px; font-size: 0.74rem; color: var(--muted); }
.star { color: var(--accent); font-weight: 700; }
a.ov.sicher { font-weight: 700; } a.ov.möglich { font-style: italic; opacity: 0.75; }
td.act { white-space: nowrap; }
td.act select, td.act input { font-size: 12.5px; padding: 2px 5px; }
td.act input[type="text"] { width: 14ch; }
td.act a { color: var(--muted); font-size: 12px; margin-left: 6px; }
.more { display: block; width: 100%; padding: 8px; background: var(--accent-soft); color: var(--fg); border: 0; }
.legend { color: var(--muted); font-size: 0.84rem; margin: 0; }
.legend b { color: var(--fg); }
.loading { padding: 16px; color: var(--muted); }
footer { color: var(--muted); font-size: 0.8rem; }
#toast { position: fixed; bottom: calc(12px + env(safe-area-inset-bottom, 0px)); right: calc(12px + env(safe-area-inset-right, 0px)); background: var(--fg); color: var(--bg); padding: 8px 14px; border-radius: 8px; font-size: 0.9rem; }
@media (max-width: 600px) { body { font-size: 14px; } th, td { max-width: 22ch; } td.act input[type="text"] { width: 9ch; } .flagbar .sub { display: none; } .wrap { min-height: 70vh; } input#street { flex: 1 1 140px; } }
button.pg { font: inherit; color: var(--accent, #0b5cad); background: none; border: 0; padding: 0; cursor: pointer; text-decoration: underline dotted; }
dialog#viewer { width: min(980px, 96vw); height: min(96vh, 1400px); max-height: 96vh; padding: 0; border: 1px solid var(--line, #ccc); border-radius: 8px; background: var(--bg); color: var(--fg); }
dialog#viewer::backdrop { background: rgba(0,0,0,.55); }
#viewer .vbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--line, #ccc); position: sticky; top: 0; background: var(--bg); }
#viewer .vbar b { margin-right: auto; }
#viewer .vimg { overflow: auto; height: calc(100% - 52px); text-align: center; }
#viewer img { max-width: 100%; height: auto; }
__NAVCSS__
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
__CITYBAR__
<header>
  __CITYNAV__
  <h1>Adressbücher der Stadt Zürich 1859–1945</h1>
  <p class="sub">Stand __DATE__ · Einwohnerverzeichnisse und Berufsregister der Bände 1859, 1867, 1875, 1885, 1900, 1901, 1902, 1903, 1904, 1907, 1909, 1910, 1914, 1920, 1922, 1925, 1930, 1935, 1940 und 1945.</p>
</header>
<section class="note" aria-label="Hinweis zu den Daten">
  <p><b>Maschinell gelesen, nicht von Hand korrigiert.</b> Der Text stammt vom Sprachmodell qwen3.8 (Universität Bern) und wurde weder nachkorrigiert noch von Hand stichprobenweise geprüft. Rechnen Sie mit Fehlern in Namen und Strassen, besonders 1859 und 1867 (Fraktur). Ein Klick auf die <b>Seite</b> zeigt das Seitenbild (Zentralbibliothek Zürich) zum Vergleich.</p>
  <details id="about">
    <summary>Über die Daten: Umfang, Lücken, Lizenz</summary>
    <div class="cols">
      <div>
        <h2>Bände</h2>
        <ul>__VOLLIST__</ul>
        <h2>Gebiet</h2>
        <ul>
          <li><b>1859:</b> «g» bzw. «k» an der Hausnummer = Grosse Stadt (rechts der Limmat) bzw. Kleine Stadt (links). Es sind die alten Hausnummern.</li>
          <li><b>1867:</b> die Ausgemeinde, wenn der Eintrag sie nennt («… 235 Enge», «In Riesbach»); Einträge in der Stadt selbst haben kein Gebiet.</li>
          <li><b>1875, 1885:</b> die alte Gemeinde hinter der Hausnummer (A. Aussersihl, E. Enge, F. Fluntern, Hi. Hirslanden, Ho. Hottingen, O. Oberstrass, R. Riesbach, U. Unterstrass, W. Wiedikon, Z. Zürich). Sie gehören seit 1893 zur Stadt; die Hausnummern sind die der alten Gemeinde.</li>
          <li><b>1900–1910:</b> Stadtkreis I–V, <b>1914–1930:</b> Kreis 1–8, <b>1935–1945:</b> Kreis 1–11 (Eingemeindung 1934: Kreis 9 Altstetten und Albisrieden, 10 Höngg und Wipkingen, 11 Affoltern, Oerlikon, Seebach und Schwamendingen; Witikon kam zu Kreis 7). Wer ausserhalb wohnte, hat seine Gemeinde (Zollikon, Kilchberg …).</li>
        </ul>
      </div>
      <div>
        <h2>Nicht enthalten</h2>
        <ul>
          <li>Inserate, Vorspann, Behörden, Vereine, Strassen- und Häuserverzeichnisse, Warenverzeichnis, Querverweise.</li>
          <li>1901: auf 13 Seiten bricht die Lesung vor dem Seitenende ab (S. 35, 49, 93, 121, 316, 321, 372, 381, 429, 504, 578, 615, 645), 1902 auf 14 (S. 49, 97, 117, 147, 154, 282, 339, 348, 370, 375, 417, 475, 481, 516), 1903 auf 4 (S. 49, 183, 276, 336), 1904 auf 14 (S. 61, 103, 129, 139, 157, 259, 267, 305, 321, 401, 409, 426, 482, 593), 1907 auf 12 (53, 113, 168, 217, 250, 266, 341, 416, 473, 519, 601, 632), 1909 auf 14 (S. 48, 53, 62, 85, 87, 171, 197, 369, 401, 405, 469, 491, 501, 515), 1910 auf 17 (S. 68, 77, 129, 181, 210, 213, 271, 337, 382, 389, 453, 468, 479, 550, 583, 591, 663), 1914 auf 11 vor dem Seitenende ab (S. 62, 70, 97, 120, 353, 374, 397, 413, 477, 532, 587), 1920 auf 8 (S. 316, 711, 715, 720, 797, 870, 877, 885), 1922 auf 15 (S. 45, 117, 193, 391, 460, 473, 517, 639, 719, 801, 843, 849, 913, 935, 941), 1925 auf 17 (S. 33, 60, 89, 129, 152, 305, 553, 586, 588, 601, 606, 745, 808, 810, 873, 919, 1047), 1930 auf 15 (S. 312, 435, 469, 483, 509, 714, 831, 923, 983, 1013, 1071, 1171, 1221, 1307, 1308), 1935 auf 4 (S. 201, 1206, 1443, 1444), 1940 auf 3 (S. 1108, 1409, 1525), 1945 auf 20 (S. 58, 67, 74, 222, 246, 262, 373, 494, 501, 576, 603, 646, 723, 742, 1186, 1195, 1506, 1516, 1562, 1598). 1930 bis 1945 steht der Kreis als eingekreiste Ziffer, die das Modell oft als ☎ las; dann kommt der Kreis aus der Strasse (Flag «kreis_aus_strasse»). 1900 und 1903 haben kein Berufsregister. 1901, S. 607 (Fuhrhalter): das Modell setzte das Telefon bei allen Einträgen, gedruckt ist es nicht bei allen.</li>
        </ul>
        <h2>Telefonbuch</h2>
        <ul><li>Einträge mit Telefon sind, wo möglich, mit dem PTT-Telefonbuch verbunden: zuerst über die gedruckte Nummer und den Familiennamen (höchstens 5 Jahre Abstand), sonst über die Verknüpfung von <a href="https://thodel.github.io/vernetzte-schweiz/">Vernetzte Schweiz</a>, sonst wenn im Telefonbuch der Gemeinde genau eine Person mit diesem Namen und Vornamen steht. __TELSTAT__</li></ul>
        <h2>Verknüpfungen</h2>
        <ul>
          <li><b>Andere Bände:</b> __NOTHER__ Einträge sind automatisch mit derselben Person in mindestens einem anderen Band verbunden (gleicher Familienname, passender Vorname, dazu Beruf, Strasse, Allianzname); mehrdeutige Fälle bleiben offen.</li>
          <li><b>Normdaten:</b> __NAUTH__ Einträge haben einen <b>ungeprüften</b> Kandidaten aus dem HLS bzw. Wikidata (Person mit Bezug zur Gemeinde, lebte im Jahr des Bandes, Name und Vorname passen, Beruf passt zum Feld oder der Name ist selten).</li>
          <li><b>Karte damals:</b> Link auf die Siegfriedkarte des Jahres (swisstopo Zeitreise) an der Strasse (Lage nach OpenStreetMap, nur wenn sie im Quartier des gedruckten Kreises bzw. der alten Gemeinde liegt), sonst an der Stadtmitte. Dazu die <a href="karte.html">Karte</a> aller Einträge.</li>
        </ul>
        <h2>Seitenbilder</h2>
        <ul><li>Die Scans stammen von der <a href="https://zop.zb.uzh.ch/collections/9e5087c3-e5f8-4b76-a106-3b5fc830a0f7">Zentralbibliothek Zürich (Zurich Open Platform)</a>, dort unter CC0; die Seite lädt sie über IIIF direkt von der ZB. «Seite» ist die Seite im PDF der ZB und zugleich die Bildnummer im IIIF-Manifest. Je Band: __IIIFLIST__</li></ul>
        <h2>Lizenz</h2>
        <ul><li>Die Bände bis 1914 sind gemeinfrei; die Scans aller Bände, auch 1920–1945, gibt die Zentralbibliothek Zürich unter CC0 frei. Daten <a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0 1.0</a>, Code <a href="__REPO__/blob/main/LICENSE">MIT</a>. CSV im <a href="__REPO__/tree/main/data/csv">Repo</a>.</li></ul>
      </div>
    </div>
  </details>
</section>
<div class="toolbar">
  <div class="tabs" role="tablist" id="tabs"></div>
  <select id="vol" aria-label="Band"><option value="1914">1914</option><option value="1945">1945</option><option value="1940">1940</option><option value="1935">1935</option><option value="1930">1930</option><option value="1925">1925</option><option value="1922">1922</option><option value="1920">1920</option><option value="1910">1910</option><option value="1909">1909</option><option value="1907">1907</option><option value="1904">1904</option><option value="1903">1903</option><option value="1902">1902</option><option value="1901">1901</option><option value="1900">1900</option><option value="1885">1885</option><option value="1875">1875</option><option value="1867">1867</option><option value="1859">1859</option><option value="">alle Bände (gross)</option></select>
  <select id="area" aria-label="Gebiet"><option value="">alle Gebiete</option></select>
  <select id="conf" aria-label="Konfidenz"><option value="">alle Konfidenzen</option><option value="high">high</option><option value="medium">medium</option></select>
  <select id="qa" aria-label="Hinweis"><option value="">alle Hinweise</option><option value="-">ohne Hinweis</option></select>
  <input id="street" type="search" list="streets" placeholder="Strasse …" aria-label="Strasse (Anfang)">
  <datalist id="streets"></datalist>
  <select id="tel" aria-label="Telefon"><option value="">Telefon: alle</option><option value="1">mit ☏</option><option value="link">mit Telefonbuch-Eintrag</option><option value="none">☏, kein Eintrag gefunden</option></select>
  <span class="chip" id="skchip" hidden>Strasse (Karte) = <b id="sklabel"></b><button type="button" id="skclear" aria-label="Strassenfilter entfernen">✕</button></span>
  <label><input type="checkbox" id="onlyflag"> nur markierte</label>
  <input id="q" type="search" placeholder="Suchen: Name, Beruf, Strasse, Rubrik, ID …" aria-label="Suchen">
  <span class="count" id="count" aria-live="polite"></span>
</div>
__FSPANEL__
<div class="flagbar">
  <span><span class="n" id="nflags">0</span> Flags in diesem Browser · <span id="nreported">0</span> bereits im Repo gemeldet</span>
  <button class="btn primary" id="dl">Flags als CSV herunterladen</button>
  <button class="btn" id="copy">CSV in die Zwischenablage</button>
  <button class="btn" id="clear">Flags löschen</button>
  <span class="sub">Danach: <code>python scripts/91_merge_flags.py &lt;datei.csv&gt;</code> und committen.</span>
</div>
<p class="legend"><b>Seite</b> = Seite im PDF der ZB, anklicken zeigt das Seitenbild · <b>Gebiet</b> = Kreis bzw. alte Gemeinde wie gedruckt · <b>Strasse</b> anklicken filtert · <b>Konfidenz</b>: high = keine Auffälligkeit, medium = ein Hinweis spricht für Prüfung · <b>Hinweise</b>: Maus darüber für Erklärung · <b>☏</b> = Telefon genannt · <b>Telefonbuch</b>: passender Eintrag im PTT-Telefonbuch, Link auf die Person bei Vernetzte Schweiz und aufs Seitenbild; «nummer» = gleiche Nummer und Name, «name» = einzige Person mit Name und Vorname, sonst die Stufe der Verknüpfung von Vernetzte Schweiz · <b>Andere Bände</b>: dieselbe Person in anderen Bänden (automatisch; <b>fett</b> = sicher, normal = wahrscheinlich, <i>kursiv</i> = möglich; Maus darüber zeigt den Eintrag) · <b>Normdaten</b>: ungeprüfte Kandidaten aus HLS und Wikidata · <b>Karte damals</b>: Siegfriedkarte des Jahres bei swisstopo · <b>✓</b> = Flag schon im Repo</p>
<div class="wrap"><table id="t"><thead></thead><tbody></tbody></table><div class="loading" id="loading" hidden>Band wird geladen …</div><button class="more" id="more" hidden>weitere Zeilen zeigen</button></div>
<footer>Daten CC0 1.0 · Code MIT · Quelle für <a href="https://thodel.github.io/vernetzte-schweiz/">Vernetzte Schweiz 1860–1914</a></footer>
<div id="toast" hidden></div>
<dialog id="viewer" aria-label="Seitenbild">
  <div class="vbar"><b id="vtitle"></b>
    <button class="btn" id="vprev" aria-label="vorige Seite">‹ Seite</button><button class="btn" id="vnext" aria-label="nächste Seite">Seite ›</button>
    <a id="vfull" target="_blank" rel="noopener">volle Grösse ↗</a> · <a id="vzb" target="_blank" rel="noopener">bei der ZB ↗</a>
    <button class="btn" id="vclose" aria-label="schliessen">✕</button></div>
  <div class="vimg"><img id="vimg" alt=""></div>
</dialog>
<script>
__FSJS__
const FSTX = __FSTX__;
const META = __META__;
const LABELS = __LABELS__;
const QA = __QA__;
const GEO = __GEO__;
const HOW = {nummer: 'gleiche Telefonnummer und Familienname', sicher: 'Vernetzte Schweiz: sicher', wahrscheinlich: 'Vernetzte Schweiz: wahrscheinlich', möglich: 'Vernetzte Schweiz: möglich (nur Name)', name: 'einzige Person dieses Namens und Vornamens im Telefonbuch der Gemeinde'};
const REASONS = __REASONS__;
const REPORTED = __REPORTED__;
const REPO = "__REPO__";
const PAGE = 300;
const KEY = 'zuerich.flags.v1';
const VOLS = {};   // «Band|Reiter» → Zeilen
const P = new URLSearchParams(location.search);
let tab = P.get('tab') && META.tabs[P.get('tab')] ? P.get('tab') : 'einwohner';
let shown = PAGE;
let skF = P.get('sk') || '';
let flags = {};
try { flags = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { flags = {}; }
const reported = {}; for (const f of REPORTED) reported[f.table + '|' + f.id] = f;
const $ = id => document.getElementById(id);
const tabsEl = $('tabs'), q = $('q'), vol = $('vol'), conf = $('conf'), qa = $('qa'), street = $('street'), tel = $('tel'), onlyflag = $('onlyflag');
const thead = document.querySelector('#t thead'), tbody = document.querySelector('#t tbody'), more = $('more'), count = $('count');
for (const k in QA) { const o = document.createElement('option'); o.value = k; o.textContent = QA[k]; qa.appendChild(o); }
for (const k in META.tabs) { const b = document.createElement('button'); b.setAttribute('role', 'tab'); b.textContent = `${META.tabs[k].label} (${META.tabs[k].n.toLocaleString('de-CH')})`; b.dataset.k = k; b.onclick = () => { tab = k; shown = PAGE; render(); }; tabsEl.appendChild(b); }
function esc(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function save() { try { localStorage.setItem(KEY, JSON.stringify(flags)); } catch (e) {} }
function toast(msg) { const t = $('toast'); t.textContent = msg; t.hidden = false; setTimeout(() => { t.hidden = true; }, 2500); }
function loadVol(v) {
  const k = v + '|' + tab;
  if (VOLS[k]) return Promise.resolve(VOLS[k]);
  if (!META.files[k]) return Promise.resolve(VOLS[k] = []);
  return fetch(`data/${v}-${tab}.json`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(d => (VOLS[k] = d));
}
function wanted() { return vol.value ? [vol.value] : Object.keys(META.volumes); }
function issueUrl(r) {
  const cols = META.tabs[tab].cols, id = r[0];
  const body = `Tabelle: ${META.tabs[tab].label}\nID: ${id}\nBand ${r[1]}, PDF-Seite ${r[2]}\n\nGelesene Zeile:\n${r[cols.indexOf('text')] ?? ''}\n\nProblem:\n`;
  return `${REPO}/issues/new?title=${encodeURIComponent('Flag ' + id)}&labels=${encodeURIComponent('review')}&body=${encodeURIComponent(body)}`;
}
function cell(col, v, r) {
  if (col === 'other_volume') {
    if (!v) return '<td></td>';
    return '<td>' + v.split(';;').map(x => { const [tier, ov, oid, otext, ev] = x.split('|');
      return `<a class="ov ${esc(tier)}" href="?tab=einwohner&vol=${esc(ov)}&q=${encodeURIComponent(oid)}" title="${esc(tier + ': ' + otext + ' · ' + ev)}">${esc(ov)}</a>`; }).join(' ') + '</td>';
  }
  if (col === 'authority') {
    if (!v) return '<td></td>';
    const [tier, label, life, hls, qid, gnd, field, note] = v.split('|');
    const links = [hls ? `<a href="https://hls-dhs-dss.ch/de/articles/${esc(hls)}/" target="_blank" rel="noopener">HLS</a>` : '',
      qid ? `<a href="https://www.wikidata.org/wiki/${esc(qid)}" target="_blank" rel="noopener">Wikidata</a>` : '',
      gnd ? `<a href="https://d-nb.info/gnd/${esc(gnd)}" target="_blank" rel="noopener">GND</a>` : ''].filter(Boolean).join(' · ');
    return `<td class="wide" title="${esc(field + (note ? ' · ' + note : ''))}">${esc(label)} <small>${esc(life)}</small> · ${links} <span class="pill ${tier === 'wahrscheinlich' ? 'high' : 'medium'}" title="ungeprüfter Kandidat">${esc(tier)}</span></td>`;
  }
  if (col === 'zeitreise') {
    const cols = META.tabs[tab].cols, sk = r[cols.indexOf('street_key')], ar = r[cols.indexOf('area')];
    const hit = sk ? (GEO[ar + '|' + sk] || GEO['|' + sk]) : null;
    const g = hit || GEO['|'], exact = !!hit;
    return `<td><a href="https://map.geo.admin.ch/#/map?lang=de&center=${g[0]},${g[1]}&z=${exact ? 11 : 9}&crosshair=marker&bgLayer=void&layers=ch.swisstopo.zeitreihen@year=${esc(r[1])}" target="_blank" rel="noopener" title="${exact ? 'Strasse' : 'Gemeinde'} auf der Siegfriedkarte ${esc(r[1])} (swisstopo Zeitreise)">${exact ? 'Strasse' : 'Ort'} ${esc(r[1])} ↗</a></td>`;
  }

  if (col === 'page') return META.iiif[r[1]] ? `<td class="num"><button type="button" class="pg" data-v="${esc(r[1])}" data-p="${esc(v)}" title="Seitenbild anzeigen (Zentralbibliothek Zürich)">${esc(v)}</button></td>` : `<td class="num" title="Seite im PDF">${esc(v)}</td>`;
  if (col === 'parse_confidence') return `<td><span class="pill ${esc(v)}">${esc(v)}</span></td>`;
  if (col === 'phone_flag') return `<td class="num">${v === '1' ? '<span class="star" title="Telefon">☏</span>' : ''}</td>`;
  if (col === 'street_raw') return `<td>${v ? `<button type="button" class="st" data-s="${esc(v)}" title="nach ${esc(v)} filtern">${esc(v)}</button>` : ''}</td>`;
  if (col === 'telefon') {
    if (!v) return r[META.tabs[tab].cols.indexOf('phone_flag')] === '1' ? '<td class="sub">nicht gefunden</td>' : '<td></td>';
    const [how, year, name, st, phone, eid, img] = v.split('|');
    const tip = `Telefonbuch ${year}: ${name}${st ? ', ' + st : ''}${phone ? ', Nr. ' + phone : ''} · Zuordnung: ${HOW[how] || how}`;
    const main = eid ? `<a href="https://thodel.github.io/vernetzte-schweiz/#/e/${esc(eid)}" target="_blank" rel="noopener" title="${esc(tip)}">${esc(year)}${phone ? ' · Nr. ' + esc(phone) : ''}</a>` : `<span title="${esc(tip)}">${esc(year)}</span>`;
    return `<td>${main}${img ? ` · <a href="${esc(img)}" target="_blank" rel="noopener" title="Seite im Telefonbuch (PTT-Archiv)">Bild</a>` : ''} <span class="pill ${how === 'nummer' || how === 'sicher' ? 'high' : 'medium'}" title="${esc(HOW[how] || how)}">${esc(how)}</span></td>`;
  }
  if (col === 'qa_flags') return `<td>${v ? v.split(' ').map(x => `<span class="qa" title="${esc(QA[x] || x)}">${esc(x)}</span>`).join('') : ''}</td>`;
  if (col === 'entry_id') return `<td class="id">${esc(v)}</td>`;
  if (['building_no','volume'].includes(col)) return `<td class="num">${esc(v)}</td>`;
  if (['occupation_raw','text'].includes(col)) return `<td class="wide">${esc(v)}</td>`;
  return `<td>${esc(v)}</td>`;
}
function actCell(r) {
  const key = tab + '|' + r[0], f = flags[key] || {};
  const opts = ['<option value="">— Flag —</option>'].concat(REASONS.map(x => `<option value="${esc(x)}" ${f.reason === x ? 'selected' : ''}>${esc(x)}</option>`)).join('');
  return `<td class="act"><select data-key="${esc(key)}" data-f="reason" aria-label="Grund">${opts}</select> <input type="text" data-key="${esc(key)}" data-f="note" placeholder="Notiz" value="${esc(f.note || '')}" aria-label="Notiz"><a href="${issueUrl(r)}" target="_blank" rel="noopener">Issue</a></td>`;
}
// Seitenbild: IIIF der Zentralbibliothek Zürich; Bild-IDs je Band erst beim ersten Öffnen laden
const IIIF = {};
function loadIiif(v) { return IIIF[v] ? Promise.resolve(IIIF[v]) : fetch(`data/${v}-iiif.json`).then(r => r.json()).then(d => (IIIF[v] = d)); }
let cur = null;
function showPage(v, p) {
  cur = [v, p];  // sofort setzen: schnelle Klicks auf ‹ › zählen weiter, bevor die Bild-IDs geladen sind
  loadIiif(v).then(ids => {
    p = Math.max(1, Math.min(ids.length, p)); cur = [v, p];
    const base = META.iiif_base + ids[p - 1];
    $('vtitle').textContent = `Band ${v}, Seite ${p} von ${ids.length}`;
    $('vimg').src = base + '/full/!1400,2000/0/default.jpg';
    $('vimg').alt = `Seitenbild ${v}, Seite ${p}`;
    $('vfull').href = base + '/full/max/0/default.jpg';
    $('vzb').href = META.iiif[v].handle;
    if (!$('viewer').open) $('viewer').showModal();
  }).catch(() => toast('Seitenbild nicht erreichbar'));
}
document.addEventListener('click', e => { const b = e.target.closest('button.pg'); if (b) showPage(b.dataset.v, +b.dataset.p); });
$('vprev').onclick = () => cur && showPage(cur[0], cur[1] - 1);
$('vnext').onclick = () => cur && showPage(cur[0], cur[1] + 1);
$('vclose').onclick = () => $('viewer').close();
$('viewer').addEventListener('keydown', e => { if (e.key === 'ArrowLeft') $('vprev').click(); if (e.key === 'ArrowRight') $('vnext').click(); });
const areaSel = $('area');
let areaKey = '';
function areaList(rows, ai) {
  const key = tab + '|' + vol.value; if (key === areaKey) return; areaKey = key;
  const n = {}; for (const r of rows) if (r[ai]) n[r[ai]] = (n[r[ai]] || 0) + 1;
  const cur = areaSel.value || P.get('area') || '';
  areaSel.innerHTML = '<option value="">alle Gebiete</option>' + Object.entries(n).sort((x, y) => x[0].localeCompare(y[0], 'de', {numeric: true})).map(([s, c]) => `<option value="${esc(s)}">${esc(s)} (${c.toLocaleString('de-CH')})</option>`).join('');
  areaSel.value = n[cur] ? cur : '';
}
let streetKey = '';
function streetList(rows, si) {
  const key = tab + '|' + vol.value; if (key === streetKey) return; streetKey = key;
  const n = {}; for (const r of rows) if (r[si]) n[r[si]] = (n[r[si]] || 0) + 1;
  $('streets').innerHTML = Object.entries(n).sort((a, b) => b[1] - a[1]).slice(0, 500).map(([s, c]) => `<option value="${esc(s)}">${c}</option>`).join('');
}
function syncUrl() {
  const p = new URLSearchParams();
  p.set('tab', tab); p.set('vol', vol.value || 'alle');
  if (areaSel.value) p.set('area', areaSel.value); if (conf.value) p.set('conf', conf.value); if (qa.value) p.set('qa', qa.value); if (tel.value) p.set('tel', tel.value); if (skF) p.set('sk', skF);
  if (street.value.trim()) p.set('str', street.value.trim());
  if (q.value.trim()) p.set('q', q.value.trim());
  FS.toParams(p);
  history.replaceState(null, '', location.pathname + '?' + p.toString() + (location.hash === '#suche' ? '#suche' : ''));
}
let seq = 0, fsTab = '';
function render() {
  for (const b of tabsEl.children) b.setAttribute('aria-selected', b.dataset.k === tab);
  const vs = wanted(), my = ++seq;
  if (vs.some(v => !VOLS[v + '|' + tab])) {
    $('loading').hidden = false; $('loading').textContent = 'Band wird geladen …';
    Promise.all(vs.map(loadVol)).then(() => { if (my === seq) render(); }, e => { $('loading').textContent = 'Band konnte nicht geladen werden (' + e.message + ').'; });
    return;
  }
  $('loading').hidden = true;
  if (tab !== fsTab) { fsTab = tab; FS.refresh(); }
  const hide = META.tabs[tab].hide;
  const cols = META.tabs[tab].cols, oi = META.tabs[tab].cols.indexOf('other_volume'), all = vs.flatMap(v => VOLS[v + '|' + tab]);
  const ai = cols.indexOf('area'), a = areaSel.value;
  areaList(all, ai);
  const needle = q.value.trim().toLowerCase(), c = conf.value, h = qa.value, s = street.value.trim().toLowerCase();
  const ci = cols.indexOf('parse_confidence'), hi = cols.indexOf('qa_flags'), si = cols.indexOf('street_raw');
  const pi = cols.indexOf('phone_flag'), ti = cols.indexOf('telefon'), t = tel.value, ki = cols.indexOf('street_key');
  $('skchip').hidden = !skF; if (skF) $('sklabel').textContent = skF;
  streetList(all, si);
  const rows = all.filter(r => (!c || r[ci] === c)
    && (!h || (h === '-' ? !r[hi] : (' ' + r[hi] + ' ').includes(' ' + h + ' ')))
    && (!s || r[si].toLowerCase().startsWith(s))
    && (!skF || r[ki] === skF)
    && (!a || r[ai] === a)
    && (!t || (t === '1' ? r[pi] === '1' : t === 'link' ? !!r[ti] : r[pi] === '1' && !r[ti]))
    && (!onlyflag.checked || flags[tab + '|' + r[0]] || reported[tab + '|' + r[0]])
    && (!needle || r.filter((_, i) => i !== oi).join(' ').toLowerCase().includes(needle))
    && FS.test(r, cols));
  thead.innerHTML = '<tr><th>Flag</th>' + cols.filter(cc => !hide.includes(cc)).map(cc => `<th>${esc(LABELS[cc] || cc)}</th>`).join('') + '</tr>';
  tbody.innerHTML = rows.slice(0, shown).map(r => {
    const key = tab + '|' + r[0];
    const cls = (flags[key] && flags[key].reason ? 'flagged ' : '') + (reported[key] ? 'reported' : '');
    return `<tr class="${cls}" title="${reported[key] ? esc('gemeldet: ' + reported[key].reason + ' ' + reported[key].note) : ''}">${actCell(r)}${r.map((vv, i) => hide.includes(cols[i]) ? '' : cell(cols[i], vv, r)).join('')}</tr>`;
  }).join('');
  more.hidden = rows.length <= shown;
  count.textContent = `${Math.min(shown, rows.length).toLocaleString('de-CH')} von ${rows.length.toLocaleString('de-CH')} Zeilen` + (tab === 'berufe' && vol.value === '1900' ? ' · 1900 hat kein Berufsregister' : '');
  $('nflags').textContent = Object.values(flags).filter(f => f.reason).length;
  $('nreported').textContent = REPORTED.length;
  syncUrl();
}
tbody.addEventListener('change', e => {
  const el = e.target, key = el.dataset.key; if (!key) return;
  flags[key] = flags[key] || {}; flags[key][el.dataset.f] = el.value;
  if (!flags[key].reason && !flags[key].note) delete flags[key];
  save(); const tr = el.closest('tr'); tr.classList.toggle('flagged', !!(flags[key] && flags[key].reason)); $('nflags').textContent = Object.values(flags).filter(f => f.reason).length;
});
tbody.addEventListener('click', e => {
  const b = e.target.closest('button.st'); if (!b) return;
  street.value = b.dataset.s; shown = PAGE; render();
});
function flagsCsv() {
  const q2 = s => '"' + String(s ?? '').replace(/"/g, '""') + '"';
  const lines = ['table,id,reason,note,by,date'];
  const today = new Date().toISOString().slice(0, 10);
  for (const key in flags) { const f = flags[key]; if (!f.reason) continue; const [t, id] = key.split('|'); lines.push([t, id, f.reason, f.note || '', '', today].map(q2).join(',')); }
  return lines.join('\n') + '\n';
}
$('dl').onclick = () => {
  const blob = new Blob(['﻿' + flagsCsv()], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `flags_zuerich_${new Date().toISOString().slice(0, 10)}.csv`; document.body.appendChild(a); a.click(); a.remove();
  toast('CSV wird heruntergeladen (falls gesperrt: Zwischenablage nutzen)');
};
$('copy').onclick = () => {
  const text = flagsCsv();
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(() => toast('CSV kopiert'), () => fallbackCopy(text)); else fallbackCopy(text);
};
function fallbackCopy(text) { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); toast('CSV kopiert'); } catch (e) { toast('Kopieren nicht möglich: Text ist markiert'); } ta.remove(); }
$('clear').onclick = () => { if (!Object.keys(flags).length) return; flags = {}; save(); render(); toast('Flags gelöscht'); };
more.onclick = () => { shown += PAGE; render(); };
for (const el of [q, street]) el.addEventListener('input', () => { shown = PAGE; render(); });
for (const el of [vol, areaSel, conf, qa, tel, onlyflag]) el.addEventListener('change', () => { shown = PAGE; render(); });
if (P.get('vol')) vol.value = P.get('vol') === 'alle' ? '' : P.get('vol');
if (P.get('conf')) conf.value = P.get('conf');
if (P.get('qa')) qa.value = P.get('qa');
if (P.get('tel')) tel.value = P.get('tel');
$('skclear').onclick = () => { skF = ''; shown = PAGE; render(); };
if (P.get('str')) street.value = P.get('str');
if (P.get('q')) q.value = P.get('q');
FS.init({ cols: () => META.tabs[tab].cols, skip: ['street_key', 'zeitreise', 'telefon', 'other_volume', 'authority'], labels: LABELS, tx: FSTX, first: 'surname', onChange: () => { shown = PAGE; render(); } });
render();
</script>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True, help="Zielordner")
    args = ap.parse_args()
    rows = load_rows()
    (args.out / "data").mkdir(parents=True, exist_ok=True)
    files = {}
    for v in VOLUMES:
        for k in rows[v]:
            if not rows[v][k]:
                continue
            p = args.out / "data" / f"{v}-{k}.json"
            p.write_text(json.dumps(rows[v][k], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            files[f"{v}|{k}"] = len(rows[v][k])
            print(f"{v} {k}: {len(rows[v][k])} → {p} ({p.stat().st_size / 1e6:.1f} MB)")
    iiif = {}
    vrows = {r["volume"]: r for r in csv.DictReader((CSV_DIR / "01_iiif_volumes.csv").open(encoding="utf-8"))}
    ids = {}
    for r in csv.DictReader((CSV_DIR / "01_iiif_pages.csv").open(encoding="utf-8")):
        assert r["iiif_image"].startswith(IIIF_BASE) and int(r["page"]) == len(ids.setdefault(r["volume"], [])) + 1
        ids[r["volume"]].append(r["iiif_image"].removeprefix(IIIF_BASE))
    for v in VOLUMES:
        if v in ids:
            (args.out / "data" / f"{v}-iiif.json").write_text(json.dumps(ids[v], separators=(",", ":")), encoding="utf-8")
            iiif[v] = {"handle": vrows[v]["handle"], "doi": vrows[v]["doi"], "manifest": vrows[v]["manifest"]}
    n = {k: Counter() for k, *_ in TABS}
    for v in rows:
        for k in rows[v]:
            n[k][v] = len(rows[v][k])
    meta = {"volumes": VOLUMES, "files": files, "iiif": iiif, "iiif_base": IIIF_BASE,
            "tabs": {k: {"label": label, "cols": cols, "n": sum(n[k].values()),
                         "hide": cols[cols.index("street_key"):]}  # Schlüssel und weitere CSV-Spalten: nur für die Suche
                     for k, label, _f, cols in TABS}}
    ti = {k: cols.index("phone_flag") for k, _l, _f, cols in TABS}
    n_tel = sum(1 for v in rows for k in rows[v] for r in rows[v][k] if r[ti[k]] == "1")
    fmt = lambda x: f"{x:,}".replace(",", " ")
    reported = load_flags()
    html = (TEMPLATE.replace("__CITYBAR__", site_nav.city_bar("zuerich"))
            .replace("__CITYNAV__", site_nav.city_nav("Zürich 1859–1945", REPO_URL, "entries"))
            .replace("__NAVCSS__", site_nav.CSS).replace("__FSPANEL__", site_nav.search_panel())
            .replace("__FSJS__", site_nav.FIELD_SEARCH_JS).replace("__FSTX__", json.dumps(site_nav.fs_texts(), ensure_ascii=False))
            .replace("__META__", json.dumps(meta, ensure_ascii=False))
            .replace("__LABELS__", json.dumps(LABELS, ensure_ascii=False))
            .replace("__QA__", json.dumps(QA, ensure_ascii=False))
            .replace("__GEO__", json.dumps(GEO, ensure_ascii=False, separators=(",", ":")))
            .replace("__NOTHER__", f"{len(OTHER):,}".replace(",", "\u202f"))
            .replace("__NAUTH__", f"{len(AUTH):,}".replace(",", "\u202f"))
            .replace("__REASONS__", json.dumps(REASONS, ensure_ascii=False))
            .replace("__REPORTED__", json.dumps(reported, ensure_ascii=False))
            .replace("__VOLLIST__", "".join(f"<li><b>{v}</b> · {VOLUMES[v]}: {fmt(n['einwohner'][v])} Einwohner"
                                            + (f", {fmt(n['berufe'][v])} im Berufsregister" if n['berufe'][v] else ", kein Berufsregister") + "</li>"
                                            for v in sorted(VOLUMES)))
            .replace("__TELSTAT__", f"{len(PHONE):,} von {n_tel:,} Einträgen mit Telefon haben einen Treffer.".replace(",", "\u202f"))
            .replace("__IIIFLIST__", " · ".join(f'<a href="{iiif[v]["doi"]}">{v}</a> (<a href="{iiif[v]["manifest"]}">IIIF</a>)' for v in sorted(iiif)))
            .replace("__REPO__", REPO_URL)
            .replace("__DATE__", date.today().strftime("%d.%m.%Y")))
    (args.out / "index.html").write_text(html, encoding="utf-8")
    site_fonts.copy(args.out)
    print(f"{len(reported)} gemeldete Flags → {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
