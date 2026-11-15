# Adressbücher Zürich 1859–1922

Einträge der Adressbücher der Stadt Zürich, maschinell gelesen. Quelle für
[Vernetzte Schweiz 1860–1914](https://thodel.github.io/vernetzte-schweiz/), wo sie mit den
Telefonbüchern und den anderen Adressbüchern verknüpft werden.

| Band | Seiten | Einwohner | Berufsregister | Teile (Seiten im PDF) |
|---|---:|---:|---:|---|
| 1859, D. Hintermeister (Fraktur) | 454 | 4 506 | 3 652 | Einwohner 77–263, Berufe 265–394 |
| 1867, D. Hintermeister, 2. Aufl. (Fraktur) | 232 | 5 981 | 6 730 | Einwohner 61–151, Berufe 152–222 |
| 1875, Orell Füssli | 418 | 15 507 | 4 237 | Einwohner 9–222, Berufe 225–272 |
| 1885, Orell Füssli | 574 | 27 347 | 7 411 | Einwohner 15–320, Berufe 335–415 |
| 1900 | 768 | 60 671 | – | Einwohner 33–534 (kein Berufsregister im Band) |
| 1914 | 1 377 | 64 390 | 17 347 | Einwohner 33–652, Berufe 661–854 |
| 1920 | 1 482 | 69 064 | 19 157 | Einwohner 31–716, Berufe 717–953 |
| 1922 | 1 480 | 69 674 | 18 606 | Einwohner 23–726, Berufe 727–956 |

«Vernetzte Schweiz» übernimmt die Bände 1867–1914; 1859, 1920 und 1922 liegen ausserhalb ihres Zeitfensters (1860–1914).
1920 und 1922 sind die ersten Bände nach 1914; 1925–1945 werden gelesen und kommen nach.

## Dateien

Schema wie [adressbuecher-aarau](https://github.com/thodel/adressbuecher-aarau), dazu die
Spalten `municipality` (Gemeinde zum Stand 1914), `qa_flags` und `district` (Gebiet in der Stadt, wie gedruckt):

| Band | `district` | Beispiel |
|---|---|---|
| 1859 | Grosse Stadt / Kleine Stadt (g bzw. k an der Hausnummer) | «339 g, gr. Brunngasse» → Grosse Stadt |
| 1867 | Ausgemeinde als Wort im Text (Stadt selbst: leer) | «629 Hornaugasse, Riesbach» → Riesbach |
| 1875, 1885 | alte Gemeinde hinter der Hausnummer | «Rankstrasse 77 R.» → Riesbach |
| 1900 | Kreis I–V vor der Strasse | «III Freischützgasse 1» → Kreis III |
| 1914, 1920, 1922 | Kreis 1–8 vor der Strasse | «6 Habsburgstrasse 26» → Kreis 6 |

Leer, wenn nichts dasteht oder der Eintrag ausserhalb der Stadt liegt (dann steht die Gemeinde in `municipality`).

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
- **1867:** dasselbe Modell, auf tei; Seitenbilder 1600 px breit von der ZB (IIIF), ohne Vergrösserung.
  Alle 162 Seiten endeten sauber.
- **1920, 1922:** dasselbe Modell, gelesen auf tei.dh.unibe.ch; die Seitenbilder kamen direkt von der ZB (IIIF, rund
  860 px breit, also 150 dpi), dann 2× vergrössert wie die anderen Bände.
- Keine Nachkorrektur und noch keine Stichprobe von Hand. `qa_flags` markiert Verdachtsfälle
  (seltene Strasse, Trennstrich, zusammengesetzter Name); solche Einträge haben
  `parse_confidence = medium`.

## Gemeinden

- **1859, 1867, 1875 und 1885** nennen die Stadt und die Ausgemeinden (1875: Aussersihl, Enge, Fluntern,
  Hirslanden, Hottingen, Oberstrass, Riesbach, Unterstrass, Wiedikon). Sie sind seit der
  Eingemeindung 1893 Teil der Stadt; `municipality` ist darum überall «Zürich». Die alte Gemeinde
  steht im Text des Eintrags («… Rankstrasse 77 R.»), die Hausnummern sind die der alten Gemeinde.
- **1900, 1914, 1920 und 1922** nennen den Stadtkreis vor der Strasse (1900: I–V, sonst 1–8); `street_raw` steht ohne ihn,
  `district` mit ihm. 1914 setzte das Modell oft den Kreis als Hausnummer («4 Zeughausstr. 29» → 4); `convert.py`
  nimmt dann die Nummer aus der gedruckten Zeile (12 015 Einträge).
- **Ausserhalb der Stadt:** Wer 1914 in einer anderen Gemeinde wohnte («… In Albisrieden.» 1859,
  «…, Zollikon» 1914), bekommt diese Gemeinde (`OUTSIDE` in `scripts/convert.py`). 1859 trifft das 28
  Einwohner, 1914 36.

## Lücken

- **1914:** 11 Seiten des Einwohnerverzeichnisses (S. 62, 70, 97, 120, 353, 374, 397, 413, 477, 532, 587)
  brechen in der Lesung vor dem Seitenende ab, auch im zweiten Versuch mit doppeltem Tokenbudget an derselben
  Stelle; es fehlen dort die letzten Einträge der Seite.
- **1920:** ebenso 8 Seiten (S. 316, 711, 715, 720, 797, 870, 877, 885); **1922:** 15 Seiten (S. 45, 117, 193,
  391, 460, 473, 517, 639, 719, 801, 843, 849, 913, 935, 941).
- **1867:** Fraktur wie 1859; typische Lesefehler «R» für «N» und «f» für «ſ» («Riederdorfstrasse»,
  «Oberstraf», «Auferfchl.» für Aussersihl).
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
Baden und Bern. Ein Klick auf die Seite zeigt das Seitenbild (siehe unten).

- `python scripts/90_seite.py --out _site` baut sie lokal (`index.html` und je Band und Teil
  `data/<Band>-<Teil>.json`, die die Seite erst bei Bedarf lädt); GitHub Actions (`.github/workflows/pages.yml`)
  baut und veröffentlicht sie bei jedem Push.
- Karte: `python scripts/92_karte.py --out _site/karte.html` (Kreise je Strasse).
- `scripts/10_geo.py`: das Gebiet je Eintrag (1859 Grosse/Kleine Stadt, 1867–1885 alte Gemeinde, 1900–1922
  Kreis) und die Strassenpunkte aus OpenStreetMap, nur wenn sie im Quartier des Gebiets liegen
  (`web/geo/streets.csv`); offene Strassen von Hand in `web/geo/streets_manual.csv` (`10_geo.py todo`).
  Hausnummern werden nicht verortet.
- `scripts/80_telefon.py --vs <vernetzte-schweiz> --commit <sha>`: Einträge mit ☎ → PTT-Telefonbuch
  (`web/telefon.csv`, Commit in `telefon_source.txt`).
- `scripts/81_baende.py`: dieselbe Person in den anderen Bänden (`web/baende.csv`).
- `scripts/82_normdaten.py --vs …`: ungeprüfte Kandidaten aus HLS und Wikidata (`web/normdaten.csv`).
- `scripts/91_merge_flags.py <flags.csv>`: Flags aus der Seite nach `data/review/flags.csv`.

## Seitenbilder

Die PDFs sind die der Zentralbibliothek Zürich ([Zurich Open Platform](https://zop.zb.uzh.ch/collections/9e5087c3-e5f8-4b76-a106-3b5fc830a0f7),
Adressbücher 1859–1974, dort unter CC0); der Dateiname 9900… ist die Katalognummer. Die Seite lädt die Bilder über
IIIF direkt von der ZB.

- `data/csv/01_iiif_volumes.csv`: je Band ZOP-UUID, Handle, DOI, Katalognummer, IIIF-Manifest, Lizenz, Zahl der Bilder.
- `data/csv/01_iiif_pages.csv`: je Seite Canvas und IIIF-Bilddienst. Seite = Seite im PDF = Canvas in derselben Folge;
  die Zahl der Bilder stimmt bei allen Bänden mit dem PDF überein, und je Band glichen fünf Stichproben (Vorschaubild
  gegen gerenderte PDF-Seite und ihre Nachbarn) nur der gleichen Seite.
- Die Tabellen decken auch die nächsten Bände ab (1867, 1920, 1922, 1925, 1930, 1935, 1940, 1945).

## Lizenz

Die Bücher bis 1914 sind gemeinfrei (URG Art. 2 Abs. 1, Art. 29 Abs. 2). Die Scans aller Bände, auch 1920 und
1922, gibt die Zentralbibliothek Zürich unter CC0 frei.
Die Daten in `data/` stehen unter [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/),
der Code unter MIT. Die Scans selbst liegen nicht in diesem Repo.
