# Validation record for 0.1.1

Local test date: 2026-10-06, Windows, Python 3.12.14. **20 synthetic unittest cases passed**, covering CSV dialects and UTF-8 BOM/multiline strings, Unity metadata/locale preservation, Godot locale columns, JSON pointer selection, review gates, original preservation, stale/duplicate/missing IDs, hash mismatch, formatter rejection and external converter round-trip acceptance/rejection. Research-first batch prompts and project-brief acceptance/rejection are also covered.

The full synthetic CLI demo ran successfully: import → batch → apply as draft → review → export → Markdown status.

The Python wheel built successfully and installed into an isolated local target directory. Its installed module's CLI help ran successfully. The allowlisted source ZIP is separately checked for excluded binary/game/work files and runs the same synthetic test suite after extraction.

A separate private integration test used the available UnrealLocres executable against a local extracted Unreal localization resource with **10,919 entries**: export → import project → stage unchanged text → compile → independent converter re-export → compare all keys/values. The original resource was checked unchanged. This verifies this converter/resource combination and an unchanged-text round-trip, not all Unreal versions, packaging, game loading or latest translation runtime behavior. No game resource is included in the release.

CI is configured for Windows/Linux and Python 3.10/3.12. Those remote runs have not been executed during preparation; local passing tests do not imply CI has already passed. Optional fontTools glyph inspection does not establish in-game shaping or font integration.

The CLI explicitly emits UTF-8 on redirected output streams. A regression test runs the full demo under a legacy cp1252 output setting and verifies Thai output.
