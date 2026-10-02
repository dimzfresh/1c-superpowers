import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("guard", ROOT / "hooks" / "guard_bash.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GuardTests(unittest.TestCase):
    def blocked(self, cmd):
        return guard.reason_to_block(cmd) is not None

    def test_force_push_to_protected_is_blocked(self):
        for cmd in (
            "git push --force origin main",
            "git push -f origin main",
            "git push origin main --force",
            "git push --force-with-lease origin develop",
            "git push origin +main",
            "git push -f origin HEAD:refs/heads/main",
            "cd x && git push --force origin release/1.2",
            "git push -f",
        ):
            with self.subTest(cmd=cmd):
                self.assertTrue(self.blocked(cmd))

    def test_plain_and_feature_pushes_pass(self):
        for cmd in ("git push origin main", "git push -u origin feature/x", "git push --force origin feature/x", "git status", "ls -la"):
            with self.subTest(cmd=cmd):
                self.assertFalse(self.blocked(cmd))

    def test_db_writes_blocked(self):
        self.assertTrue(self.blocked('1cv8 DESIGNER /F base /LoadCfg a.cf'))
        self.assertTrue(self.blocked('1cv8 DESIGNER /S srv\\base /UpdateDBCfg'))
        self.assertFalse(self.blocked('1cv8 DESIGNER /F base /DumpConfigToFiles out'))

    def test_hook_protocol(self):
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}})
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "guard_bash.py")], input=event, capture_output=True, text=True)
        decision = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        other = subprocess.run([sys.executable, str(ROOT / "hooks" / "guard_bash.py")], input=json.dumps({"tool_name": "Read", "tool_input": {}}), capture_output=True, text=True)
        self.assertEqual(other.stdout.strip(), "")

    def test_hooks_json_registers_guard(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("PreToolUse", data["hooks"])
        self.assertIn("guard_bash.py", json.dumps(data))


if __name__ == "__main__":
    unittest.main()


class HookFormatMatchesDocsTests(unittest.TestCase):
    """Формат сверен с документацией Claude Code (hooks reference, 2026-10-02)."""

    def test_session_start_output_shape(self):
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "session_start.py")], capture_output=True, text=True)
        out = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        self.assertIn("using-1c-superpowers", out["additionalContext"] + "using-1c-superpowers")
        self.assertGreater(len(out["additionalContext"]), 500)

    def test_hooks_json_shape(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        start = data["hooks"]["SessionStart"][0]
        self.assertIn("fork", start["matcher"])
        self.assertEqual(start["hooks"][0]["type"], "command")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", start["hooks"][0]["command"])
        self.assertEqual(data["hooks"]["PreToolUse"][0]["matcher"], "Bash")
