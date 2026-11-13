# Adressbücher Zürich 1859–1914

Einträge der Adressbücher der Stadt Zürich, maschinell gelesen. Quelle für
[Vernetzte Schweiz 1860–1914](https://thodel.github.io/vernetzte-schweiz/), wo sie mit den
Telefonbüchern und den anderen Adressbüchern verknüpft werden.

| Band | Seiten | Einwohner | Berufsregister | Teile (Seiten im PDF) |
|---|---:|---:|---:|---|
| 1859, D. Hintermeister (Fraktur) | 454 | 4 506 | 3 652 | Einwohner 77–263, Berufe 265–394 |
| 1875, Orell Füssli | 418 | 15 507 | 4 237 | Einwohner 9–222, Berufe 225–272 |
| 1885, Orell Füssli | 574 | 27 347 | 7 411 | Einwohner 15–320, Berufe 335–415 |
| 1900 | 768 | 60 671 | – | Einwohner 33–534 (kein Berufsregister im Band) |
| 1914 | 1 377 | 64 390 | 17 347 | Einwohner 33–652, Berufe 661–854 |

«Vernetzte Schweiz» übernimmt die Bände von 1875 an; 1859 liegt vor ihrem Zeitfenster (1860–1914).

## Dateien

Schema wie [adressbuecher-aarau](https://github.com/thodel/adressbuecher-aarau), dazu die
Spalten `municipality` (Gemeinde zum Stand 1914) und `qa_flags`.

- `data/csv/04_entries.csv`: Einwohnerverzeichnisse.
- `data/csv/04_berufe.csv`: Berufsregister; der Beruf steht in `heading`.
- `data/csv/03_sections.csv`: welche Seiten in welchen Teil gehen.
- `data/csv/00_volumes.csv`: die Bände mit Prüfsumme des PDFs.
- `data/csv/10_authority_links.csv`: leer. Normdaten (Wikidata, HLS, GND) verknüpft «Vernetzte
  Schweiz» über die Personen, nicht dieses Repo.
- `data/qwen/<Jahr>/`: die Lesung, wie sie vom Modell kam (`entries.csv`, je Seite `pages.csv`).

`python3 scripts/convert.py` erzeugt `data/csv/` aus `data/qwen/`; `python3 -m unittest discover -s tests`
prüft Strasse, Hausnummer und Familienname.

## Wie gelesen

- **Modell:** `qwen3.8-27b` auf GPUStack der Universität Bern, Seitenbild 2× vergrössert,
  Ausgabe als JSON-Zeilen (Familienname, Allianzname, Vorname, Beruf, Strasse, Hausnummer, Kreis
  bzw. Gemeinde, Telefon). Seiten, deren Ausgabe abbrach, wurden ein zweites Mal gelesen.
- Keine Nachkorrektur und noch keine Stichprobe von Hand. `qa_flags` markiert Verdachtsfälle
  (seltene Strasse, Trennstrich, zusammengesetzter Name); solche Einträge haben
  `parse_confidence = medium`.

## Gemeinden

- **1859, 1875 und 1885** nennen die Stadt und die Ausgemeinden (1875: Aussersihl, Enge, Fluntern,
  Hirslanden, Hottingen, Oberstrass, Riesbach, Unterstrass, Wiedikon). Sie sind seit der
  Eingemeindung 1893 Teil der Stadt; `municipality` ist darum überall «Zürich». Die alte Gemeinde
  steht im Text des Eintrags («… Rankstrasse 77 R.»), die Hausnummern sind die der alten Gemeinde.
- **1900 und 1914** nennen den Stadtkreis vor der Strasse (1900: I–V, 1914: 1–8); `street_raw` steht ohne ihn.
- **Ausserhalb der Stadt:** Wer 1914 in einer anderen Gemeinde wohnte («… In Albisrieden.» 1859,
  «…, Zollikon» 1914), bekommt diese Gemeinde (`OUTSIDE` in `scripts/convert.py`). 1859 trifft das 28
  Einwohner, 1914 36.

## Lücken

- **1914:** 11 Seiten des Einwohnerverzeichnisses (S. 62, 70, 97, 120, 353, 374, 397, 413, 477, 532, 587)
  brechen in der Lesung vor dem Seitenende ab, auch im zweiten Versuch mit doppeltem Tokenbudget an derselben
  Stelle; es fehlen dort die letzten Einträge der Seite.
- **1859:** Fraktur; die Lesung ist nicht geprüft. Hausnummern sind die alten Nummern mit «g» (Grosse
  Stadt) und «k» (Kleine Stadt).
- Zeilen ohne bestimmbaren Familiennamen fehlen: lange Firmennamen (mehr als vier Wörter vor dem ersten
  Komma), Inseratverweise, Bruchstücke (1914: 887 Zeilen, meist Genossenschaften und Ämter).

## Nicht übernommen

Inserate, Vorspann, Behörden-, Vereins- und Tarifteile, Strassen- und Häuserverzeichnisse, das alphabetische
Warenverzeichnis und Querverweise («Bankrat, siehe III. Teil.», «Bechtold, siehe Bächtold.»).
1875 steht vor «Siehe Inserat» eine Hand, die das Modell als ☎ liest; Zürich hat erst seit 1880
ein Telefonnetz, `phone_flag` bleibt darum vor 1880 leer.

## Seite

<https://thodel.github.io/adressbuecher-zuerich/>: alle Einträge durchsuchbar, mit Filtern nach Band, Gebiet
(Kreis bzw. alte Gemeinde), Strasse, Konfidenz, Hinweis und Telefon, Flagging je Zeile wie bei Aarau, Basel,
Baden und Bern. Seitenbilder zeigt und verlinkt die Seite nicht (Herkunft der Scans offen).

- `python scripts/90_seite.py --out _site` baut sie lokal (`index.html` und je Band und Teil
  `data/<Band>-<Teil>.json`, die die Seite erst bei Bedarf lädt); GitHub Actions (`.github/workflows/pages.yml`)
  baut und veröffentlicht sie bei jedem Push.
- Karte: `python scripts/92_karte.py --out _site/karte.html` (Kreise je Strasse).
- `scripts/10_geo.py`: das Gebiet je Eintrag (1859 Grosse/Kleine Stadt, 1875/1885 alte Gemeinde, 1900/1914
  Kreis) und die Strassenpunkte aus OpenStreetMap, nur wenn sie im Quartier des Gebiets liegen
  (`web/geo/streets.csv`); offene Strassen von Hand in `web/geo/streets_manual.csv` (`10_geo.py todo`).
  Hausnummern werden nicht verortet.
- `scripts/80_telefon.py --vs <vernetzte-schweiz> --commit <sha>`: Einträge mit ☎ → PTT-Telefonbuch
  (`web/telefon.csv`, Commit in `telefon_source.txt`).
- `scripts/81_baende.py`: dieselbe Person in den anderen Bänden (`web/baende.csv`).
- `scripts/82_normdaten.py --vs …`: ungeprüfte Kandidaten aus HLS und Wikidata (`web/normdaten.csv`).
- `scripts/91_merge_flags.py <flags.csv>`: Flags aus der Seite nach `data/review/flags.csv`.

## Lizenz

Die Bücher sind vor 1914 erschienen; ihr Inhalt ist gemeinfrei (URG Art. 2 Abs. 1, Art. 29 Abs. 2).
Die Daten in `data/` stehen unter [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/),
der Code unter MIT. Die Scans selbst liegen nicht in diesem Repo.
