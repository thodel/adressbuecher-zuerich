"""Strasse, Hausnummer und Familienname (scripts/convert.py)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collections import Counter  # noqa: E402

from convert import (CIRCLED, MUNICIPALITY, PHONE_LEAD, SAME, clean_street, district, kreis_from_text,  # noqa: E402
                     municipality, own_surname, section_of, street_kreis)


class Street(unittest.TestCase):
    def test_number_moves_to_its_field(self):
        self.assertEqual(clean_street("Bärenplatz 29", ""), ("Bärenplatz", "29"))
        self.assertEqual(clean_street("r. Neuve, 5", ""), ("r. Neuve", "5"))
        self.assertEqual(clean_street("Kramgasse 62", "62"), ("Kramgasse", "62"))

    def test_district_number_is_dropped(self):
        self.assertEqual(clean_street("4 Lagerstrasse 24", ""), ("Lagerstrasse", "24"))
        self.assertEqual(clean_street("III Konradstrasse", "25"), ("Konradstrasse", "25"))
        self.assertEqual(clean_street("1. Augustweg", "3"), ("1. Augustweg", "3"))
        self.assertEqual(clean_street("3 Scheunen", "57", kreis=False), ("3 Scheunen", "57"))

    def test_phone_marks_are_dropped(self):
        self.assertEqual(clean_street("pl. de la Gare. R T 180", ""), ("pl. de la Gare", ""))


class District(unittest.TestCase):
    def test_kreis_and_number_from_text(self):
        self.assertEqual(kreis_from_text("1914", "Wenzler, Karl, Maurer, 6 Habsburgstrasse 26.", "Habsburgstrasse"), ("6", "26"))
        self.assertEqual(kreis_from_text("1914", "Globus, 1 Bahnhofbrücke 1 u. 1 Löwenplatz 41.", "Bahnhofbrücke"), ("1", "1"))
        self.assertEqual(kreis_from_text("1900", "— Emil, Metzger, III Freischützgasse 1.", "Freischützgasse"), ("III", "1"))
        self.assertEqual(kreis_from_text("1885", "— Rud., Rennweg 50 Z.", "Rennweg"), ("", ""))

    def test_district_per_volume(self):
        self.assertEqual(district("1914", {"district": "", "text": ""}, "26", "6"), "Kreis 6")
        self.assertEqual(district("1900", {"district": "III", "text": ""}, "1", ""), "Kreis III")
        self.assertEqual(district("1885", {"district": "R.", "text": ""}, "77", ""), "Riesbach")
        self.assertEqual(district("1875", {"district": "", "text": "Beuret, Schlosser, Wildbachstrasse 27 Riesbach."}, "27", ""), "Riesbach")
        self.assertEqual(district("1859", {"district": "", "text": ""}, "339 g", ""), "Grosse Stadt")


class Municipality(unittest.TestCase):
    def test_outside_the_city(self):
        self.assertEqual(municipality({"district": "Zollikon"}), "Zollikon")
        self.assertEqual(municipality({"district": "Aussersihl."}), "Zürich")
        self.assertEqual(municipality({"district": "4"}), "Zürich")
        self.assertEqual(municipality({"district": "", "text": "Wybler, Kaspar, Viehhandel. In Albisrieden."}), "Albisrieden")
        self.assertEqual(municipality({"district": "In Riesbach", "text": "Haasis, Jakob. In Riesbach, 62"}), "Zürich")
        self.assertEqual(municipality({"district": "", "text": "Meier, J. In Ulstetten."}), "Altstetten")


class SameAddress(unittest.TestCase):
    def test_marks(self):
        for s in ("m. a", "m. a.", "m.a.", "dito"):
            self.assertTrue(SAME.match(s), s)
        self.assertFalse(SAME.match("Maupas"))


class Surname(unittest.TestCase):
    def test_wrong_inheritance_is_replaced(self):
        self.assertEqual(own_surname({"surname": "Hegner", "dash_prefix": "1", "text": "Grüter, Alfred."}), "Grüter")
        self.assertEqual(own_surname({"surname": "Roth", "dash_prefix": "1", "text": "— Rud., Sohn"}), "Roth")
        self.assertEqual(own_surname({"surname": "☎ Adler", "dash_prefix": "0", "text": "☎ Adler, Gasthaus"}), "Adler")


class Sections(unittest.TestCase):
    def test_outside(self):
        self.assertEqual(section_of(next(iter(__import__("convert").SECTIONS)), 1), "")


if __name__ == "__main__":
    unittest.main()


class Circled1930(unittest.TestCase):
    def test_circled_digit_is_the_kreis(self):
        text = "— Karl G. (Neukomm), Glasermeister, ③ Badenerstrasse 437.".translate(CIRCLED)
        self.assertEqual(kreis_from_text("1930", text, "Badenerstrasse"), ("3", "437"))

    def test_phone_only_at_line_start(self):
        self.assertTrue(PHONE_LEAD.search("☎— Jakob J. (Maspero), Malermeister, ☎ Fliederstr. 11."))
        self.assertTrue(PHONE_LEAD.search("☎Acar A.-G., Handel in Werkzeugen, 2 Bleicherweg 5."))
        self.assertTrue(PHONE_LEAD.search("Gross, E., 4 Hohlstrasse 123. Tel. S 3405."))
        self.assertFalse(PHONE_LEAD.search("— Luise (Krieg), Wwe., ☎ Badenerstr. 362."))

    def test_kreis_from_street_only_when_unambiguous(self):
        row = lambda st, d: {"street_raw": st, "district": d, "municipality": MUNICIPALITY, "qa_flags": ""}  # noqa: E731
        out = [row("Näfgasse", "Kreis 8")] * 3 + [row("Seestrasse", "Kreis 2")] * 3 + [row("Seestrasse", "Kreis 8")] * 3
        lost = [row("Näfgasse", ""), row("Seestrasse", "")]
        street_kreis(out + lost, Counter())
        self.assertEqual([r["district"] for r in lost], ["Kreis 8", ""])
        self.assertEqual(lost[0]["qa_flags"], "kreis_aus_strasse")
