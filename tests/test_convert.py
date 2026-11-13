"""Strasse, Hausnummer und Familienname (scripts/convert.py)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from convert import SAME, clean_street, municipality, own_surname, section_of  # noqa: E402


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
