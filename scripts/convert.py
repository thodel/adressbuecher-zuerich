"""Lesungen von qwen3.8 (data/qwen/<Jahr>/entries.csv) → Eintragsdateien im Schema von adressbuecher-aarau.

    python scripts/convert.py

Schreibt je Band data/csv/04_entries_<Band>.csv (Einwohner) und 04_berufe_<Band>.csv (Berufsregister), 03_sections.csv
(welche Seiten in welchen Teil gehen) und 10_authority_links.csv (leer: Normdaten verknüpft
«Vernetzte Schweiz» über die Einheiten, nicht dieses Repo).

Übernommen werden nur das Einwohnerverzeichnis und das Berufsregister der Stadt; Inserate (Seiten mit
weniger als zehn Einträgen), Vorspann, Behörden, Häuserverzeichnisse und Querverweise nicht.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QWEN = ROOT / "data" / "qwen"
CSV = ROOT / "data" / "csv"

FIELDS = [
    "entry_id", "volume", "page", "section", "line_from", "line_to", "entry_type", "citizen_flag",
    "dash_prefix", "surname", "surname_inherited", "alliance_name", "maiden_name", "forename", "title",
    "civil_status", "relation", "occupation_raw", "origin_raw", "origin_canton", "address_seq",
    "address_role", "street_raw", "building_no", "phone_flag", "heading", "parse_method",
    "parse_confidence", "residual", "text", "municipality", "qa_flags", "district",
]
AUTH_FIELDS = [
    "entry_id", "kind", "volume", "surname", "forename", "occupation", "origin", "qid", "label", "birth",
    "death", "hls_id", "gnd", "wd_description", "wd_occupations", "evidence", "score", "n_candidates",
    "tier", "hls_origins", "hls_head", "hls_check",
]
METHOD = "qwen3.8-27b, Bild 2x"

# ── Aufbau der Bände ─────────────────────────────────────────────────────
# Seite = Seite im PDF bzw. Bildnummer der Lesung. Geprüft an den ersten und letzten Einträgen.
# 1875 und 1885 nennen die Stadt und neun Ausgemeinden (Aussersihl, Enge, Fluntern, Hirslanden,
# Hottingen, Oberstrass, Riesbach, Unterstrass, Wiedikon); alle sind seit 1893 Teil der
# Gemeinde Zürich. 1900 und 1914 nennen die Kreise I–V. Der Stand 1914 ist also überall Zürich.
MUNICIPALITY = "Zürich"
# Wer ausserhalb der Stadt wohnt, steht mit dem Ort statt des Kreises da («… Seestrasse 12, Zollikon»).
OUTSIDE = {"Zollikon", "Kilchberg", "Küsnacht", "Rüschlikon", "Adliswil", "Höngg", "Altstetten",
           "Albisrieden", "Oerlikon", "Schwamendingen", "Seebach", "Affoltern", "Witikon", "Wallisellen",
           "Dübendorf", "Schlieren", "Zumikon", "Thalwil", "Dietikon", "Urdorf", "Oberengstringen",
           "Unterengstringen", "Weiningen", "Regensdorf", "Opfikon", "Wallisellen"}
# 1859: «… Weinhandlung. In Albisrieden.»; Lesefehler des Modells auf den Ort von 1914
PLACE_ALIAS = {"Oberurdorf": "Urdorf", "Ulstetten": "Altstetten", "Bollikon": "Zollikon", "Weinigen": "Weiningen"}
# Gebiet innerhalb der Stadt (Spalte district): 1859 Grosse/Kleine Stadt (g/k an der Hausnummer), 1867 die Ausgemeinde im Text, 1875/1885 die
# alte Gemeinde hinter der Hausnummer («Rankstrasse 77 R.»), 1900 Kreis I–V, 1914–1922 Kreis 1–8 vor der Strasse.
OLD = {"Z": "Zürich", "Zürich": "Zürich", "A": "Aussersihl", "Aussersihl": "Aussersihl", "E": "Enge", "Enge": "Enge",
       "F": "Fluntern", "Fl": "Fluntern", "Fluntern": "Fluntern", "Hi": "Hirslanden", "Hl": "Hirslanden",
       "Hirs": "Hirslanden", "Hirslanden": "Hirslanden", "Ho": "Hottingen", "Hottingen": "Hottingen",
       "O": "Oberstrass", "Oberstr": "Oberstrass", "Oberstrass": "Oberstrass", "R": "Riesbach", "Riesb": "Riesbach",
       "Riesbach": "Riesbach", "U": "Unterstrass", "Unterstr": "Unterstrass", "Unterstrass": "Unterstrass",
       "W": "Wiedikon", "Wiedikon": "Wiedikon"}
KREIS = {"1900": r"I{1,3}|IV|V", "1914": r"[1-8]", "1920": r"[1-8]", "1922": r"[1-8]", "1925": r"[1-8]", "1930": r"[1-8]"}  # Kreise 1–8 bis 1934
# 1867: die Ausgemeinde steht als Wort im Text («… 235 Enge», «In Riesbach»), mit Fraktur-Lesefehlern
# (ſ → f, ß: «Oberstraf», «Auferfchl.», «Außerfihl»).
OLD_1867 = [(re.compile(p), n) for p, n in (
    (r"\bAu[sßf]{0,2}e?r[sßf]*c?h?i?h?l\b|\bAu[sßf]+er[sßfz]+ih?l\b", "Aussersihl"), (r"\bEnge\b", "Enge"),
    (r"\bFluntern\b", "Fluntern"), (r"\bHirslanden\b", "Hirslanden"), (r"\bHottingen\b", "Hottingen"),
    (r"\bOberstra[sßf]{1,2}e?\b", "Oberstrass"), (r"\bRiesb(?:ach|\.)", "Riesbach"),
    (r"\bUnterstra[sßf]{1,2}e?\b", "Unterstrass"), (r"\bWiedikon\b", "Wiedikon"))]
IN_PLACE = re.compile(r"\bIn ([A-ZÄÖÜ][a-zäöüß]+)\b")
SECTIONS = {
    "1859": [("einwohner", 77, 263), ("berufe", 265, 394)],  # Fraktur; davor das Häuserverzeichnis
    "1867": [("einwohner", 61, 151), ("berufe", 152, 222)],  # Fraktur (Hintermeister, 2. Aufl.)
    "1875": [("einwohner", 9, 222), ("berufe", 225, 272)],
    "1885": [("einwohner", 15, 320), ("berufe", 335, 415)],
    "1900": [("einwohner", 33, 534)],  # ohne Berufsregister
    "1914": [("einwohner", 33, 652), ("berufe", 661, 854)],
    # nach dem Zeitfenster von «Vernetzte Schweiz»; Grenzen aus den Kolumnentiteln, von Hand geprüft
    "1920": [("einwohner", 31, 716), ("berufe", 717, 953)],
    "1922": [("einwohner", 23, 726), ("berufe", 727, 956)],
    "1925": [("einwohner", 33, 910), ("berufe", 911, 1132)],
    "1930": [("einwohner", 42, 1072), ("berufe", 1073, 1308)],
}
# Ab 1925 steht der Allianzname (Frauenname) in Klammern nach dem Vornamen: «Huber, Rudolf (Glanzmann), …»,
# nicht mehr am Familiennamen («Hirt-Guyer»). Das Modell legte ihn mal in origin, mal in den Vornamen, mal
# als Familiennamen ab; er wird darum aus der gedruckten Zeile genommen. «(gesch. Peter)» bleibt Zivilstand.
ALLIANCE_PAREN_FROM = 1925
ALLIANCE_PAREN = re.compile(r"^[\s—–*☎§-]*(?:[^,(]+,\s*)?[^,(]*?\(([A-ZÄÖÜ][\wäöüéèçàô'’-]+(?:[- ][A-ZÄÖÜ][\wäöüéèçàô'’-]+)?)\)")

# Zürich hat erst seit 1880 ein Telefonnetz; 1875 steht vor «Siehe Inserat» eine Hand, die das Modell
# als ☎ liest.
PHONE_FROM = 1880

# Ab 1930 steht der Kreis als eingekreiste Ziffer vor der Strasse («③ Badenerstrasse 437»). Das Modell schrieb
# sie mal als Ziffer, mal als ③, und in rund jedem neunten Eintrag als ☎. Darum: ①–⑧ zählen als Ziffer; Abonnent
# ist nur, wer ☎ (oder §) am Zeilenanfang oder «Tel.» hat; ein ☎ vor der Strasse ist ein verlesener Kreis.
# Dessen Ziffer ist verloren; der Kreis kommt dann aus der Strasse, wenn sie im selben Band in einem Kreis liegt.
CIRCLED_FROM = 1930
CIRCLED = str.maketrans("①②③④⑤⑥⑦⑧⑨", "123456789")
PHONE_LEAD = re.compile(r"^\s*(?:[—–-]\s*)?[☎§]|\bTel\.")
STREET_KREIS_MIN, STREET_KREIS_SHARE = 3, 0.9  # so oft im Band mit Kreis belegt, so einheitlich

MIN_ENTRIES = 10  # weniger Einträge auf einer Seite: Inserat oder Zwischenseite
NOT_ENTRY = re.compile(r"siehe auch|voir aussi|^\(?(?:Siehe|Voir)\b|Abkürzungen|Abréviations|"
                       r"alphabetischen Reihenfolge|Telephonzeichen|La lettre R\.", re.I)
FIRM = re.compile(r"&|\bCie\b|\bC°|\bGebr(?:\.|üder)|\bfrères\b|A\.-?G\.|\bAG\b|S\. ?A\.|Aktiengesellschaft|"
                  r"Société|Genossenschaft|Verein\b|Gesellschaft|Fabri(?:k|que)\b|Kasse\b|Caisse\b|Banque\b|"
                  r"Bank\b|Werke?\b|Erben\b|hoirie\b", re.I)
WIDOW = re.compile(r"\bWwe\.?|\bWitwe\b|\bWittwe\b|\bveuve\b", re.I)
DASH = re.compile(r"^\s*[—–-]")
LEAD = re.compile(r"^[\s*†§☎„\"'«»(]+")
# «Bankrat, siehe III. Teil.», «Bechtold, siehe Bächtold.»: Verweis ohne eigene Adresse.
SEE = re.compile(r"\bsiehe\b", re.I)
SAME = re.compile(r"^(?:m\. ?a\.?|même adresse|dito|ditto|do\.?|id\.?|ebenda|ebd\.?)$", re.I)


def section_of(volume: str, page: int) -> str:
    for name, a, b in SECTIONS[volume]:
        if a <= page <= b:
            return name
    return ""


def own_surname(r: dict) -> str:
    """Familienname; ein vom Vorgänger geerbter Name, der zum Text nicht passt, wird ersetzt."""
    sn = LEAD.sub("", r["surname"]).strip()
    text = LEAD.sub("", r["text"])
    if r["dash_prefix"] == "1" and not DASH.match(text) and sn and sn not in text:
        return re.split(r"[,(]", text)[0].strip(" .")
    return sn


def clean_street(street: str, number: str, kreis: bool = True) -> tuple[str, str]:
    """Strasse ohne Telefonzeichen, ohne Kreis und ohne doppelte Hausnummer; «Bärenplatz 29» → («Bärenplatz», «29»),
    «4 Lagerstrasse 24» (1914, Kreis 4) → («Lagerstrasse», «24»). Kreise gibt es erst seit 1893; 1875 ist
    «3 Scheunen» (Enge) ein Ortsname."""
    if kreis:
        street = re.sub(r"^(?:[1-8]|I{1,3}|IV|V)\s+(?=[A-ZÄÖÜa-zäöü])", "", street.strip())
    for _ in range(2):  # «… R T 180»: erst die Telefonnummer, dann das R.
        street = re.sub(r"\s*(?:\bH\.|☎.*|\bT\s?\d+.*|\bR\.?\s*$|\bR?\s?T\.?\s*$)", "", street).strip(" ,.")
    number = number.strip(" ,.")
    if number:
        street = re.sub(rf"[\s,]+{re.escape(number)}\s*$", "", street)
    else:
        m = re.match(r"^(.*\D)[\s,]+(\d+\s?[a-z]?)$", street)
        if m:
            street, number = m.group(1).strip(" ,"), m.group(2).replace(" ", "")
    return street, number


def kreis_from_text(volume: str, text: str, street: str) -> tuple[str, str]:
    """1900/1914: («Kreis», «Hausnummer») aus «… 4 Lagerstrasse 24.» im gedruckten Text; leer, wenn nicht zu finden."""
    if volume not in KREIS or not street:
        return "", ""
    head = rf"(?:^|[\s,.;])({KREIS[volume]})\s+{re.escape(street[:5])}"
    m = re.search(head + r"[^,;\d]*\s(\d+(?:\s?[a-z](?![\w.]))?)", text)  # mit Hausnummer («12 a», nicht «1 u.»)
    if m:
        return m.group(1), m.group(2).replace(" ", "")
    m = re.search(head, text)
    return (m.group(1), "") if m else ("", "")


def district(volume: str, r: dict, number: str, kreis: str) -> str:
    """Gebiet in der Stadt, wie gedruckt (siehe OLD, KREIS); leer, wenn nichts dasteht."""
    d = r.get("district", "").strip(" .")
    if volume == "1859":
        gk = re.sub(r"[^gk]", "", number) or re.sub(r"[^gk]", "", d if d in ("g", "k") else "")
        return {"g": "Grosse Stadt", "k": "Kleine Stadt"}.get(gk, "")
    if volume == "1867":
        for rx, name in OLD_1867:
            if rx.search(r["text"]) or rx.search(d):
                return name
        return ""
    if volume in ("1875", "1885"):
        if d in OLD:
            return OLD[d]
        text, no = r["text"], number
        i = text.rfind(no) if no else -1
        m = re.match(r"[\s.]*([A-ZÄÖÜ][a-zäöü]{0,11})\.?", text[i + len(no):]) if i >= 0 else None
        return OLD.get(m.group(1), "") if m else ""
    if volume in KREIS:
        k = kreis or (d if re.fullmatch(KREIS[volume], d) else "")
        return f"Kreis {k}" if k else ""
    return ""


def municipality(r: dict) -> str:
    """Gemeinde 1914: Zürich, ausser der Eintrag nennt einen Ort, der 1914 eine eigene Gemeinde war."""
    places = [r.get("district", "").strip(" .").removeprefix("In ")] + IN_PLACE.findall(r.get("text", ""))
    for place in places:
        place = PLACE_ALIAS.get(place, place)
        if place in OUTSIDE:
            return place
    return MUNICIPALITY


def convert(volume: str) -> tuple[list[dict], Counter]:
    rows = list(csv.DictReader(open(QWEN / volume / "entries.csv", encoding="utf-8")))
    pages = Counter(int(r["page"]) for r in rows)
    out, stats = [], Counter()
    last = ("", "")  # Adresse des vorigen Eintrags, für «m. a.» (même adresse)
    prev_surname = ""
    circled = int(volume) >= CIRCLED_FROM
    for r in rows:
        if circled:
            r = {**r, "text": r["text"].translate(CIRCLED), "district": r["district"].translate(CIRCLED)}
        page, seq = int(r["page"]), int(r["seq"])
        sec = section_of(volume, page)
        if not sec:
            stats["ausserhalb der Verzeichnisse"] += 1
            continue
        if pages[page] < MIN_ENTRIES:
            stats["Inserat- oder Zwischenseite"] += 1
            continue
        if NOT_ENTRY.search(r["text"]):
            stats["Querverweis oder Vorbemerkung"] += 1
            continue
        if SEE.search(r["text"]) and not r["street"].strip():
            stats["Querverweis oder Vorbemerkung"] += 1
            continue
        surname = own_surname(r)
        alliance, forename, origin, civil = r["alliance_name"], r["forename"], r["origin"], r["civil_status"]
        m = ALLIANCE_PAREN.match(r["text"]) if int(volume) >= ALLIANCE_PAREN_FROM else None
        if m:
            alliance = m.group(1)
            forename = re.sub(rf"\s*\({re.escape(alliance)}\)", "", forename)
            origin = "" if origin.strip("() ") == alliance else origin
            civil = "" if civil.strip("() ") == alliance else civil
            if r["dash_prefix"] == "1" and surname == alliance and prev_surname:
                surname = prev_surname  # das Modell nahm den Allianznamen als Familiennamen
                stats["Allianzname statt Familienname korrigiert"] += 1
            stats["Allianzname aus Klammer"] += 1
        prev_surname = surname or prev_surname
        if not surname or len(surname.split()) > 4:
            stats["ohne Familienname"] += 1
            continue
        street, number = clean_street(r["street"], r["building_no"], kreis=int(volume) >= 1893)
        kreis, printed_no = kreis_from_text(volume, r["text"], street)
        if kreis and number == kreis and printed_no and printed_no != kreis:
            number = printed_no  # das Modell setzte den Kreis als Hausnummer («4 Zeughausstr. 29» → 4)
            stats["Hausnummer statt Kreis korrigiert"] += 1
        if SAME.match(street):
            street, number = last
            stats["Adresse vom vorigen Eintrag"] += 1
        last = (street, number)
        flags = [f for f in r["qa_flags"].split(";") if f]
        if circled:
            phone = bool(PHONE_LEAD.search(r["text"]))
            if street and re.search(r"(?<=.)☎\s*" + re.escape(street[:5]), r["text"]):
                flags.append("kreis_als_telefon")
                stats["Kreis als ☎ gelesen"] += 1
        else:
            phone = int(volume[:4]) >= PHONE_FROM and bool(r["phone"].strip() or "☎" in r["text"] or r["text"].lstrip().startswith("§"))
        firm = bool(FIRM.search(f"{surname} {r['forename']} {r['text'][:60]}")) and not WIDOW.search(r["text"])
        out.append({
            "entry_id": f"{volume}-{sec}-{page:03d}-{seq:03d}", "volume": volume, "page": page,
            "section": sec, "line_from": seq, "line_to": seq,
            "entry_type": "firma" if firm else "person", "citizen_flag": "",
            "dash_prefix": r["dash_prefix"], "surname": surname,
            "surname_inherited": "1" if r["dash_prefix"] == "1" and DASH.match(r["text"]) else "",
            "alliance_name": alliance, "maiden_name": "", "forename": forename.strip(" .,"),
            "title": r["title"], "civil_status": civil, "relation": "",
            "occupation_raw": r["occupation"], "origin_raw": origin, "origin_canton": "",
            "address_seq": "1", "address_role": "", "street_raw": street, "building_no": number,
            "phone_flag": "1" if phone else "", "heading": r["heading"],
            "parse_method": METHOD,
            "parse_confidence": "medium" if {"street_rare", "hyphen", "unreadable", "surname_split"} & set(flags)
            else "high",
            "residual": "", "text": r["text"], "municipality": municipality(r), "qa_flags": ";".join(flags),
            "district": district(volume, r, number, kreis) if municipality(r) == MUNICIPALITY else "",
        })
        stats[sec] += 1
    if circled:
        street_kreis(out, stats)
    return out, stats


def street_kreis(out: list[dict], stats: Counter) -> None:
    """Kreis aus der Strasse, wo er unlesbar war: nur, wenn die Strasse im Band einheitlich in einem Kreis liegt."""
    seen: dict[str, Counter] = {}
    for r in out:
        if r["district"] and r["street_raw"]:
            seen.setdefault(r["street_raw"], Counter())[r["district"]] += 1
    for r in out:
        if r["district"] or not r["street_raw"] or r["municipality"] != MUNICIPALITY:
            continue
        c = seen.get(r["street_raw"])
        if not c:
            continue
        top, k = c.most_common(1)[0]
        if k >= STREET_KREIS_MIN and k / sum(c.values()) >= STREET_KREIS_SHARE:
            r["district"] = top
            r["qa_flags"] = ";".join(f for f in (r["qa_flags"], "kreis_aus_strasse") if f)
            stats["Kreis aus der Strasse"] += 1


def main() -> None:
    entries, berufe, sections = [], [], []
    for volume in SECTIONS:
        rows, stats = convert(volume)
        entries += [r for r in rows if r["section"] == "einwohner"]
        berufe += [r for r in rows if r["section"] == "berufe"]
        sections += [{"volume": volume, "section": n, "page_from": a, "page_to": b} for n, a, b in SECTIONS[volume]]
        print(volume, dict(sorted(stats.items())))
    CSV.mkdir(parents=True, exist_ok=True)
    # je Band eine Datei: zusammen wären es über 100 MB, die Grenze von GitHub; 80–82 lesen alle 04_*.csv
    for old in (*CSV.glob("04_entries*.csv"), *CSV.glob("04_berufe*.csv")):
        old.unlink()
    files = [(f"04_entries_{v}.csv", [r for r in entries if r["volume"] == v], FIELDS) for v in SECTIONS]
    files += [(f"04_berufe_{v}.csv", [r for r in berufe if r["volume"] == v], FIELDS) for v in SECTIONS
              if any(n == "berufe" for n, *_ in SECTIONS[v])]
    for name, rows, fields in (*files,
                               ("03_sections.csv", sections, ["volume", "section", "page_from", "page_to"]),
                               ("10_authority_links.csv", [], AUTH_FIELDS)):
        with open(CSV / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
