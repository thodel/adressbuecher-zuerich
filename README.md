# Adressbücher Zürich 1859–1945

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
| 1901 | 1 084 | 62 835 | 11 952 | Einwohner 33–570, Berufe 577–689 |
| 1902 | 1 062 | 55 419 | 12 510 | Einwohner 33–528, Berufe 537–653 |
| 1903 | 748 | 48 434 | – | Einwohner 33–457 (kein Berufsregister im Band) |
| 1904 | 1 028 | 47 210 | 13 454 | Einwohner 33–469, Berufe 479–605 |
| 1907 | 1 154 | 51 718 | 14 672 | Einwohner 37–526, Berufe 535–680 |
| 1909 | 1 237 | 54 173 | 15 607 | Einwohner 37–562, Berufe 573–726 |
| 1910 | 1 308 | 58 340 | 16 026 | Einwohner 37–602, Berufe 613–773 |
| 1914 | 1 377 | 64 390 | 17 347 | Einwohner 33–652, Berufe 661–854 |
| 1920 | 1 482 | 69 068 | 19 157 | Einwohner 31–716, Berufe 717–953 |
| 1922 | 1 480 | 69 675 | 18 606 | Einwohner 23–726, Berufe 727–956 |
| 1925 | 1 698 | 84 186 | 17 436 | Einwohner 33–910, Berufe 911–1132 |
| 1930 | 1 964 | 93 341 | 18 903 | Einwohner 42–1072, Berufe 1073–1308 |
| 1935 | 2 000 | 137 840 | 21 889 | Einwohner 35–1190, Berufe 1191–1444 |
| 1940 | 2 184 | 156 715 | 20 010 | Einwohner 30–1313, Berufe 1319–1532 |
| 1945 | 2 290 | 167 766 | 20 198 | Einwohner 29–1395, Berufe 1399–1623 |

«Vernetzte Schweiz» übernimmt die Bände 1867–1914 (1901–1903 seit dem Wochenlauf, `scripts/weekly/`); 1859 und 1920–1945 liegen ausserhalb ihres Zeitfensters (1860–1914).

## Dateien

Schema wie [adressbuecher-aarau](https://github.com/thodel/adressbuecher-aarau), dazu die
Spalten `municipality` (Gemeinde zum Stand 1914), `qa_flags` und `district` (Gebiet in der Stadt, wie gedruckt):

| Band | `district` | Beispiel |
|---|---|---|
| 1859 | Grosse Stadt / Kleine Stadt (g bzw. k an der Hausnummer) | «339 g, gr. Brunngasse» → Grosse Stadt |
| 1867 | Ausgemeinde als Wort im Text (Stadt selbst: leer) | «629 Hornaugasse, Riesbach» → Riesbach |
| 1875, 1885 | alte Gemeinde hinter der Hausnummer | «Rankstrasse 77 R.» → Riesbach |
| 1900–1910 | Kreis I–V vor der Strasse | «III Freischützgasse 1» → Kreis III |
| 1914–1930 | Kreis 1–8 vor der Strasse | «6 Habsburgstrasse 26» → Kreis 6 |
| 1935–1945 | Kreis 1–11 vor der Strasse (Eingemeindung 1934) | «⑪ Schaffhauserstr. 410» → Kreis 11 |

Leer, wenn nichts dasteht oder der Eintrag ausserhalb der Stadt liegt (dann steht die Gemeinde in `municipality`).

- `data/csv/04_entries_<Band>.csv`: Einwohnerverzeichnisse, je Band eine Datei (zusammen wären es über die
  100 MB, die GitHub je Datei erlaubt).
- `data/csv/04_berufe_<Band>.csv`: Berufsregister; der Beruf steht in `heading`.
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
- **1925:** der Allianzname steht in Klammern nach dem Vornamen («Huber, Rudolf (Glanzmann)»), nicht mehr am
  Familiennamen; `convert.py` nimmt ihn aus der gedruckten Zeile (50 679 Einträge), weil das Modell ihn uneinheitlich
  ablegte (meist als Herkunft, 295-mal als Familiennamen). «(gesch. Peter)» bleibt Zivilstand.
- **1930:** der Kreis steht als eingekreiste Ziffer vor der Strasse («③ Badenerstrasse 437»). Das Modell schrieb sie
  mal als Ziffer, mal als ③ und in 10 122 Einträgen als ☎. `convert.py` liest ①–⑧ als Ziffer und zählt nur ☎ am
  Zeilenanfang (oder «Tel.») als Telefon. Wo die Ziffer verloren ist, kommt der Kreis aus der Strasse, wenn sie im
  Band mindestens dreimal und zu 90 % in einem Kreis steht (6 416 Einträge, Flag `kreis_aus_strasse`).
- **1935:** erster Band nach der Eingemeindung von 1934: Kreise 1–11 (9 Altstetten und Albisrieden, 10 Höngg und
  Wipkingen, 11 Affoltern, Oerlikon, Seebach und Schwamendingen; Witikon kam zu Kreis 7). ⑩ und ⑪ werden zu «10»
  und «11». Wieder las das Modell den Kreis oft als ☎ (16 268 Einträge); 1 433 bekommen ihn aus der Strasse, 355 in der Stadt
  bleiben ohne Kreis (meist lange Strassen über mehrere Kreise). `municipality` ist «Zürich» auch in den Kreisen
  9–11, obwohl diese Gemeinden 1914 noch selbständig waren: aus dem Kreis allein lässt sich die alte Gemeinde nicht
  bestimmen.
- **1940:** wie 1935 (Kreise 1–11 als eingekreiste Ziffer, Telefon als Zeichen am Zeilenanfang). Der Kreis als ☎
  gelesen in 23 549 Einträgen; 2 386 bekommen ihn aus der Strasse, 570 Einwohner in der Stadt bleiben ohne Kreis.
  Zwischen den Teilen liegen Inserate und das Titelblatt des Branchenregisters (S. 1314–1318); S. 28 ist ein
  Inserat («La Suisse»), S. 29 sind die Erläuterungen, ab S. 1535 folgt das Häuserverzeichnis. Gelesen wurden
  S. 28–1536; übernommen sind nur die beiden Teile.
- **1945:** wie 1940. Der Kreis als ☎ gelesen in 37 100 Einträgen; 7 618 bekommen ihn aus der Strasse, 740
  Einwohner in der Stadt bleiben ohne Kreis. Das Telefonzeichen am Zeilenanfang verschluckt oft den Strich der
  Fortsetzungszeile («☎ Jakob (Lüscher), …» unter «Wild»); `convert.py` behält dann den geerbten Familiennamen,
  wenn das erste Wort der Zeile der gelesene Vorname ist. Vorher stand in 2 405 Einträgen der Vorname als
  Familienname, jetzt in 315; dieselbe Regel berichtigt auch ältere Bände (am meisten 1925 und 1930).
  Trägt die Lesung einen Firmenkopf als Familiennamen durch die Fortsetzungszeilen («Hauser, E.» auf S. 494, 55 Zeilen),
  nimmt `convert.py` das Wort vor dem Komma («Hauser»); das trifft auch 1900 und 1922 («Burkhard, Burkhardt u. Burkhart.»,
  102 und 85 Zeilen). Fortsetzungszeilen unter «A. & Cie.» ohne Namen davor bleiben falsch (1945: 391 Zeilen).
  S. 26 ist ein Inserat («La Suisse»), S. 27 sind die Erläuterungen, S. 28 eine Statistik (älteste Stadtbürger);
  S. 1396–1398 Inserate und Erläuterungen zum Branchenregister, ab S. 1624 Inserate und das Strassenverzeichnis.
- **1901:** wie 1900 (Kreis I–V vor der Strasse, Telefon als Zeichen am Zeilenanfang), dazu das Berufsregister
  (II. Abteilung). Gelesen auf tei im Wochenlauf (`scripts/weekly/`), Seiten über IIIF der ZB. S. 570 endet mit
  einem «Avis» der Redaktion, S. 571–576 sind Inserate und das Titelblatt der II. Abteilung; unter der Fusszeile
  von S. 689 («Die mit ‡ Bezeichneten sind Mitglieder des Gewerbe-Verband Zürich») stehen Verlagsinserate, die
  `convert.py` weglässt (`FOOTER`); ab S. 690 Inserate und das Häuserverzeichnis. Auf S. 607 (Fuhrhalter) setzte
  das Modell das Telefon bei allen 79 Einträgen, gedruckt ist es nur bei einem Teil.
- **1902:** wie 1901 (Kreis I–V vor der Strasse, Antiqua, Berufsregister als II. Abteilung). Gelesen auf tei im
  Wochenlauf, Seiten über IIIF der ZB. S. 528 endet mit dem «Avis» der Redaktion, S. 529–536 sind Inserate und das
  Titelblatt der II. Abteilung; unter der Fusszeile von S. 653 stehen Verlagsinserate, die `convert.py` weglässt;
  ab S. 654 Inserate. Das Zeichen am Zeilenanfang (vom Modell als § oder ☎ gelesen)
  wird wie 1901 als Telefon gewertet (`phone_flag`); in den Seitenbildern von 1902 ist es aber das Zeichen der Mitglieder
  des Gewerbe-Verbands Zürich (Fusszeile: «Die mit ‡ Bezeichneten …»), ein Telefonzeichen ist dort nicht zu sehen.
  `phone_flag` ist für 1902 (und wohl auch 1901) darum unzuverlässig.
- **1903:** wie 1900 (Kreis I–V vor der Strasse, Antiqua, kein Berufsregister im Band). Gelesen auf tei im Wochenlauf, Seiten über IIIF der ZB. Einwohner S. 33–457 (Spaltenseite 425 endet mit «Trey»); ab S. 458 das Häuserverzeichnis. Auch hier ist das Zeichen am Zeilenanfang das des Gewerbe-Verbands, `phone_flag` unzuverlässig.
- **1904:** wie 1901–1903 (Kreis I–V vor der Strasse, Antiqua). Einwohner S. 33–469 (unten Inserat, S. 470 «Avis»), Berufsregister S. 479–605 (Spaltenseite 3 bis 129, «Zugjalousienfabrikation»). Das Zeichen am Zeilenanfang ist wieder das des Gewerbe-Verbands, `phone_flag` unzuverlässig. Telefon, Treffer im anderen Band und Normdaten folgen, sobald Vernetzte Schweiz den Band übernommen hat.
- **1907:** wie 1901–1904 (Kreis I–V vor der Strasse, Antiqua). Einwohner S. 37–526 (Spaltenseite 1 bis 490, «Zwipf»; darunter Inserat), Berufsregister S. 535–680 (Spaltenseite 3 bis 148, «Zuckerwarenfabrik»; ab S. 681 Inserate). Anders als 1901–1906 unterscheidet das Modell hier das Telefonzeichen (Blitz) vom Zeichen des Gewerbe-Verbands (Stern über v); `phone_flag` stimmte in der Stichprobe. 1905 und 1906 sind gelesen, aber noch nicht übernommen (Stichprobe unter 80 %). Telefon, Treffer im anderen Band und Normdaten folgen, sobald Vernetzte Schweiz den Band übernommen hat.
- **1909:** wie 1907 (Kreis I–V vor der Strasse, Antiqua). Einwohner S. 37–562 (Spaltenseite 1 bis 526, «Zylberscher-Bähler»; darunter Inserat), Berufsregister S. 573–726 (Spaltenseite 3 bis 156, «Zuschneide-Schulen»; darunter Inserat). Telefon (Blitz) und Gewerbe-Verband (Stern über v) meist getrennt; auf Berufe-S. 661 las das Modell den Blitz als «*», dort fehlt `phone_flag`.
- **1910:** wie 1909. Einwohner S. 37–602 (Spaltenseite 1 bis 566, «Zyman-Ostrowiecki»; darunter Inserat), Berufsregister S. 613–773 (Spaltenseite 3 bis 163, «Zuschneide-Schulen»; darunter Inserat).
- **1908** ist gelesen, aber nicht übernommen (Stichprobe 15 von 20). Telefon, Treffer im anderen Band und Normdaten für 1909 und 1910 folgen, sobald Vernetzte Schweiz die Bände übernommen hat.
- **1901–1904, 1907, 1909, 1910 und 1920–1945:** dasselbe Modell, gelesen auf tei.dh.unibe.ch; die Seitenbilder kamen direkt von der ZB (IIIF, rund
  860 px breit, also 150 dpi), dann 2× vergrössert wie die anderen Bände.
- Keine Nachkorrektur und noch keine Stichprobe von Hand. 1940 hat Claude 20 zufällige Einträge (Seed 1940) mit
  dem Seitenbild verglichen: 18 in allen Feldern richtig (einmal Telefon übersehen und der Kreis der Geschäfts- an
  der Privatadresse, einmal «Amstüz» für «Amstuz»); im Feld `text` stand viermal ☎ für den Kreis. 1945 ebenso
  (Seed 1945): 18 von 20 richtig («Hönicg» für «Hönig»; einmal der Vorname als Familienname, seither behoben). Die 20 nachgelesenen Seiten von 1945 (siehe unten) hatten eine eigene Stichprobe, je ein Eintrag pro Seite: 16 von 20 richtig (zweimal das Telefonzeichen übersehen, «Dienstmann-Büro» für «Dienstmänner-Büro», «Hörwieg» und «Bankkommiss.» für «Hörwick» und «Bankcommis»; einmal der Firmenkopf «Hauser, E.» als Familienname, seither behoben).
  1901 (Seed 1901, `data/review/weekly_1901.csv`): 18 von 20 richtig («See-strasse» mit dem Trennstrich der Zeile;
  einmal Telefon auf S. 607, siehe oben). 1902 (Seed 1902, `data/review/weekly_1902.csv`): 18 von 20 richtig («Bielski»
  für «Bielinski»; bei Öchslin-Regazzoni die Geschäfts- statt der Wohnadresse). 1903 (Seed 1903, `data/review/weekly_1903.csv`): 17 von 20 in allen Feldern richtig (einmal «Geschäftsrd.» für «Geschäftsrsdr.», zweimal `phone_flag` gesetzt, wo das Zeichen des Gewerbe-Verbands steht). 1904 (Seed 1904, `data/review/weekly_1904.csv`): 18 von 20 richtig (zweimal `phone_flag` auf dem Zeichen des Gewerbe-Verbands). 1907 (Seed 1907, `data/review/weekly_1907.csv`): 16 von 20 in allen Feldern richtig (zweimal der Allianzname falsch bzw. nicht abgetrennt, einmal «Stroh Schneider» und die Geschäfts- statt der Wohnadresse, einmal der Beruf aus der Rubrik «Damen Schneiderinnen» getrennt). 1909 (Seed 1909, `data/review/weekly_1909.csv`): 16 von 20 richtig (zweimal der Allianzname bei «— -Name» fehlend bzw. vom Haupteintrag, «Bleiglasler» für «Bleiglaser», einmal das Telefon neben dem Gewerbe-Verbands-Zeichen übersehen). 1910 (Seed 1910, `data/review/weekly_1910.csv`): 18 von 20 richtig («Assfal» für «Assfalg», einmal das Telefon neben dem Gewerbe-Verbands-Zeichen übersehen). `qa_flags` markiert Verdachtsfälle
  (seltene Strasse, Trennstrich, zusammengesetzter Name); solche Einträge haben
  `parse_confidence = medium`.

## Gemeinden

- **1859, 1867, 1875 und 1885** nennen die Stadt und die Ausgemeinden (1875: Aussersihl, Enge, Fluntern,
  Hirslanden, Hottingen, Oberstrass, Riesbach, Unterstrass, Wiedikon). Sie sind seit der
  Eingemeindung 1893 Teil der Stadt; `municipality` ist darum überall «Zürich». Die alte Gemeinde
  steht im Text des Eintrags («… Rankstrasse 77 R.»), die Hausnummern sind die der alten Gemeinde.
- **1900–1910 und 1914–1945** nennen den Stadtkreis vor der Strasse (1900–1910: I–V, 1914–1930: 1–8, 1935–1945: 1–11); `street_raw` steht ohne ihn,
  `district` mit ihm. 1914 setzte das Modell oft den Kreis als Hausnummer («4 Zeughausstr. 29» → 4); `convert.py`
  nimmt dann die Nummer aus der gedruckten Zeile (12 015 Einträge).
- **Ausserhalb der Stadt:** Wer 1914 in einer anderen Gemeinde wohnte («… In Albisrieden.» 1859,
  «…, Zollikon» 1914), bekommt diese Gemeinde (`OUTSIDE` in `scripts/convert.py`). 1859 trifft das 28
  Einwohner, 1914 36.

## Lücken

- **1914:** 11 Seiten des Einwohnerverzeichnisses (S. 62, 70, 97, 120, 353, 374, 397, 413, 477, 532, 587)
  brechen in der Lesung vor dem Seitenende ab, auch im zweiten Versuch mit doppeltem Tokenbudget an derselben
  Stelle; es fehlen dort die letzten Einträge der Seite.
- **1901:** ebenso 13 Seiten (S. 35, 49, 93, 121, 316, 321, 372, 381, 429, 504, 578, 615, 645);
  **1902:** 14 Seiten (S. 49, 97, 117, 147, 154, 282, 339, 348, 370, 375, 417, 475, 481, 516); **1903:** 4 Seiten (S. 49, 183, 276, 336); **1904:** 14 Seiten (S. 61, 103, 129, 139, 157, 259, 267, 305, 321, 401, 409, 426, 482, 593); **1907:** 12 Seiten (S. 53, 113, 168, 217, 250, 266, 341, 416, 473, 519, 601, 632); **1909:** 14 Seiten (S. 48, 53, 62, 85, 87, 171, 197, 369, 401, 405, 469, 491, 501, 515); **1910:** 17 Seiten (S. 68, 77, 129, 181, 210, 213, 271, 337, 382, 389, 453, 468, 479, 550, 583, 591, 663);
  **1920:** 8 Seiten (S. 316, 711, 715, 720, 797, 870, 877, 885); **1922:** 15 Seiten (S. 45, 117, 193,
  391, 460, 473, 517, 639, 719, 801, 843, 849, 913, 935, 941); **1925:** 17 Seiten (S. 33, 60, 89, 129, 152, 305,
  553, 586, 588, 601, 606, 745, 808, 810, 873, 919, 1047); **1930:** 15 Seiten (S. 312, 435, 469, 483, 509, 714,
  831, 923, 983, 1013, 1071, 1171, 1221, 1307, 1308); **1935:** 4 Seiten (S. 201, 1206, 1443, 1444);
  **1940:** 3 Seiten (S. 1108, 1409, 1525).
- **1945:** keine Lücke mehr. 20 Seiten (S. 58, 67, 74, 222, 246, 262, 373, 494, 501, 576, 603, 646, 723, 742, 1186,
  1195, 1506, 1516, 1562, 1598) fehlten zuerst, weil ihre Lesung ohne Schlusszeile endete und `collect.py` solche
  Seiten ganz verwirft. Am 20.11.2026 neu gelesen (`scripts/weekly/nachlesung/`): mit leicht anderer Vergrösserung
  (1,8- bis 2,5-fach statt 2-fach) und 32 000 Tokens kamen 18 Seiten mit Schlusszeile. Die meisten alten Lesungen
  waren vollständig gewesen, drei nicht (S. 373: 41 statt 128 Einträge, S. 501: 21 statt 131, S. 603: 94 statt 125).
  S. 74 endet in fünf Runden ohne Schlusszeile, aber mit dem letzten Eintrag der Seite (am Bild geprüft). S. 1195
  bricht in jeder Runde im selben Eintrag ab, elf Einträge vor dem Seitenende; dort stammt die rechte Spalte aus
  einer eigenen Lesung des Spaltenausschnitts. Beide Fälle sind in der Rohdatei auf tei vermerkt (`ended_note`).
  Ob dasselbe Vorgehen die Lücken der Bände 1914–1940 schliesst, ist nicht geprüft.
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
- `scripts/10_geo.py`: das Gebiet je Eintrag (1859 Grosse/Kleine Stadt, 1867–1885 alte Gemeinde, 1900–1945
  Kreis) und die Strassenpunkte aus OpenStreetMap, nur wenn sie im Quartier des Gebiets liegen
  (`web/geo/streets.csv`); offene Strassen von Hand in `web/geo/streets_manual.csv` (`10_geo.py todo`).
  Hausnummern werden nicht verortet.
- `scripts/80_telefon.py --vs <vernetzte-schweiz> --commit <sha>`: Einträge mit ☎ → PTT-Telefonbuch
  (`web/telefon.csv`, Commit in `telefon_source.txt`).
- `scripts/81_baende.py`: dieselbe Person in den anderen Bänden (`web/baende.csv`, im Repo gepackt je Jahr
  als `web/baende/<Jahr>.csv.gz`; `90_seite.py` teilt und packt neu, wenn die .csv neuer ist).
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

Die Bücher bis 1914 sind gemeinfrei (URG Art. 2 Abs. 1, Art. 29 Abs. 2). Die Scans aller Bände, auch 1920–1945,
gibt die Zentralbibliothek Zürich unter CC0 frei.
Die Daten in `data/` stehen unter [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/),
der Code unter MIT. Die Scans selbst liegen nicht in diesem Repo.
