"""Das Bandmenü der Seite ist nach Jahr geordnet; der Standardband ist vorgewählt, nicht vorangestellt.

Bis 25.11.2026 stand das Menü von Hand im HTML von scripts/90_seite.py, 1914 vor 1945. Der Test liest nur
VOLUMES, DEFAULT_VOLUME und vol_options aus dem Skript (ohne die Daten zu laden).

    python3 -m unittest discover -s tests -v
"""
import ast
import re
import unittest
from pathlib import Path

SKRIPT = Path(__file__).resolve().parents[1] / "scripts" / "90_seite.py"
NAMEN = {"VOLUMES", "DEFAULT_VOLUME", "vol_options"}


def _teile() -> dict:
    baum = ast.parse(SKRIPT.read_text(encoding="utf-8"))
    knoten = [n for n in baum.body
              if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in NAMEN for t in n.targets))
              or (isinstance(n, ast.FunctionDef) and n.name in NAMEN)]
    ns: dict = {}
    exec(compile(ast.Module(body=knoten, type_ignores=[]), str(SKRIPT), "exec"), ns)
    return ns


class Bandmenue(unittest.TestCase):
    def test_nach_jahr_absteigend_standard_vorgewaehlt(self):
        ns = _teile()
        self.assertTrue(NAMEN <= ns.keys(), NAMEN - ns.keys())
        html = ns["vol_options"](ns["VOLUMES"], ns["DEFAULT_VOLUME"])
        werte = re.findall(r'<option value="(\d{4})"', html)
        self.assertEqual(sorted(werte), sorted(ns["VOLUMES"]))
        self.assertEqual(werte, sorted(werte, key=int, reverse=True))
        self.assertEqual(re.findall(r'<option value="(\d{4})" selected', html), [ns["DEFAULT_VOLUME"]])
        self.assertTrue(html.endswith('<option value="">alle Bände (gross)</option>'))

    def test_kein_handgeschriebenes_menue(self):
        self.assertNotRegex(SKRIPT.read_text(encoding="utf-8"), r'<select id="vol"[^>]*><option value="\d')


class Staedteleiste(unittest.TestCase):
    """scripts/site_nav.py (in allen adressbuecher-* gleich): mehrere Bestände einer Stadt nach Anfangsjahr."""

    def test_bestaende_einer_stadt_nach_jahr(self):
        import re as _re
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import site_nav
        stadt: dict = {}
        for _key, name, _url in site_nav.CITIES:
            ort, jahre = name.rsplit(" ", 1)
            stadt.setdefault(ort, []).append(int(_re.match(r"\d{4}", jahre).group(0)))
        for ort, anfang in stadt.items():
            self.assertEqual(anfang, sorted(anfang), ort)


if __name__ == "__main__":
    unittest.main()
