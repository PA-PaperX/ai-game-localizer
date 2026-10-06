"""Create an allowlisted source distribution without game data or local work."""
import hashlib
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
files = [root / name for name in ("README.md", "AGENTS.md", "CONTRIBUTING.md", "LICENSE", "pyproject.toml", ".gitignore", "Start-GUI.cmd")]
allowed = {".py", ".md", ".json", ".csv", ".yml", ".html", ".css", ".js", ".cmd"}
for folder in ("src", "tests", "examples", "docs", "scripts", ".github", ".21st"):
    files.extend(p for p in (root / folder).rglob("*") if p.is_file() and p.suffix in allowed and "__pycache__" not in p.parts)
for path in files:
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise SystemExit(f"Refusing linked/outside source: {path.name}")
    content = path.read_text(encoding="utf-8")
    local_path_marker = "C:" + chr(92) + "Users" + chr(92)
    key_marker = "BEGIN " + "PRIVATE KEY"
    if local_path_marker in content or key_marker in content:
        raise SystemExit(f"Local path/private key marker in source: {path.name}")
destination = root / "dist" / "paperx-ai-game-localizer-0.2.1-source.zip"
destination.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        info = zipfile.ZipInfo("ai-game-localizer/" + path.relative_to(root).as_posix(), date_time=(2026, 10, 6, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, path.read_bytes())
print(f"{destination.name}: {len(set(files))} source files")
print("SHA256: " + hashlib.sha256(destination.read_bytes()).hexdigest())
