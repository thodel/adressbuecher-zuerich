# Wochenlauf: die fehlenden Zürcher Bände

Ab 16.11.2026 liest ein Wochenlauf die Adressbücher, die in diesem Repo noch fehlen, und
bringt sie hierher und, bis 1913, nach [Vernetzte Schweiz](https://thodel.github.io/vernetzte-schweiz/).

| Strom | Bände | Beginn | je Woche |
|---|---|---|---|
| A | 1901–1913, dann 1915–1944 (ohne 1920, 1922, 1925; 1930, 1935, 1940, 1945 laufen in `run_zh2.sh`) | sofort | 10 |
| B | 1899 bis 1877 (absteigend; 1885 liegt vor) | 15.12.2026 | 10 |

Zusammen 59 Bände (`queue.csv`): Strom A in etwa vier Wochen, Strom B in drei. Quelle ist die
Zentralbibliothek Zürich (Zurich Open Platform, CC0); `zop_liste.csv` ist ihre Liste mit
PDF und Handle, `make_queue.py` löst die Handles in die IIIF-Manifeste auf.

## Ablauf

**1. Lesen auf tei** (`zh_weekly.py`, `zh_classify.py`; Kopie in `tei:/home/dh/adressbuch_qwen/weekly/`).
- Der cron startet `zh_weekly.py` täglich um 01:15 (`crontab.txt`). Je Kalenderwoche nimmt der
  Lauf je Strom höchstens 10 Bände.
- Er wartet, solange ein anderer Lesedurchgang läuft, und hält an, wenn auf `/` weniger als 3 GB
  frei sind.
- Je Band:
  1. Manifest der ZB holen, Seitentabelle schreiben (`weekly/<Jahr>/iiif_pages.csv`).
  2. Jede Seite zuordnen: ein Bild mit 600 px Breite, qwen3.8 nennt den Teil (Einwohner,
     Berufe, Häuser, Strassen, Behörden, Inserate, anderes). Der grösste zusammenhängende Block
     ergibt die Seitenbereiche Einwohner und Berufe. Die Schrift, die qwen nennt, ist nur ein
     Hinweis: An 1901 (Antiqua) sagte es «fraktur».
  3. Die Seiten der beiden Teile über IIIF holen (halbe Breite des Scans, etwa 150 dpi) und mit
     `run_qwen.py` lesen (2× vergrössert, zwei Durchgänge), wie die übrigen Bände.
     `collect.py` sammelt die Einträge.
  4. Ergebnis auf den Forschungsspeicher (`/mnt/wbkolleg_dh_1/tei/adressbuch_qwen/full/zurich<Jahr>/`),
     Seitenbilder löschen. Es werden keine PDFs geladen: Die Bilder kommen Seite für Seite über
     IIIF und sind jederzeit wieder holbar.
- Den Stand zeigt `python3 zh_weekly.py --status` (`state.json`, Protokoll `weekly.log`).

**2. Übernahme auf dem Mac** (geplanter Claude-Auftrag «Zürich: gelesene Bände übernehmen»,
täglich 07:30, Anleitung in [TASK.md](TASK.md)). Je gelesenen Band:
1. Ergebnis von tei holen.
2. Am Seitenbild prüfen, ob der Band Fraktur ist; dann mit Gemini neu lesen.
3. `convert.py` um Seitenbereiche und Kreis-Muster ergänzen, umwandeln, testen, Stichprobe von
   20 Einträgen gegen das Seitenbild.
4. Seite, Karte und IIIF-Tabellen aktualisieren, committen, im sauberen Klon prüfen, pushen.
5. Bis 1913 dazu in Vernetzte Schweiz: Pin heben, einlesen, verknüpfen (Einheiten,
   Normdaten, HLS, Elites suisses), Wanderungen neu rechnen, pushen, Deploy prüfen.

Die Seitenbilder verlinkt die Seite über IIIF direkt bei der ZB, wie für die übrigen Bände.

## Grenzen

- Ab 1915 kommen die Bände nur in dieses Repo. Vernetzte Schweiz bleibt bei 1860–1914.
- Die Seitenbereiche sind maschinell bestimmt. Der Auftrag auf dem Mac prüft sie an den Rändern,
  bevor er umwandelt.
- Liest der GPU-Dienst langsamer (VPN, Last), verschiebt sich der Plan. Das Wochenbudget zählt
  begonnene Bände, nicht fertige.
