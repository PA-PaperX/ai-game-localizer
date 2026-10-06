"""Synthetic full workflow; temporary files only, no real game data."""
import json
from pathlib import Path
import tempfile
from game_localizer.cli import main


def run(*args):
    if main([str(a) for a in args]):
        raise SystemExit("Demo failed")


with tempfile.TemporaryDirectory(prefix="paperx-demo-") as directory:
    root = Path(directory)
    project, batch, result = [root / f"{name}.json" for name in ("project", "batch", "result")]
    run("import", Path(__file__).with_name("unreal.csv"), project, "--format", "csv", "--engine", "unreal")
    brief = root / "brief.json"
    brief.write_text(json.dumps({"game": "Synthetic UI demo", "build": "fixture-1", "source_language": "en", "target_language": "th", "style": "Concise neutral UI", "available_evidence": ["examples/unreal.csv"]}), encoding="utf-8")
    run("batch", project, batch, "--brief", brief)
    items = json.loads(batch.read_text(encoding="utf-8"))["items"]
    # The fixture author defines these UI functions; no external scene exists.
    contexts = {e["id"]: {"string_type": "ui", "scene": "Synthetic door interaction" if e["id"] == "door.open" else "Synthetic loading screen", "confidence": "high", "translation_readiness": "ready", "references": [{"type": "local_resource", "uri": "examples/unreal.csv and examples/demo.py", "locator": e["id"], "supports": "Original text and fixture-author-defined UI function"}]} for e in items}
    research = root / "research.json"
    research.write_text(json.dumps({"game": "Synthetic UI demo", "items": [{"id": e["id"], "source_sha256": e["source_sha256"], "context": contexts[e["id"]]} for e in items]}, ensure_ascii=False), encoding="utf-8")
    print("Research report prepared from synthetic fixture evidence before drafting targets.")
    targets = {"door.open": "เปิด {door}", "system.loading": "กำลังโหลด..."}
    result.write_text(json.dumps({"items": [{"id": e["id"], "source_sha256": e["source_sha256"], "target": targets[e["id"]], "context": contexts[e["id"]]} for e in items]}, ensure_ascii=False), encoding="utf-8")
    run("apply", project, batch, result)
    for key in targets:
        run("review", project, "--id", key, "--reviewer", "synthetic-demo", "--notes", "Checked original synthetic fixture and tokens")
    run("export", project, root / "translated.csv")
    run("status", project, "--markdown", root / "PROGRESS.md")
    print((root / "translated.csv").read_text(encoding="utf-8"))
