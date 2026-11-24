"""GitHub nimmt keine Datei über 100 MB an; ein Push mit so einer Datei scheitert erst beim Server.

Am 23.11.2026 war web/baende.csv.gz mit 1903–1910 auf 96 MB gewachsen. Seither liegt sie je Jahr in
web/baende/<Jahr>.csv.gz (scripts/90_seite.py pack_other). Die Grenze hier liegt bei 90 MB, damit eine wachsende
Datei auffällt, bevor der Push scheitert.
"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRENZE = 90_000_000


class Dateigroesse(unittest.TestCase):
    def test_keine_datei_im_repo_ueber_90_mb(self):
        files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        zu_gross = [(f, (ROOT / f).stat().st_size) for f in files.decode().split("\0")
                    if f and (ROOT / f).is_file() and (ROOT / f).stat().st_size > GRENZE]
        self.assertEqual(zu_gross, [], "über 90 MB: aufteilen oder packen")

    def test_baende_je_jahr(self):
        self.assertFalse((ROOT / "web" / "baende.csv.gz").exists(), "alte Gesamtdatei, gehört nach web/baende/")
        teile = sorted((ROOT / "web" / "baende").glob("*.csv.gz"))
        self.assertTrue(teile)
        self.assertTrue(all(p.name[:4].isdigit() for p in teile), teile)


if __name__ == "__main__":
    unittest.main()
