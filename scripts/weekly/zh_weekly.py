"""zh_weekly.py — Wochenlauf für die fehlenden Zürcher Bände auf tei (scripts/weekly/README.md).

    python3 zh_weekly.py            # vom cron täglich um 01:15 gestartet (siehe crontab.txt)
    python3 zh_weekly.py --status   # Stand ausgeben
    python3 zh_weekly.py --years 1900-1920   # nur diese Jahrgänge, aufsteigend, ohne Wochenbudget
                                             # (seit 18.11.2026 so im cron, stündlich; immer nur ein Band)

Je Kalenderwoche (Montag–Sonntag) liest der Lauf je Strom höchstens 10 Bände (queue.csv:
Strom A ab 1900 sofort, Strom B vor 1900 ab 15.12.2026). Je Band:
1. Manifest der ZB holen, Seitentabelle schreiben (weekly/<Jahr>/iiif_pages.csv).
2. Seiten zuordnen (zh_classify.py, kleines Bild je Seite): Seitenbereiche Einwohner und Berufe.
   Die Schrift, die qwen dabei nennt, ist unzuverlässig (Antiqua 1901 hiess «fraktur»); sie steht
   nur als Hinweis `fraktur_hinweis` im Stand. Ob ein Band Fraktur ist, prüft der Wochenauftrag auf
   dem Mac am Seitenbild; Fraktur-Bände liest er dort mit Gemini neu.
3. Bilder der beiden Teile holen (fetch_iiif.py, halbe Breite des Scans, etwa 150 dpi), mit
   qwen3.8-27b lesen (run_qwen.py, 2× vergrössert, zwei Durchgänge), sammeln (collect.py).
4. Ergebnis auf den Forschungsspeicher, Seitenbilder löschen (wieder holbar über IIIF).
Läuft schon ein anderer Lesedurchgang (run_qwen.py, etwa run_zh2.sh), wartet der Lauf bis
zum nächsten Tag. Ein Sperrfile verhindert zwei Läufe gleichzeitig. Kein Schlüssel wird ausgegeben.
"""
from __future__ import annotations

import csv
import datetime as dt
import fcntl
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent          # /home/dh/adressbuch_qwen/weekly
WORK = HERE.parent                              # /home/dh/adressbuch_qwen (run_qwen.py, collect.py, fetch_iiif.py)
SHARE = Path("/mnt/wbkolleg_dh_1/tei/adressbuch_qwen")
STATE = HERE / "state.json"
LOG = HERE / "weekly.log"
PER_WEEK = 10
YEARS: tuple[int, int] | None = None            # --years 1900-1920: nur diese Jahrgänge, ohne Wochenbudget
UA = {"User-Agent": "adressbuecher-zuerich (Universitaet Bern, DH)"}
TZ = dt.timezone(dt.timedelta(hours=1))         # MEZ; die Woche zählt nach Schweizer Datum
OTHERS = "run_qwen.py|be_weekly.py"             # solange einer davon läuft, wartet Zürich


def log(msg: str) -> None:
    line = f"{dt.datetime.now(TZ):%d.%m %H:%M} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(st: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1))
    tmp.rename(STATE)
    subprocess.run(["rsync", "-t", str(STATE), str(SHARE / "weekly_state.json")], check=False)


def busy() -> bool:
    """Läuft gerade ein anderer Lesedurchgang auf dem GPU-Dienst, oder liest der Berner Lauf
    (adressbuecher-bern/scripts/weekly/be_weekly.py) gerade einen Band?"""
    r = subprocess.run(["pgrep", "-f", OTHERS], capture_output=True, text=True)
    return bool(r.stdout.strip())


def week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def pages_table(year: str, manifest: str, d: Path) -> list[dict]:
    with urllib.request.urlopen(urllib.request.Request(manifest, headers=UA), timeout=120) as r:
        m = json.loads(r.read())
    canvases = m.get("items") or m["sequences"][0]["canvases"]
    rows = []
    for n, c in enumerate(canvases, 1):
        try:
            svc = c["images"][0]["resource"]["service"]["@id"]           # IIIF Presentation 2
        except (KeyError, IndexError):
            svc = c["items"][0]["items"][0]["body"]["service"][0]["id"]   # Presentation 3
        rows.append({"volume": year, "page": n, "canvas": c.get("@id") or c.get("id"), "iiif_image": svc,
                     "width": c.get("width", 0)})
    with open(d / "iiif_pages.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    return rows


def sections(classify: Path) -> tuple[dict, float]:
    """Seitenbereiche aus der Zuordnung: der grösste Block je Teil (Lücken bis 8 Seiten, etwa
    eingestreute Inserate, gehören dazu). Dazu der Anteil Fraktur im Einwohnerteil."""
    rows = [r for r in csv.DictReader(open(classify, encoding="utf-8"))]
    out = {}
    for part in ("einwohner", "berufe"):
        ps = sorted(int(r["page"]) for r in rows if r["part"] == part)
        blocks, cur = [], []
        for p in ps:
            if cur and p - cur[-1] > 8:
                blocks.append(cur); cur = []
            cur.append(p)
        if cur:
            blocks.append(cur)
        best = max(blocks, key=len, default=[])
        if len(best) >= 5:
            out[part] = [best[0], best[-1]]
    if "einwohner" in out and "berufe" in out and out["berufe"][0] <= out["einwohner"][1]:
        out["berufe"][0] = out["einwohner"][1] + 1          # überlappt nie
    lo, hi = out.get("einwohner", [0, -1])
    sc = [r["script"] for r in rows if lo <= int(r["page"]) <= hi and r["script"]]
    fraktur = sc.count("fraktur") / len(sc) if sc else 0.0
    return out, fraktur


def run(cmd: list[str], logfile: Path) -> int:
    with open(logfile, "a") as f:
        return subprocess.run(cmd, cwd=WORK, stdout=f, stderr=subprocess.STDOUT).returncode


def process(q: dict, st: dict) -> None:
    year = q["year"]
    d = HERE / year
    d.mkdir(exist_ok=True)
    s = st.setdefault(year, {"stream": q["stream"]})
    s.update(status="läuft", week=week(dt.datetime.now(TZ).date()), started=f"{dt.datetime.now(TZ):%Y-%m-%d %H:%M}")
    save_state(st)
    rows = pages_table(year, q["manifest"], d)
    log(f"{year}: Manifest {len(rows)} Seiten; ordne Seiten zu")
    run([sys.executable, str(HERE / "zh_classify.py"), "--pages", str(d / "iiif_pages.csv"), "--out", str(d / "classify.csv")], d / "run.log")
    secs, fraktur = sections(d / "classify.csv")
    s.update(sections=secs, pages=len(rows))
    if "einwohner" not in secs:
        s["status"] = "fehler: kein Einwohnerteil erkannt"; save_state(st); log(f"{year}: {s['status']}"); return
    s["fraktur_hinweis"] = round(fraktur, 2)
    width = max(800, min(1200, round(int(rows[len(rows) // 2]["width"] or 2000) / 2)))
    ranges = ",".join(f"{a}-{b}" for a, b in secs.values())
    vol = f"zurich{year}"
    out = WORK / "full" / vol
    (out / "results").mkdir(parents=True, exist_ok=True)
    log(f"{year}: Teile {secs}, hole Bilder ({width} px)")
    if run([sys.executable, "fetch_iiif.py", "--volume", year, "--width", str(width), "--pages", ranges,
            "--table", str(d / "iiif_pages.csv"), "--out", str(out / "pages")], d / "run.log"):
        s["status"] = "fehler: Bilder"; save_state(st); log(f"{year}: Bilder nicht vollständig"); return
    for p in (1, 2):
        todo = [str(f) for f in sorted((out / "pages").glob("*.jpeg"))
                if '"ended": true' not in ((out / "results" / f"{f.stem}_x2.json").read_text()
                                            if (out / "results" / f"{f.stem}_x2.json").exists() else "")]
        log(f"{year}: Durchgang {p}, {len(todo)} Seiten")
        if todo:
            run([sys.executable, "run_qwen.py", "--workers", "4", "--upscale", "2", "--out", str(out / "results"), *todo], out / "run.log")
    run([sys.executable, "collect.py", str(out / "results"), "--volume", vol, "--out", str(out / "entries.csv")], d / "run.log")
    n = sum(1 for _ in open(out / "entries.csv", encoding="utf-8")) - 1 if (out / "entries.csv").exists() else 0
    subprocess.run(["rsync", "-rt", "--exclude", "pages/", f"{out}/", str(SHARE / "full" / vol) + "/"], check=False)
    subprocess.run(["rsync", "-rt", f"{d}/", str(SHARE / "weekly" / year) + "/"], check=False)
    subprocess.run(["rm", "-rf", str(out / "pages")], check=False)     # Seitenbilder löschen, über IIIF wieder holbar
    s.update(status="gelesen", entries=n, finished=f"{dt.datetime.now(TZ):%Y-%m-%d %H:%M}", width=width)
    save_state(st)
    log(f"{year}: gelesen, {n} Einträge; Bilder gelöscht")


def load_env() -> None:
    """GPUSTACK_* aus tei's .env.gpustack lesen (die Datei hat Zeilen, an denen `sh` scheitert).
    Werte werden nie ausgegeben."""
    f = Path("/home/dh/agentic_historian/.env.gpustack")
    if "GPUSTACK_API_KEY" in os.environ or not f.exists():
        return
    for line in f.read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep and k.startswith("GPUSTACK_"):
            os.environ[k] = v.strip().strip('"').strip("'")


def main() -> None:
    global YEARS
    if "--years" in sys.argv:
        a, _, b = sys.argv[sys.argv.index("--years") + 1].partition("-")
        YEARS = (int(a), int(b or a))
    load_env()
    st = load_state()
    if "--status" in sys.argv:
        for y, s in sorted(st.items()):
            print(y, s.get("stream"), s.get("status"), s.get("week"), s.get("entries", ""), s.get("sections", ""))
        return
    lock = open(HERE / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return                                            # ein Lauf ist schon unterwegs
    queue = list(csv.DictReader(open(HERE / "queue.csv", encoding="utf-8")))
    # Wir halten die Sperre: ein Band mit Status "läuft" stammt aus einem abgebrochenen Lauf (Neustart von tei).
    # Neu aufnehmen; run_qwen.py überspringt die schon sauber gelesenen Seiten.
    for y in [y for y, s in st.items() if s.get("status") == "läuft"]:
        log(f"{y}: abgebrochener Lauf, nehme den Band wieder auf")
        del st[y]
    while True:
        today = dt.datetime.now(TZ).date()
        if busy():
            log("anderer Lesedurchgang aktiv, warte"); return
        free = os.statvfs("/").f_bavail * os.statvfs("/").f_frsize / 1e9
        if free < 3:
            log(f"nur {free:.1f} GB frei auf /, warte"); return
        if YEARS:   # Vorrang-Fenster: nur diese Jahrgänge, ohne Wochenbudget, einer nach dem anderen
            nxt = next((q for q in sorted(queue, key=lambda q: int(q["year"]))
                        if q["year"] not in st and YEARS[0] <= int(q["year"]) <= YEARS[1]), None)
        else:
            used = {k: sum(1 for s in st.values() if s.get("stream") == k and s.get("week") == week(today)) for k in "AB"}
            nxt = next((q for q in queue
                        if q["year"] not in st and used[q["stream"]] < PER_WEEK
                        and (not q["not_before"] or today >= dt.date.fromisoformat(q["not_before"]))), None)
        if not nxt:
            return
        try:
            process(nxt, st)
        except Exception as e:                            # Band als Fehler markieren, nächster Tag versucht den nächsten
            st.setdefault(nxt["year"], {})["status"] = f"fehler: {type(e).__name__}"
            save_state(st); log(f"{nxt['year']}: {e!r}")


if __name__ == "__main__":
    main()
