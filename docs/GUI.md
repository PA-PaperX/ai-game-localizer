# GUI preview — 0.2.0

The first GUI is an offline browser application served by Python on `127.0.0.1`, with no external frontend dependencies or automatic AI calls. It is inspired by Microsoft's [NavigationView guidance](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/navigationview); it is not a native WinUI executable.

## Open it

Install Python 3.10 or newer, then `python -m pip install -e .` and run:

```powershell
game-localizer-gui --workspace work/gui
```

Alternatively, double-click `Start-GUI.cmd` in the source checkout. Leave its server console running; Ctrl+C stops it. A new local session URL is generated each launch. Reopen using that URL rather than an old bookmark. Files remain on disk after closing the server.

## Two primary pages

**Overview** shows progress and clickable resources, plus AI batch preparation. **Text** combines search, filters and editing. Context opens beside the selected text in a dialog; export is a header action. There are no separate Context, AI or Export navigation pages. “Save and next” saves changes and advances; unchanged reviewed text is not downgraded.

## Work through one scene at a time

1. **Import:** select an exported UTF-8 CSV. ID/source/target columns are detected by common names and can be corrected before import. Choose the actual engine. Unity String Table and Godot translation CSVs are supported through configurable columns. Existing translations become drafts.
2. **Text:** search English, Thai or keys; filter resource, namespace and status. View 50 entries at a time. Source text is read-only, translation text is editable. “Separate lines” displays newlines and numeric brace markers without rewriting source; those markers are only display hints, not proof of dialogue timing. Ctrl+K focuses search; Ctrl+S saves a draft. “Save and next” combines saving and advancing.
3. **Context:** record scene, speaker, listener, references and uncertainty. File neighbors help research but do not prove scene continuity. Saving context also returns a translation to draft.
4. **AI:** create a resource batch, give its research prompt and project brief to your assistant, and establish scene evidence before asking for translation. Import the original batch and result JSON. IDs, hashes and engine tokens must match; GUI-generated batches also detect later edits. Applied text remains draft. The program does not browse, verify citations or call an AI provider itself.
5. **Review:** explicitly record a reviewer and notes after checking meaning and context. GUI review requires readiness `ready` and references. This checks recorded metadata, not whether the sources actually prove the translation.
6. **Export:** download reviewed CSV. Unreviewed rows retain the original imported target or fall back to source. Other columns remain intact. Build and test game resources using an engine/game-compatible tool afterwards.

Each edit stores the previous entry in `history/`; restoring creates a draft, never an automatic approval. Batch imports save a whole-project checkpoint in `batches/<run>/before.json` (manual recovery only in this preview). Disk changes by another program block GUI writes until restart, preventing silent overwrites.

## Private Outlast pilot

This opt-in migration command copies an existing experimental translation project's exported CSVs and review records into a separate GUI workspace:

```powershell
game-localizer-gui --workspace work/outlast-gui --outlast "D:\YourPrivateTranslationProject"
```

Expected layout: `source/exports/en/*.csv`, `translations/full/<resource>.th.csv`, optional `translations/context-reviewed.json`. A matching original key and source are required. Existing reviewed statuses retain explicitly labelled legacy provenance; the importer does not claim a new review. Import is performed once per workspace. Editing the GUI copy does not update the original project or installed game automatically. Export and reconcile deliberately before the game's build process.

No real corpus, proprietary assets or game installation are included. The generic GUI and AI prompts do not assume Outlast characters, pronouns or tone.

## Current boundaries

- GUI import/export currently covers CSV. Selected JSON string leaves and optional `.locres` conversion remain CLI workflows.
- CSV uses comma separators in the dialog. The Python workspace API and CLI also accept a custom delimiter.
- Unreal validation preserves opaque backtick input/image substitutions, simple `|plural(one=...,other=...)` branch labels/order and branch tokens, and Slate closing tags. Complex/nested syntax is not a general parser and remains rejected where unsupported.
- Engine selection does not imply binary extraction, archive rebuilding, keys, signing or installation support.
- Browser session APIs require a random token, loopback host and same origin. The server does not expose arbitrary file browsing. Workspace data are still ordinary local files; keep them backed up.
- Theme is light, with Thai system fonts, visible keyboard focus and a two labelled navigation tabs. This is a preview, not a signed desktop installer.

## Validate

```powershell
python -m unittest discover -s tests -v
node --check src/game_localizer/web/app.js
```

GUI tests use synthetic text, exercise draft/review/history/export, stale edits, token preservation and HTTP session boundaries. Runtime translation quality and engine packaging require game-specific testing.
