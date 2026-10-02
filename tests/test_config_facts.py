import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "1c-review" / "scripts" / "config_facts.py"
DUMP = ROOT / "tests" / "fixture-dump"
BSP = ROOT / "tests" / "fixture-dump-bsp"


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


class ConfigFactsTests(unittest.TestCase):
    def test_info_has_compat_and_locks(self):
        code, out, _ = run("info", DUMP)
        self.assertEqual(code, 0)
        self.assertIn("Режим совместимости: Version8_3_24", out)
        self.assertIn("Блокировки: Managed", out)
        self.assertIn("Версия установленной платформы: в выгрузке нет", out)

    def test_info_finds_bsp_version(self):
        _, out, _ = run("info", BSP)
        self.assertRegex(out, r"БСП: \d")

    def test_card_shows_module_flags(self):
        _, out, _ = run("card", DUMP, "CommonModules", "ОбменССайтомСервер")
        self.assertIn("ReturnValuesReuse=DontUse", out)
        self.assertIn("Privileged=true", out)

    def test_search_returns_line_numbers(self):
        _, out, _ = run("search", DUMP, "HTTPСоединение")
        self.assertRegex(out, r"ObjectModule\.bsl:\d+:")

    def test_list_objects(self):
        _, out, _ = run("list", DUMP, "Documents")
        self.assertIn("ЗаказКлиента", out)

    def test_path_escape_is_refused(self):
        code, _, err = run("read", DUMP, "../x")
        self.assertEqual(code, 1)
        self.assertIn("выходит за каталог", err)

    def test_1cd_dump_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "Configuration.xml").write_text("<x/>", encoding="utf-8")
            Path(tmp, "base.1CD").write_bytes(b"x")
            code, _, err = run("info", tmp)
            self.assertEqual(code, 1)
            self.assertIn("1CD", err)

    def test_no_writes_in_script(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for banned in (".write_text(", ".write_bytes(", "open(", "subprocess", "os.remove", "shutil"):
            self.assertNotIn(banned, text)


if __name__ == "__main__":
    unittest.main()
