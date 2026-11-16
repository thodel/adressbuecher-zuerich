"""Warteschlange der fehlenden Zürcher Bände für den Wochenlauf (scripts/weekly/README.md).

    python3 scripts/weekly/make_queue.py      # zop_liste.csv → queue.csv

Aus `zop_liste.csv` (Liste der ZB, je Band PDF und Handle) werden die Adressbücher bis 1945
genommen, ohne Stadtpläne und ohne Bände, die schon gelesen sind oder auf tei laufen
(run_zh2.sh: 1930, 1935, 1940, 1945). Je Band wird der Handle über die ZOP-Schnittstelle in die
Item-UUID und das IIIF-Manifest aufgelöst. Gelesen wird über IIIF, nicht aus dem PDF.

Reihenfolge und Ströme:
- `A` (ab 1900): 1901–1913, dann 1915–1944 aufsteigend, sofort;
- `B` (vor 1900): 1899 absteigend bis 1877, frühestens ab 15.12.2026.
Je Strom höchstens 10 Bände je Kalenderwoche (Montag–Sonntag).
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONE = {1859, 1867, 1875, 1885, 1900, 1914, 1920, 1922, 1925, 1930, 1935, 1940, 1945}
UA = {"User-Agent": "adressbuecher-zuerich (Universitaet Bern, DH)"}
B_FROM = "2026-12-15"


def resolve(handle: str) -> str:
    """Handle → Item-UUID (ZOP leitet /server/api/pid/find auf das Item um)."""
    h = handle.split("/handle/")[1]
    req = urllib.request.Request(f"https://zop.zb.uzh.ch/server/api/pid/find?id={h}", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.geturl().rstrip("/").rsplit("/", 1)[1]


def main() -> None:
    rows = [r for r in csv.DictReader(open(HERE / "zop_liste.csv", encoding="utf-8"))
            if not r["datei"].startswith("Stadtplan") and int(r["jahr"]) <= 1945 and int(r["jahr"]) not in DONE]
    a = sorted((r for r in rows if int(r["jahr"]) >= 1900), key=lambda r: int(r["jahr"]))
    b = sorted((r for r in rows if int(r["jahr"]) < 1900), key=lambda r: -int(r["jahr"]))
    out = []
    for stream, part, not_before in (("A", a, ""), ("B", b, B_FROM)):
        for r in part:
            uuid = resolve(r["handle"])
            out.append({"year": r["jahr"], "stream": stream, "not_before": not_before, "title": r["titel"],
                        "handle": r["handle"], "uuid": uuid,
                        "manifest": f"https://zop.zb.uzh.ch/server/iiif/{uuid}/manifest", "pdf_bytes": r["bytes"]})
            time.sleep(0.3)
    with open(HERE / "queue.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print(f"queue.csv: {len(out)} Bände (A {len(a)}, B {len(b)})")


if __name__ == "__main__":
    main()
