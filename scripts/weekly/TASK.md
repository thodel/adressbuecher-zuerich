# Auftrag: gelesene Zürcher Bände übernehmen

Dieser Text ist die Anleitung für den geplanten Claude-Auftrag (täglich 07:30 MEZ). Er setzt
den Wochenlauf fort, den `README.md` beschreibt. Zeiten in MEZ. Nie einen Schlüssel ausgeben.

## Regeln

- Committen nur mit Pfad, nie `git add -A`. Vor jedem Push den Stand in einem sauberen Klon
  prüfen (Tests, Skripte importierbar).
- `data/csv/*` nur über `scripts/convert.py` ändern, `data/qwen/<Jahr>/` nur mit dem Ergebnis von tei.
- Keine Seitenbilder und keine PDFs ins Repo oder auf die Seite; die Seite verlinkt IIIF der ZB.
- Wenn etwas nicht stimmt (Seitenbereiche falsch, Stichprobe unter 80 % voll korrekt, Tests rot,
  Fraktur ohne Gemini-Schlüssel), diesen Band nicht übernehmen: im Bericht melden und weiter.

## Schritte

1. **Stand holen.** `ssh dh@tei.dh.unibe.ch 'python3 /home/dh/adressbuch_qwen/weekly/zh_weekly.py --status'`.
   Zu übernehmen sind Bände mit Status `gelesen`, die nicht in `scripts/weekly/ingested.csv` stehen.
   Bände mit `fehler: …` melden. Gibt es nichts zu tun, kurz berichten und enden.
2. **Je Band** (älteste Jahre zuerst innerhalb des Stroms):
   1. Holen: `rsync -rt dh@tei.dh.unibe.ch:/mnt/wbkolleg_dh_1/tei/adressbuch_qwen/full/zurich<Jahr>/{entries.csv,pages.csv} data/qwen/<Jahr>/`
      und `…/weekly/<Jahr>/{iiif_pages.csv,classify.csv}` nach `/tmp`.
   2. **Fraktur?** Eine Seite aus der Mitte des Einwohnerteils über IIIF ansehen
      (`<iiif_image>/full/900,/0/default.jpg`). Ist sie Fraktur, mit Gemini neu lesen (Schlüssel
      aus der Umgebung, wie in bern-adressbuecher) und dann weiter mit 3.
   3. **Seitenbereiche** aus `zh_weekly.py --status` an den Rändern prüfen: je erste und letzte
      Seite von Einwohnern und Berufen ansehen; nötigenfalls korrigieren.
   4. **convert.py:** `SECTIONS[<Jahr>]`, `KREIS[<Jahr>]` ergänzen. Das Muster für den Kreis an
      Beispielzeilen bestimmen:
      - bis 1892: alte Gemeinde hinter der Hausnummer, wie 1875/1885;
      - 1893–1913: Kreis I–V als römische Zahl vor der Strasse, wie 1900;
      - ab 1913/1914: Kreis 1–8, ab 1934 mehr Kreise.
      Ab 1925 steht der Allianzname in Klammern (`ALLIANCE_PAREN_FROM`). `python3 scripts/convert.py`,
      `python3 -m unittest discover -s tests`.
   5. **Stichprobe:** 20 zufällige Einträge (Seed = Jahr) gegen das Seitenbild prüfen. Voll korrekt
      heisst: alle Felder. In `data/review/weekly_<Jahr>.csv` festhalten. Unter 80 %: nicht übernehmen.
   6. **Tabellen und Seite:**
      - `data/csv/01_iiif_volumes.csv` und `01_iiif_pages.csv` um den Band ergänzen (aus `queue.csv`
        und `iiif_pages.csv`; Lizenz CC0);
      - `00_volumes.csv` um den Band ergänzen (ohne PDF-Prüfsumme, Quelle IIIF);
      - README-Tabelle ergänzen;
      - dann die Skripte wie bei 1925: `10_geo.py`, `80_telefon.py`, `81_baende.py`,
        `82_normdaten.py`, `90_seite.py`, `92_karte.py`.
   7. Commit `Zürich <Jahr> (…): Einwohner n, Berufsregister m` mit Pfaden, sauberer Klon, Push.
   8. In `scripts/weekly/ingested.csv` eintragen (Jahr, Datum, Commit, Einträge, Stichprobe).
3. **Vernetzte Schweiz** (nur wenn ein Band bis 1913 neu ist; einmal je Lauf, nach allen Bänden):
   1. In `config/sources.toml` beim Eintrag `zuerich` den Commit heben. Die Dateien je Band
      aufführen: `data/csv/04_entries_<Jahr>.csv` (Einwohner) und `04_berufe_<Jahr>.csv` (Berufe),
      nur Bände 1860–1914.
   2. `make ingest link entities`; dann `python3 scripts/hls_coverage.py`, `scripts/elites_match.py`,
      `python3 scripts/check_migration.py --update`. Zahlen in PLAN.md, README und docs nachführen.
   3. `python3 -m unittest discover -s tests`, Commit mit Pfaden, sauberer Klon, Push.
   4. Auf den Pages-Deploy warten und die Live-Seite prüfen: Suche in Zürich im neuen Jahr,
      eine Einheit, Wanderungen.
4. **Bericht** (kurz, deutsch, MEZ): übernommene Bände mit Einträgen und Stichprobe, Commits,
   was offen ist (Fehler, Fraktur, nächste Bände auf tei). Denselben Text in
   `~/Library/Application Support/Claude/side-session-notes/local_05d0e445-92c3-423f-94b6-d1c32b9eaa4c/zuerich_weekly_status.md`
   oben anfügen.
