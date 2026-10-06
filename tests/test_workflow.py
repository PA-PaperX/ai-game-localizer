import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from game_localizer.cli import main, read_json, save, validate, LocalizerError


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.project = self.root / "project.json"
        self.batch = self.root / "batch.json"
        self.result = self.root / "result.json"
        self.out = self.root / "stage.csv"
        self.source.write_text('key,source,target,metadata\nopen,Open {door},,keep\nhello,"Hello, friend",Original translation,untouched\n', encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, code=0):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            actual = main([str(x) for x in args])
        self.assertEqual(actual, code, args)

    def setup_drafts(self):
        self.run_cli("import", self.source, self.project, "--format", "csv", "--engine", "unreal")
        self.run_cli("batch", self.project, self.batch)
        b = read_json(self.batch)
        items = [{"id": e["id"], "source_sha256": e["source_sha256"],
                  "target": "เปิด {door}" if e["id"] == "open" else "ไง แก",
                  "context": {"speaker": "synthetic player", "scene": "test"}} for e in b["items"]]
        save(self.result, {"items": items})
        return items

    def test_review_gate_and_roundtrip(self):
        original = self.source.read_bytes()
        self.setup_drafts()
        self.run_cli("apply", self.project, self.batch, self.result)
        self.run_cli("export", self.project, self.out)
        with self.out.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["target"], "Open {door}")
        self.assertEqual(rows[1]["target"], "Original translation")
        self.out.unlink()
        self.run_cli("review", self.project, "--id", "open", "--reviewer", "PaperX", "--notes", "Verified scene and placeholder")
        self.run_cli("export", self.project, self.out)
        with self.out.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["target"], "เปิด {door}")
        self.assertEqual(rows[0]["metadata"], "keep")
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(read_json(self.project)["entries"][1]["status"], "draft")

    def test_atomic_rejection(self):
        items = self.setup_drafts()
        before = self.project.read_bytes()
        items[1]["source_sha256"] = "stale"
        save(self.result, {"items": items})
        self.run_cli("apply", self.project, self.batch, self.result, code=2)
        self.assertEqual(before, self.project.read_bytes())

    def test_unknown_duplicate_missing_ids(self):
        items = self.setup_drafts()
        for wrong in (items[:1], items + items[:1], items + [{"id": "injected"}]):
            save(self.result, {"items": wrong})
            self.run_cli("apply", self.project, self.batch, self.result, code=2)

    def test_bad_target(self):
        items = self.setup_drafts()
        for target in ("เปิด", "", "\ufffd {door}", "เปิด {other}"):
            items[0]["target"] = target
            save(self.result, {"items": items})
            self.run_cli("apply", self.project, self.batch, self.result, code=2)

    def test_stale_reviewed_batch(self):
        self.setup_drafts()
        self.run_cli("apply", self.project, self.batch, self.result)
        self.run_cli("review", self.project, "--id", "open", "--reviewer", "PaperX", "--notes", "Checked")
        before = self.project.read_bytes()
        self.run_cli("apply", self.project, self.batch, self.result, code=2)
        self.assertEqual(self.project.read_bytes(), before)

    def test_tampered_source(self):
        self.setup_drafts()
        p = read_json(self.project)
        p["entries"][0]["source"] = "Altered"
        save(self.project, p)
        self.run_cli("status", self.project, code=2)

    def test_duplicate_csv_and_wrong_width(self):
        for contents in ("key,source\nx,a\nx,b\n", "key,source\nx,a,extra\n", "key,source,source\nx,a,b\n"):
            self.source.write_text(contents, encoding="utf-8")
            self.run_cli("import", self.source, self.project, "--format", "csv", code=2)
            self.assertFalse(self.project.exists())

    def test_unity_columns_preserved(self):
        self.source.write_text('Key,Id,English(en),Thai(th),Shared Comments\nGREETING,42,Hello,,NPC\n', encoding="utf-8")
        self.run_cli("import", self.source, self.project, "--format", "csv", "--engine", "unity", "--id-column", "Key", "--source-column", "English(en)", "--target-column", "Thai(th)")
        self.run_cli("export", self.project, self.out)
        with self.out.open(encoding="utf-8", newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row, {"Key": "GREETING", "Id": "42", "English(en)": "Hello", "Thai(th)": "Hello", "Shared Comments": "NPC"})

    def test_godot_bom_multiline_semicolon(self):
        self.source.write_text('\ufeffkeys;en;fr\nline;"First\nSecond";Autre\n', encoding="utf-8", newline="")
        self.run_cli("import", self.source, self.project, "--format", "csv", "--engine", "godot", "--id-column", "keys", "--source-column", "en", "--target-column", "th", "--delimiter", ";")
        self.run_cli("export", self.project, self.out)
        self.assertTrue(self.out.read_bytes().startswith(b"\xef\xbb\xbf"))
        with self.out.open(encoding="utf-8-sig", newline="") as f:
            row = next(csv.DictReader(f, delimiter=";"))
        self.assertEqual(row["th"], "First\nSecond")
        self.assertEqual(row["fr"], "Autre")

    def test_json_pointer_preserves_non_text_and_outside_selection(self):
        source = self.root / "locale.json"
        save(source, {"dialogue": {"a/b~c": ["Hello {name}", 4, True]}, "script": "never translate"})
        self.run_cli("import", source, self.project, "--format", "json", "--pointer", "/dialogue")
        self.run_cli("batch", self.project, self.batch)
        e = read_json(self.batch)["items"][0]
        self.assertEqual(e["id"], "/dialogue/a~1b~0c/0")
        save(self.result, {"items": [{"id": e["id"], "source_sha256": e["source_sha256"], "target": "สวัสดี {name}"}]})
        self.run_cli("apply", self.project, self.batch, self.result)
        self.run_cli("review", self.project, "--id", e["id"], "--reviewer", "test", "--notes", "Synthetic test")
        self.run_cli("export", self.project, self.out)
        self.assertEqual(read_json(self.out), {"dialogue": {"a/b~c": ["สวัสดี {name}", 4, True]}, "script": "never translate"})

    def test_json_requires_explicit_scope_and_unique_keys(self):
        source = self.root / "source.json"
        source.write_text('{"a":"one","a":"two"}', encoding="utf-8")
        self.run_cli("import", source, self.project, "--format", "json", "--pointer", "", code=2)
        self.run_cli("import", source, self.project, "--format", "json", code=2)

    def test_refuse_overwrite(self):
        self.setup_drafts()
        self.run_cli("export", self.project, self.source, code=2)
        self.run_cli("export", self.project, self.project, code=2)
        self.run_cli("batch", self.project, self.batch, code=2)

    def test_inspection_candidates(self):
        (self.root / "UnityPlayer.dll").touch()
        (self.root / "demo.locres").touch()
        (self.root / "project.godot").touch()
        report = self.root / "inspection.json"
        self.run_cli("inspect", self.root, "--output", report)
        self.assertEqual(set(read_json(report)["candidates"]), {"unreal", "unity", "godot"})

    def test_tokens_and_unsupported_formats(self):
        for source, target in (("<b>{name}</b> %s %d", "<b>{name}</b> %d %s"), ("{n, plural, one {x} other {y}}", "{n}"), ("{n}|plural(one=x,other=y)", "{n}")):
            with self.assertRaises(LocalizerError):
                validate(source, target)
        validate("<b>{name}</b> %1$s %2$d", "%2$d <b>{name}</b> %1$s")

    def test_locres_mismatch_never_publishes_binary(self):
        original = self.root / "original.locres"
        original.write_bytes(b"synthetic original")
        tool = self.root / "converter.exe"
        tool.write_bytes(b"synthetic converter marker")
        output = self.root / "staged.locres"
        def fake_converter(args, **kwargs):
            dest = Path(args[-1])
            if args[1] == "import":
                dest.write_bytes(b"synthetic converted binary")
            else:
                dest.write_text("key,source\nwrong,wrong\n", encoding="utf-8")
        with patch("game_localizer.cli.subprocess.run", side_effect=fake_converter):
            self.run_cli("locres-compile", original, self.source, output, "--tool", tool, code=2)
        self.assertFalse(output.exists())
        self.assertEqual(original.read_bytes(), b"synthetic original")

    def test_locres_matching_roundtrip_publishes_stage(self):
        original = self.root / "original.locres"
        original.write_bytes(b"synthetic original")
        tool = self.root / "converter.exe"
        tool.write_bytes(b"synthetic converter marker")
        self.source.write_text("key,source,target\nopen,Open,เปิด\n", encoding="utf-8")
        output = self.root / "staged.locres"
        def fake_converter(args, **kwargs):
            dest = Path(args[-1])
            if args[1] == "import":
                dest.write_bytes(b"synthetic converted binary")
            else:
                dest.write_text("key,source\nopen,เปิด\n", encoding="utf-8")
        with patch("game_localizer.cli.subprocess.run", side_effect=fake_converter):
            self.run_cli("locres-compile", original, self.source, output, "--tool", tool)
        self.assertEqual(output.read_bytes(), b"synthetic converted binary")
        self.assertEqual(original.read_bytes(), b"synthetic original")

    def test_batch_target_language_mismatch(self):
        self.setup_drafts()
        b = read_json(self.batch)
        b["target_language"] = "another language"
        save(self.batch, b)
        before = self.project.read_bytes()
        self.run_cli("apply", self.project, self.batch, self.result, code=2)
        self.assertEqual(self.project.read_bytes(), before)

    def test_batch_research_first_with_project_brief(self):
        self.run_cli("import", self.source, self.project, "--format", "csv")
        brief = self.root / "brief.json"
        save(brief, {"game": "Synthetic adventure", "build": "test-1", "style": "project-specific"})
        self.run_cli("batch", self.project, self.batch, "--brief", brief)
        b = read_json(self.batch)
        self.assertEqual(b["project_brief"]["game"], "Synthetic adventure")
        self.assertIn("BEFORE", b["instruction"])
        self.assertIn("research report before any target text", b["research_prompt"])
        self.assertIn("Only after", b["translation_prompt"])
        self.assertNotIn("outlast", json.dumps(b).lower())
        self.assertNotIn("translate profanity at", json.dumps(b).lower())

    def test_batch_rejects_invalid_project_brief(self):
        self.run_cli("import", self.source, self.project, "--format", "csv")
        brief = self.root / "brief.json"
        save(brief, ["not a project brief"])
        self.run_cli("batch", self.project, self.batch, "--brief", brief, code=2)
        self.assertFalse(self.batch.exists())


if __name__ == "__main__":
    unittest.main()
