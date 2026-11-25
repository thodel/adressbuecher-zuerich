"""Der Zürcher Lauf (scripts/weekly/zh_weekly.py) beginnt keinen Band, solange der Berner Lauf liest.

    python3 -m unittest discover -s tests -v
"""
import importlib.util
import unittest
from pathlib import Path

WEEKLY = Path(__file__).resolve().parents[1] / "scripts" / "weekly"


class VorrangBern(unittest.TestCase):
    def test_wartet_auf_bern_und_jeden_lesedurchgang(self):
        spec = importlib.util.spec_from_file_location("zh_weekly", WEEKLY / "zh_weekly.py")
        zh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(zh)
        self.assertEqual(set(zh.OTHERS.split("|")), {"run_qwen.py", "be_weekly.py"})


if __name__ == "__main__":
    unittest.main()
