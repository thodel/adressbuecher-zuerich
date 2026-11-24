"""92_karte.py — Karte der Einträge nach Strasse (GitHub Pages).

    python scripts/92_karte.py --out web/karte.html

Liest data/csv/04_entries_<Band>.csv, 04_berufe_<Band>.csv und die Punkte aus web/geo/ (scripts/10_geo.py) und schreibt
eine Seite mit Leaflet: Kreise je Strasse, Fläche nach Zahl der Einträge, wählbar
nach Band, Verzeichnis und «nur mit Telefon». Ein Klick führt zu den Einträgen auf der Hauptseite.

Strassenpunkte: OpenStreetMap (heutige Strassenmitte), verortet je Gebiet (1859 Grosse/Kleine Stadt,
1875/1885 alte Gemeinde, 1900–1945 Kreis; siehe 10_geo.py), sonst von Hand (web/geo/streets_manual.csv).
Dieselbe Strasse am selben Punkt aus mehreren Gebieten bzw. Bänden ist ein Kreis. Strassen ohne Punkt
fehlen auf der Karte und werden gezählt; nie verortet wird die Hausnummer.
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import site_nav  # noqa: E402  gemeinsame Navigation
import site_fonts  # noqa: E402  Schriften lokal (fonts/)
_geo = importlib.import_module("10_geo")
norm_street, area_of, manual_points, point = _geo.norm_street, _geo.area, _geo.manual_points, _geo.point

CSV_DIR = Path("data/csv")
GEO = Path("web/geo")
TELEFON = Path("web/telefon.csv")
REPO_URL = "https://github.com/thodel/adressbuecher-zuerich"
VOLS = ["1859", "1867", "1875", "1885", "1900", "1901", "1902", "1903", "1904", "1907", "1909", "1910", "1911", "1914", "1920", "1922", "1925", "1930", "1935", "1940", "1945"]


def counts():
    """(Gemeinde) bzw. (Gemeinde, Strasse) → Zähler je «<Band><e|b>[t]» (t = mit Telefon)."""
    muni, street = defaultdict(Counter), defaultdict(Counter)
    variants = defaultdict(Counter)
    linked = set()
    if TELEFON.exists():
        linked = {r["entry_id"] for r in csv.DictReader(TELEFON.open(encoding="utf-8"))}
    files = [(f, "e") for f in _geo.register_files("entries")] + [(f, "b") for f in _geo.register_files("berufe")]
    for f, tab in files:
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if not r["municipality"]:
                continue
            keys = [r["volume"] + tab] + ([r["volume"] + tab + "t"] if r["phone_flag"] == "1" else [])
            for k in keys:
                muni[r["municipality"]][k] += 1
            if r["street_raw"]:
                sk = (area_of(r), norm_street(r["street_raw"]))
                for k in keys:
                    street[sk][k] += 1
                variants[sk][r["street_raw"]] += 1
    return muni, street, variants, len(linked)


def load_points(name: str, key) -> dict:
    p = GEO / name
    if not p.exists():
        return {}
    return {key(r): (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(p.open(encoding="utf-8")) if r["lat"]}


TEMPLATE = r"""<!doctype html>
<html lang="de">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Karte Zürich 1859–1945</title>
<meta name="description" content="Karte der Einträge der Adressbücher der Stadt Zürich 1859–1945 nach Strasse.">
<link rel="stylesheet" href="fonts/fonts.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
/* Layout: Karte füllt den Rest unter einem schmalen Kopf mit Steuerung. */
:root { --bg: #f6f5f1; --paper: #ffffff; --fg: #1d2129; --muted: #5c6370; --line: #d9d7cf; --accent: #7a2e2e;
  --street: #7a2e2e; --muni: #2d5f7a; --font-body: "Source Sans 3", "Segoe UI", system-ui, sans-serif; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #15171b; --paper: #1d2026; --fg: #e8e6df;
  --muted: #a39f94; --line: #353942; --accent: #d08a84; --street: #e0928b; --muni: #7fb6d6; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #15171b; --paper: #1d2026; --fg: #e8e6df; --muted: #a39f94; --line: #353942;
  --accent: #d08a84; --street: #e0928b; --muni: #7fb6d6; color-scheme: dark }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: var(--font-body); font-size: 15px; line-height: 1.4;
  display: flex; flex-direction: column; box-sizing: border-box;
  padding: 16px max(16px, env(safe-area-inset-right, 0px)) 16px max(16px, env(safe-area-inset-left, 0px)); gap: 10px; }
header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 20px; }
.nav { font-size: 0.9rem; color: var(--muted); }
.nav a, .sub a, .leaflet-popup-content a { color: var(--accent); }
.nav a { font-weight: 600; text-decoration: none; }
h1 { font-size: 1.3rem; margin: 0; text-wrap: balance; }
.sub { color: var(--muted); font-size: 0.88rem; margin: 0; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; font-size: 0.92rem; }
select { font: inherit; padding: 5px 9px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper); color: var(--fg); }
select:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.key { display: inline-flex; align-items: center; gap: 5px; color: var(--muted); }
.dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; opacity: .8; }
#map { flex: 1 1 auto; min-height: 420px; border: 1px solid var(--line); border-radius: 8px; }
.leaflet-container { font-family: var(--font-body); }
.leaflet-popup-content { font-size: 14px; }
.leaflet-popup-content b { font-weight: 700; }
@media (max-width: 600px) { #map { min-height: 65vh; } }
__NAVCSS__
</style>
__CITYBAR__
<header>
  __CITYNAV__
  <h1>Karte: Adressbücher der Stadt Zürich 1859–1945</h1>
  <p class="sub">Stand __DATE__ · Kreisfläche = Zahl der Einträge je Strasse. Lage: heutige Strassenmitte nach OpenStreetMap, nur wenn sie im Quartier des gedruckten Kreises bzw. der alten Gemeinde liegt; Hausnummern werden nicht verortet (1859 und in den Ausgemeinden alte Nummern). __UNPLACED__</p>
</header>
<div class="toolbar">
  <select id="vol" aria-label="Band"><option value="1914">1914</option><option value="1945">1945</option><option value="1940">1940</option><option value="1935">1935</option><option value="1930">1930</option><option value="1925">1925</option><option value="1922">1922</option><option value="1920">1920</option><option value="1911">1911</option><option value="1910">1910</option><option value="1909">1909</option><option value="1907">1907</option><option value="1904">1904</option><option value="1903">1903</option><option value="1902">1902</option><option value="1901">1901</option><option value="1900">1900</option><option value="1885">1885</option><option value="1875">1875</option><option value="1867">1867</option><option value="1859">1859</option><option value="">alle Bände</option></select>
  <select id="tab" aria-label="Verzeichnis"><option value="">Einwohner und Berufsregister</option><option value="e">Einwohner</option><option value="b">Berufsregister</option></select>
  <label><input type="checkbox" id="tel"> nur mit Telefon ☏</label>
  <input type="checkbox" id="showMuni" hidden>
  <input type="checkbox" id="showStreet" checked hidden>
  <span class="sub" id="sum" aria-live="polite"></span>
</div>
<div id="map" role="region" aria-label="Karte"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const MUNI = __MUNI__;      // [Name, lat, lon, {Zähler}]
const STREETS = __STREETS__; // [Gebiete, Strasse, lat, lon, {Zähler}, [Schreibweisen]]
const $ = id => document.getElementById(id);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function esc(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
const map = L.map('map', { scrollWheelZoom: true }).setView([47.374, 8.535], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
const muniLayer = L.layerGroup().addTo(map), streetLayer = L.layerGroup().addTo(map);
function n(c) {
  const vols = $('vol').value ? [$('vol').value] : __VOLS__, tabs = $('tab').value ? [$('tab').value] : ['e', 'b'], t = $('tel').checked ? 't' : '';
  let s = 0; for (const v of vols) for (const k of tabs) s += c[v + k + t] || 0; return s;
}
function link(params) {
  const p = new URLSearchParams({ tab: $('tab').value === 'b' ? 'berufe' : 'einwohner', ...params });
  if ($('vol').value) p.set('vol', $('vol').value);
  if ($('tel').checked) p.set('tel', '1');
  return 'index.html?' + p.toString();
}
function draw() {
  muniLayer.clearLayers(); streetLayer.clearLayers();
  const mc = css('--muni'), sc = css('--street');
  let tm = 0, ts = 0;
  const maxM = Math.max(1, ...MUNI.map(m => n(m[3]))), maxS = Math.max(1, ...STREETS.map(x => n(x[4])));  // Fläche relativ zum grössten Kreis
  if ($('showMuni').checked) for (const [name, lat, lon, c] of MUNI) {
    const k = n(c); tm += k; if (!k) continue;
    L.circleMarker([lat, lon], { radius: 4 + 36 * Math.sqrt(k / maxM), color: mc, weight: 1.5, fillColor: mc, fillOpacity: 0.25 })
      .bindPopup(`<b>${esc(name)}</b><br>${k.toLocaleString('de-CH')} Einträge<br><a href="${link({ gem: name })}">Einträge zeigen</a>`)
      .bindTooltip(`${name}: ${k}`).addTo(muniLayer);
  }
  if ($('showStreet').checked) for (const [m, st, lat, lon, c, vars] of STREETS) {
    const k = n(c); ts += k; if (!k) continue;
    L.circleMarker([lat, lon], { radius: 2.5 + 22 * Math.sqrt(k / maxS), color: sc, weight: 1, fillColor: sc, fillOpacity: 0.5 })
      .bindPopup(`<b>${esc(st)}</b><br>${k.toLocaleString('de-CH')} Einträge<br><small>${esc(m)}</small><br><small>gedruckt: ${vars.map(esc).join(', ')}</small><br><a href="${link({ sk: st })}">Einträge zeigen</a>`)
      .bindTooltip(`${st}: ${k}`).addTo(streetLayer);
  }
  $('sum').textContent = `${ts.toLocaleString('de-CH')} Einträge an verorteten Strassen`;
}
for (const id of ['vol', 'tab', 'tel', 'showMuni', 'showStreet']) $(id).addEventListener('change', draw);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
draw();
</script>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    muni, street, variants, _ = counts()
    spts = load_points("streets.csv", lambda r: (r["area"], r["street_norm"]))
    manual = manual_points()
    M = []  # eine Stadt: keine Gemeindekreise
    merged: dict = {}
    lost_streets, lost_entries = 0, 0
    for (a, st), c in sorted(street.items()):
        pt = point(manual, a, st) or spts.get((a, st))
        if not pt:
            lost_streets += 1
            lost_entries += sum(v for k, v in c.items() if not k.endswith("t"))
            continue
        k = (st, round(pt[0], 4), round(pt[1], 4))  # dieselbe Strasse am selben Punkt: ein Kreis
        e = merged.setdefault(k, [set(), st, *pt, Counter(), Counter()])
        e[0].add(a or "ohne Gebiet")
        e[4].update(c)
        e[5].update(variants[(a, st)])
    S = [[", ".join(sorted(e[0])), e[1], e[2], e[3], dict(e[4]), [v for v, _ in e[5].most_common(4)]] for e in merged.values()]
    total = sum(sum(v for k, v in c.items() if not k.endswith("t")) for c in street.values())
    fmt = lambda x: f"{x:,}".replace(",", "\u202f")
    placed = total - lost_entries
    unplaced = (f"{fmt(placed)} von {fmt(total)} Einträgen mit Strasse verortet ({len(street) - lost_streets} von {len(street)} Strassen je Gebiet); "
                f"die übrigen stehen an Strassen ohne Punkt (anderer Name heute, selten gedruckt oder Lesefehler).")
    html = (TEMPLATE.replace("__CITYBAR__", site_nav.city_bar('zuerich', 'de')).replace("__CITYNAV__", site_nav.city_nav('Zürich 1859–1945', 'https://github.com/thodel/adressbuecher-zuerich', "map", 'de')).replace("__NAVCSS__", site_nav.CSS).replace("__MUNI__", json.dumps(M, ensure_ascii=False, separators=(",", ":")))
            .replace("__STREETS__", json.dumps(S, ensure_ascii=False, separators=(",", ":")))
            .replace("__VOLS__", json.dumps(VOLS)).replace("__UNPLACED__", unplaced).replace("__REPO__", REPO_URL)
            .replace("__DATE__", date.today().strftime("%d.%m.%Y")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    site_fonts.copy(args.out)
    print(f"{unplaced} → {args.out}")


if __name__ == "__main__":
    main()
