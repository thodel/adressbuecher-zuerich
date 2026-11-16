"""zh_classify.py — jede Seite eines Zürcher Bandes einem Teil zuordnen (läuft auf tei).

    python3 zh_classify.py --pages weekly/1901/iiif_pages.csv --out weekly/1901/classify.csv

Je Seite ein kleines Bild (600 px breit) direkt von der ZB (IIIF, CC0), nichts wird gespeichert.
qwen3.8-27b (GPUStack, Schlüssel aus der Umgebung, nie ausgegeben) antwortet mit Teil und Schrift.
Daraus bestimmt zh_weekly.py die Seitenbereiche (Einwohner, Berufe) und ob der Band Fraktur ist.
Fortsetzbar: schon zugeordnete Seiten werden übersprungen.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = {"User-Agent": "adressbuecher-zuerich (Universitaet Bern, DH)"}
PARTS = ("einwohner", "berufe", "haeuser", "strassen", "behoerden", "inserate", "andere")
PROMPT = """Du siehst eine Seite aus einem Zürcher Adressbuch (1877–1945). Antworte NUR mit einem JSON-Objekt,
ohne Markdown: {"teil": "...", "schrift": "..."}.
teil, genau eines von:
- "einwohner": alphabetisches Verzeichnis der Einwohner und Firmen (Familienname, Vorname, Beruf, Adresse)
- "berufe": Verzeichnis nach Berufen oder Branchen (Zwischentitel sind Berufe, darunter Namen mit Adresse)
- "haeuser": Verzeichnis nach Strassen und Hausnummern (Eigentümer, Bewohner je Haus)
- "strassen": Strassenverzeichnis (nur Strassennamen, Kreise, Lage)
- "behoerden": Behörden, Ämter, Vereine, Institutionen, Kirchen, Schulen, Tarife, Kalender
- "inserate": ganzseitige Anzeigen oder Reklame
- "andere": Titelblatt, Inhaltsverzeichnis, leere Seite, Karte, Vorwort
schrift: "fraktur" oder "antiqua" (die Schrift der Einträge, nicht der Titel)."""


def image(url: str) -> str:
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return base64.b64encode(r.read()).decode()
        except OSError:
            if i == 4:
                raise
            time.sleep(10 * (i + 1))
    return ""


def ask(b64: str) -> dict:
    base = os.environ["GPUSTACK_BASE_URL"].rstrip("/")
    body = {"model": os.environ.get("ZH_MODEL", "qwen3.8-27b"), "temperature": 0, "max_tokens": 60,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": PROMPT}]}]}
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GPUSTACK_API_KEY']}",
                                          "Content-Type": "application/json"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                text = json.loads(r.read())["choices"][0]["message"].get("content") or ""
            m = re.search(r"\{.*\}", text, re.S)
            d = json.loads(m.group()) if m else {}
            part = d.get("teil", "") if d.get("teil", "") in PARTS else "andere"
            script = d.get("schrift", "") if d.get("schrift", "") in ("fraktur", "antiqua") else ""
            return {"part": part, "script": script}
        except (OSError, ValueError):
            if i == 3:
                return {"part": "", "script": ""}
            time.sleep(30 * (i + 1))
    return {"part": "", "script": ""}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="iiif_pages.csv des Bandes (page, iiif_image)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    done = {}
    if out.exists():
        done = {int(r["page"]): r for r in csv.DictReader(open(out, encoding="utf-8")) if r["part"]}
    pages = [r for r in csv.DictReader(open(a.pages, encoding="utf-8")) if int(r["page"]) not in done]

    def one(r: dict) -> dict:
        res = ask(image(f"{r['iiif_image']}/full/600,/0/default.jpg"))
        return {"page": int(r["page"]), **res}

    with ThreadPoolExecutor(a.workers) as ex:
        for res in ex.map(one, pages):
            done[res["page"]] = res
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page", "part", "script"])
        w.writeheader()
        w.writerows(sorted(done.values(), key=lambda r: int(r["page"])))
    print(f"{out}: {len(done)} Seiten zugeordnet")


if __name__ == "__main__":
    main()
