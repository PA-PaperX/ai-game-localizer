# PaperX AI Game Localizer

An offline, engine-independent text workflow for AI-assisted game localization: project brief → resource import → scene research with evidence → translation draft → validation → editorial review → staged export → engine-specific build and runtime verification.

เครื่องมือช่วยทำงานแปลเกมกับ AI โดย PaperX รุ่น **0.2.1** ใช้ Python 3.10 ขึ้นไป ไม่มี API key และไม่ส่งข้อความไปบริการออนไลน์เอง ใช้กับ AI ที่อ่านไฟล์ JSON ได้ รวมถึงผู้ช่วยที่ทำงานใน repository

## What works today

| Engine / input | Implemented | Packaging boundary |
| --- | --- | --- |
| Unreal Engine | UnrealLocres CSV (`key,source,target`); optional external `.locres` export/import bridge with round-trip validation | No generic PAK/IoStore packing, encryption keys, signing or installation |
| Unity | Localization String Table CSV with configurable columns; preserves Id, comments and other locales | Re-import via Unity project or a game-specific compatible resource tool; no universal AssetBundle patcher |
| Godot | Exported translation CSV (keys and locale columns) | Import/build in the project or use a compatible game-specific workflow; no PCK patcher |
| Other engines | Selected string leaves in exported UTF-8 JSON, generic CSV; filename inspection for Ren'Py, RPG Maker and GameMaker | Detection is not extraction or binary mod support |

One project JSON represents one resource. Keep separate projects per resource/language and stage them under a shared mod directory. Binary game assets are never included in this repository.

## Install and quick start

### GUI preview (0.2.1)

After installation, run `game-localizer-gui --workspace work/gui`, or double-click **Start-GUI.cmd** in the source checkout. The editor opens in your local browser with a NavigationView-inspired two-tab navigation, 50-entry pagination, English/Thai/key search, source-line separation, draft history, scene evidence, AI batches and reviewed CSV export. It runs offline; AI research and translation are performed by the assistant you choose.

This first GUI detects columns in **exported UTF-8 CSV**. It does not extract arbitrary game binaries. GUI edits stay in its workspace; exporting stages text for the game's compatible build process. [GUI guide and boundaries](docs/GUI.md).

```powershell
git clone https://github.com/PA-PaperX/ai-game-localizer.git
cd ai-game-localizer
python -m pip install -e .
game-localizer inspect "D:\Games\YourGame" --output inspection.json
game-localizer import examples/unreal.csv work/project.json --format csv --engine unreal
```

Before running the `batch` command, create `work/project-brief.json` from [the brief template](examples/project-brief.json), replacing game/build metadata and defining that project's languages, glossary and character voices.

```powershell
game-localizer batch work/project.json work/batch-01.json --limit 30 --brief work/project-brief.json
```

Give the batch, brief, [AGENTS.md](AGENTS.md) and [context research protocol](docs/CONTEXT_RESEARCH.md) to your AI assistant. **Request a research report first, with no translations.** It must inspect neighboring text and find scene-specific evidence for speakers, listeners, relationships, events, referents and tone. Require direct references with timestamps, sections or local resource locators. Defer unresolved facts that could change meaning.

After checking the research report, request draft translations using [the separate translation prompt](docs/AI_WORKFLOW.md). Each generated batch includes `research_prompt` followed by `translation_prompt`; neither assumes a particular game, genre or pronoun scheme. The CLI does not browse or verify citations itself.

The translation result format below uses a synthetic UI example. Real results must contain the context established by their research report:

```json
{
  "items": [
    {
      "id": "door.open",
      "source_sha256": "COPY_THE_EXACT_HASH_FROM_THE_BATCH",
      "target": "เปิด {door}",
      "context": {
        "speaker": "system",
        "string_type": "ui",
        "scene": "door interaction",
        "confidence": "high",
        "references": [{"type": "local_resource", "uri": "examples/unreal.csv", "locator": "door.open", "supports": "Synthetic door prompt; replace with actual screen/scene evidence"}]
      }
    }
  ]
}
```

Return **every ID in that batch exactly once**. If meaning-critical research remains unresolved, finish the report or prepare a smaller resolved batch before returning an apply-ready result. Unknown, duplicate, missing or stale IDs and broken placeholders reject the entire result before saving. Applied results are always drafts, regardless of an AI's claimed approval.

```powershell
game-localizer apply work/project.json work/batch-01.json work/result-01.json
game-localizer review work/project.json --id door.open --reviewer Reviewer --notes "Checked scene evidence, wording and token"
game-localizer export work/project.json staging/translated.csv
game-localizer status work/project.json --markdown staging/PROGRESS.md
```

Drafts do not enter exported translations. Unreviewed CSV rows preserve their existing target or fall back to source when the target is empty. JSON exports preserve unreviewed values. Reviewers are responsible for meaning and context: structural validation cannot prove translation quality. `review` records an explicit attestation, not an automatic linguistic assessment.

Outputs must use a new path. `export` writes staging files and refuses the recorded source path; it does not install a mod or launch the game. Keep original assets backed up and use the correct game-specific installation process after testing.

Run the complete synthetic example (no AI account needed):

```powershell
python examples/demo.py
python -m unittest discover -s tests -v
```

## Unity / Godot / JSON recipes

```powershell
game-localizer import examples/unity.csv work/unity.json --format csv --engine unity --id-column Key --source-column "English(en)" --target-column "Thai(th)"
game-localizer import examples/godot.csv work/godot.json --format csv --engine godot --id-column keys --source-column en --target-column th
game-localizer import examples/locale.json work/other.json --format json --pointer /dialogue
```

CSV defaults to comma; `--delimiter ";"` handles semicolon exports. UTF-8/BOM, multiline values, row order and extra columns are preserved semantically; CSV quoting and JSON whitespace can be normalized. JSON uses RFC 6901 pointers. Use `--pointer ""` only if the entire JSON contains localization data. Never translate IDs, script expressions, file paths or event command data as ordinary dialogue.

## Unreal `.locres` bridge

Supply your own compatible [UnrealLocres](https://github.com/akintos/UnrealLocres) executable; this project does not distribute it. The bridge expects its `export INPUT -o OUTPUT` and `import ORIGINAL CSV -o OUTPUT` command syntax, and `key,source,target` CSV convention. Tool version and resource format must be compatible.

```powershell
game-localizer locres-extract extracted/Game.locres staging/original.csv --tool "D:\Tools\UnrealLocres.exe"
# Import original.csv, batch, apply, review, export translated.csv as above.
game-localizer locres-compile extracted/Game.locres staging/translated.csv staging/Game.locres --tool "D:\Tools\UnrealLocres.exe"
```

Compilation re-exports the temporary binary and compares all keys and target values before publishing the staged output. `locres-compile` accepts arbitrary compatible CSV: use the review-gated `export` workflow to generate it. It does not attest that a manually supplied CSV was reviewed. Complex plural/nested formatters require a specialized adapter before translated entries can pass the normal review gate.

## Thai fonts

```powershell
python -m pip install -e ".[fonts]"
game-localizer font-check work/project.json fonts/YourLicensedThaiFont.ttf
```

This optional check tests Unicode glyph coverage for reviewed targets. Rendering still depends on font asset selection, fallback, shaping, combining marks, line wrapping and clipping. Installing a Windows font alone does not prove that the game will use it.

## For difficult games and contributors

Read [engine support and limits](docs/ENGINES.md), [modding troubleshooting](docs/TROUBLESHOOTING.md), [context research protocol](docs/CONTEXT_RESEARCH.md), [general Thai localization guide](docs/THAI_STYLE.md) and [contributing](CONTRIBUTING.md).

There is no claim that this tool unlocks previously unmoddable games. It helps identify the failed stage and produce repeatable evidence for a new adapter. Unsupported encrypted/signed archives and proprietary formats remain explicit blockers.

## Publish to GitHub

Publish this standalone toolkit directory. Run the synthetic tests first. The release excludes game corpora, installed assets, external tools, keys, models, live projects and generated outputs. See [publishing checklist](docs/PUBLISHING.md). License: [MIT](LICENSE); licenses of games, external tools and fonts remain separate.
