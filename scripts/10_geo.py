"""10_geo.py — Strassen für die Karte verorten (Zürich 1859–1945).

    python scripts/10_geo.py streets      # Nominatim, 1 Anfrage/s, Cache in web/geo/
    python scripts/10_geo.py todo         # Hand-Liste web/geo/streets_manual.csv

Jeder Eintrag bekommt ein **Gebiet** (`area`): die Spalte `district` aus scripts/convert.py, ausserhalb der Stadt
die Gemeinde. Ohne die Spalte gilt dieselbe Regel aus dem gedruckten Text:

- 1859: «g» bzw. «k» an der Hausnummer → Grosse Stadt (rechts der Limmat) bzw. Kleine Stadt (links).
- 1875, 1885: die alte Gemeinde hinter der Hausnummer («Rankstrasse 77 R.» → Riesbach; Z. = Stadt Zürich).
- 1900–1913: der Stadtkreis I–V vor der Strasse; 1914–1930: der Kreis 1–8; 1935–1945: der Kreis 1–11 (Eingemeindung 1934).

Verortet wird je (Gebiet, Strasse), nie die Hausnummer: die Nummern von 1859 (g/k) und die der Ausgemeinden
1875/1885 sind alte Nummern. Ein Treffer von Nominatim zählt nur, wenn er in einem Quartier liegt, das zum Gebiet
gehört (Riesbach = Seefeld, Mühlebach, Weinegg …), und der Strassenname passt. 1900, 1914, 1920 und 1922 tragen schon die
vereinheitlichten Namen nach der Eingemeindung von 1893; dort darf eine Strasse auch knapp im Nachbarquartier
liegen, solange es in der Stadt nur eine Strasse dieses Namens gibt (`method = stadt`). 1859–1885 nicht:
gleichnamige Strassen der alten Gemeinden wurden 1893 umbenannt.

Ergebnis: web/geo/streets.csv (area, street_norm, entries, method, lat, lon, osm_name). Was OSM nicht kennt,
kann in web/geo/streets_manual.csv (area, street_norm, …, lat, lon, source, note) von Hand gesetzt werden;
`todo` schreibt die Liste der häufigsten offenen Strassen, schon gesetzte Zeilen bleiben.

Die Daten in data/csv bleiben unverändert.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

CSV_DIR = Path("data/csv")
GEO = Path("web/geo")
CACHE = GEO / "nominatim_cache.json"
MANUAL = GEO / "streets_manual.csv"
UA = "adressbuch-geocoder/0.1 (historical address books, low volume)"
BASE = "https://nominatim.openstreetmap.org/search"
BOX = (8.44, 47.31, 8.63, 47.44)  # Stadt Zürich heute: lon_min, lat_min, lon_max, lat_max
MIN_ENTRIES = 3

# Gebiet → heutige Quartiere (wie sie in Nominatims display_name stehen)
ALTSTADT = {"Rathaus", "Hochschulen", "Lindenhof", "City"}
QUARTIERE = {
    "Grosse Stadt": {"Rathaus", "Hochschulen"},
    "Kleine Stadt": {"Lindenhof", "City"},
    "Zürich": ALTSTADT,
    "Aussersihl": {"Werd", "Langstrasse", "Hard", "Gewerbeschule", "Escher Wyss"},
    "Enge": {"Enge"},
    "Fluntern": {"Fluntern"},
    "Hirslanden": {"Hirslanden"},
    "Hottingen": {"Hottingen"},
    "Oberstrass": {"Oberstrass"},
    "Riesbach": {"Seefeld", "Mühlebach", "Weinegg"},
    "Unterstrass": {"Unterstrass"},
    "Wiedikon": {"Alt-Wiedikon", "Sihlfeld", "Friesenberg"},
    # Kreise 1893–1913
    "Kreis I": ALTSTADT,
    "Kreis II": {"Enge", "Wollishofen", "Leimbach"},
    "Kreis III": {"Werd", "Langstrasse", "Hard", "Gewerbeschule", "Escher Wyss", "Alt-Wiedikon", "Sihlfeld", "Friesenberg"},
    "Kreis IV": {"Oberstrass", "Unterstrass", "Wipkingen"},
    "Kreis V": {"Fluntern", "Hottingen", "Hirslanden", "Seefeld", "Mühlebach", "Weinegg"},
    # Kreise ab 1913
    "Kreis 1": ALTSTADT,
    "Kreis 2": {"Enge", "Wollishofen", "Leimbach"},
    "Kreis 3": {"Alt-Wiedikon", "Sihlfeld", "Friesenberg"},
    "Kreis 4": {"Werd", "Langstrasse", "Hard"},
    "Kreis 5": {"Gewerbeschule", "Escher Wyss"},
    "Kreis 6": {"Oberstrass", "Unterstrass", "Wipkingen"},
    "Kreis 7": {"Fluntern", "Hottingen", "Hirslanden", "Witikon"},  # Witikon seit 1934
    "Kreis 8": {"Seefeld", "Mühlebach", "Weinegg"},
    # Eingemeindung 1934: neue Kreise 9–11 (Wipkingen kam von Kreis 6 zu Kreis 10)
    "Kreis 9": {"Altstetten", "Albisrieden"},
    "Kreis 10": {"Höngg", "Wipkingen"},
    "Kreis 11": {"Affoltern", "Oerlikon", "Seebach", "Saatlen", "Schwamendingen-Mitte", "Hirzenbach"},
}
OLD = {"Z": "Zürich", "Zürich": "Zürich", "A": "Aussersihl", "Aussersihl": "Aussersihl", "E": "Enge", "Enge": "Enge",
       "F": "Fluntern", "Fl": "Fluntern", "Fluntern": "Fluntern", "Hi": "Hirslanden", "Hl": "Hirslanden",
       "Hirs": "Hirslanden", "Hirslanden": "Hirslanden", "Ho": "Hottingen", "Hottingen": "Hottingen",
       "O": "Oberstrass", "Oberstr": "Oberstrass", "Oberstrass": "Oberstrass", "R": "Riesbach", "Riesb": "Riesbach",
       "Riesbach": "Riesbach", "U": "Unterstrass", "Unterstr": "Unterstrass", "Unterstrass": "Unterstrass",
       "W": "Wiedikon", "Wiedikon": "Wiedikon"}


def norm_street(s: str) -> str:
    """Gedruckte Strasse → Schlüssel: «Seefeldstr.» → «Seefeldstrasse», «Schützeng.» → «Schützengasse»,
    «gr. Brunngasse» → «Grosse Brunngasse», «Bahnhofpl.» → «Bahnhofplatz»."""
    s = re.sub(r"\s+", " ", s.replace("ß", "ss")).strip(" ,;.")
    s = re.sub(r"(?i)\bgr\.\s*", "Grosse ", s)
    s = re.sub(r"(?i)\bkl\.\s*", "Kleine ", s)
    s = re.sub(r"(?i)str\.?$", "strasse", s)
    if not re.search(r"(?i)(weg|berg|burg|steig|steg|hag|ring)\.?$", s):
        s = re.sub(r"(?i)(\w)g\.?$", r"\1gasse", s)
    s = re.sub(r"(?i)pl\.?$", "platz", s)
    s = re.sub(r"(?i)\bstr\.\s", "strasse ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:1].upper() + s[1:]


KREIS_VOLS = {"1900", "1901", "1902", "1903", "1904", "1907", "1909", "1910", "1911", "1913", "1914", "1915", "1920", "1922", "1925", "1930", "1935", "1940", "1945"}  # Bände mit Stadtkreis vor der Strasse

def area(r: dict) -> str:
    """Gebiet des Eintrags aus Band und gedrucktem Text (siehe oben); leer, wenn nichts dasteht."""
    v, t, st, no = r["volume"], r.get("text", ""), r.get("street_raw", ""), r.get("building_no", "")
    if r.get("municipality", "Zürich") != "Zürich":
        return r["municipality"]
    if "district" in r:  # Spalte aus scripts/convert.py
        return r["district"]
    if v == "1859":
        gk = re.sub(r"[^gk]", "", no)
        return {"g": "Grosse Stadt", "k": "Kleine Stadt"}.get(gk, "")
    if v in ("1875", "1885"):
        i = t.rfind(no) if no else -1
        tail = t[i + len(no):] if i >= 0 else (t[t.find(st) + len(st):] if st and st in t else "")
        m = re.match(r"[\s.]*([A-ZÄÖÜ][a-zäöü]{0,11})\.?", tail)
        return OLD.get(m.group(1), "") if m else ""
    if v in KREIS_VOLS and st:
        i = t.find(st[:6])
        kr = r"[IV]{1,3}|1[01]|[1-9]" if int(v) >= 1934 else r"[IV]{1,3}|[1-8]"  # ab 1934 Kreise 1–11
        m = re.search(rf"(?:^|[\s,])({kr})\s*$", t[:i]) if i > 0 else None
        if m and (v in ("1900", "1901", "1902", "1903", "1904", "1907", "1909", "1910", "1911", "1913")) == (not m.group(1).isdigit()):
            return "Kreis " + m.group(1)
    return ""


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("ß", "ss")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[-'’.]", " ", s)).strip()


def name_matches(res: dict, st: str) -> bool:
    """Der Strassenname des Treffers muss der gedruckte sein («Seefeldstrasse», nicht «Seefeldquai»)."""
    road = fold(res.get("display_name", "").split(",")[0])
    if res.get("display_name", "").split(",")[0].strip().isdigit():  # «54, Seefeldstrasse, …»
        road = fold(res["display_name"].split(",")[1])
    return road == fold(st)


def quartier(res: dict) -> set[str]:
    return {c.strip() for c in res.get("display_name", "").split(",")}


def inside(lat: float, lon: float) -> bool:
    return BOX[0] <= lon <= BOX[2] and BOX[1] <= lat <= BOX[3]


def query(params: dict, cache: dict) -> list:
    key = urllib.parse.urlencode(sorted(params.items()))
    if key not in cache:
        url = BASE + "?" + urllib.parse.urlencode({**params, "format": "jsonv2", "countrycodes": "ch", "limit": 10})
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            cache[key] = json.load(resp)
        time.sleep(1.1)
    return cache[key]


def register_files(kind: str) -> list[Path]:
    """Die Dateien eines Verzeichnisses, je Band eine: kind = «entries» (Einwohner) oder «berufe»."""
    return sorted(CSV_DIR.glob(f"04_{kind}_*.csv"))


def entries():
    for f in (*register_files("entries"), *register_files("berufe")):
        with f.open(encoding="utf-8") as fh:
            yield from csv.DictReader(fh)


def streets_in_data() -> tuple[Counter, dict]:
    """(Gebiet, Strasse) → Anzahl; dazu je Schlüssel die Bände (für die Regel «nur Kreis-Bände grosszügig»)."""
    c, vols = Counter(), {}
    for r in entries():
        if r["street_raw"]:
            k = (area(r), norm_street(r["street_raw"]))
            c[k] += 1
            vols.setdefault(k, set()).add(r["volume"])
    return c, vols


def manual_points() -> dict[tuple[str, str], tuple[float, float]]:
    """Von Hand gesetzte Punkte: (Gebiet, Strasse) → (lat, lon); Gebiet leer = gilt für jedes Gebiet."""
    if not MANUAL.exists():
        return {}
    return {(r["area"], r["street_norm"]): (float(r["lat"]), float(r["lon"]))
            for r in csv.DictReader(MANUAL.open(encoding="utf-8")) if r.get("lat", "").strip()}


def point(pts: dict, area_: str, st: str):
    """Punkt für (Gebiet, Strasse): aus streets.csv/Hand-Liste, sonst Hand-Punkt ohne Gebiet."""
    return pts.get((area_, st)) or pts.get(("", st))


def streets(limit: int | None) -> None:
    GEO.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    manual = manual_points()
    todo, vols = streets_in_data()
    out = []
    for i, ((ar, st), n) in enumerate(todo.most_common()):
        if limit and i >= limit:
            break
        hit, method = None, "selten"
        if point(manual, ar, st):
            lat, lon = point(manual, ar, st)
            hit, method = {"lat": lat, "lon": lon, "display_name": "von Hand (streets_manual.csv)"}, "manual"
        elif ar and ar not in QUARTIERE:
            method = "ausserhalb"  # eigene Gemeinde 1914 (Zollikon …): die Karte zeigt die Gemeinde
        elif n >= MIN_ENTRIES:
            method = "none"
            try:
                res = query({"street": st, "city": "Zürich"}, cache)
            except Exception as e:
                print(f"  Fehler {st}: {e}")
                res = []
            res = [r for r in res if inside(float(r["lat"]), float(r["lon"])) and name_matches(r, st)
                   and "Zürich" in quartier(r)]
            want = QUARTIERE.get(ar)
            ok = [r for r in res if want and quartier(r) & want]
            if ok:
                hit, method = ok[0], "quartier"
            elif res and (not ar or vols[(ar, st)] <= KREIS_VOLS):
                # Name eindeutig in der Stadt (Punkte höchstens 1.5 km auseinander = dieselbe Strasse)
                lats, lons = [float(r["lat"]) for r in res], [float(r["lon"]) for r in res]
                if max(lats) - min(lats) < 0.014 and max(lons) - min(lons) < 0.02:
                    hit, method = res[0], "stadt"
        out.append({"area": ar, "street_norm": st, "entries": n, "method": method,
                    "lat": f"{float(hit['lat']):.6f}" if hit else "", "lon": f"{float(hit['lon']):.6f}" if hit else "",
                    "osm_name": hit.get("display_name", "")[:120] if hit else ""})
        if i % 100 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"{i}/{len(todo)}", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    with (GEO / "streets.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: (r["area"], r["street_norm"])))
    found = sum(1 for r in out if r["lat"])
    print(f"{found}/{len(out)} Strassen verortet ({sum(r['entries'] for r in out if r['lat'])} von "
          f"{sum(r['entries'] for r in out)} Einträgen mit Strasse) → {GEO / 'streets.csv'}")


def todo(min_entries: int) -> None:
    """Hand-Liste: offene (Gebiet, Strasse) mit ≥ min_entries Einträgen, nach Einträgen sortiert."""
    keep = {}
    if MANUAL.exists():
        keep = {(r["area"], r["street_norm"]): r for r in csv.DictReader(MANUAL.open(encoding="utf-8"))}
    rows = []
    for r in csv.DictReader((GEO / "streets.csv").open(encoding="utf-8")):
        k = (r["area"], r["street_norm"])
        old = keep.pop(k, None)
        if old is None and (r["lat"] or int(r["entries"]) < min_entries or r["method"] == "ausserhalb"):
            continue
        rows.append({"area": k[0], "street_norm": k[1], "entries": r["entries"],
                     **{f: (old or {}).get(f, "") for f in ("lat", "lon", "source", "note")}})
    rows += [{**r, "entries": 0} for r in keep.values()]
    rows.sort(key=lambda r: (-int(r["entries"]), r["area"], r["street_norm"]))
    with MANUAL.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["area", "street_norm", "entries", "lat", "lon", "source", "note"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} Strassen in {MANUAL} ({sum(1 for r in rows if r['lat'])} mit Punkt)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("streets")
    s.add_argument("--limit", type=int)
    t = sub.add_parser("todo")
    t.add_argument("--min", type=int, default=20)
    args = ap.parse_args()
    if args.cmd == "streets":
        streets(args.limit)
    else:
        todo(args.min)


if __name__ == "__main__":
    main()
