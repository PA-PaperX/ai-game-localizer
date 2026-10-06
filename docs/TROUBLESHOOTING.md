# When the mod still does not work

Diagnose one stage at a time. Percent translated and percent working in-game are different measurements.

| Symptom | Evidence to gather | Next test |
| --- | --- | --- |
| Everything remains English | Exact game build, language selection, resource path, mount/load log, extracted installed file hash | Replace one known UI key with a conspicuous synthetic marker, stage it, then verify the installed resource independently |
| Some strings change, others do not | IDs/namespaces and resource/culture for each screenshot | Find the original string in all exported resources; match ID and source hash rather than global text replacement |
| Diamonds, boxes or disappearing Thai text | Unicode target bytes, font cmap, font asset selection/fallback | `font-check`; then test real combining marks and UI clipping in-game |
| Thai appears but vowels/tones overlap | Engine shaping, font metrics, fallback and layout screenshots | Test a licensed Thai font in the actual asset route; glyph coverage alone is insufficient |
| Subtitle translation does not trigger | Speaker, scene, timing tags, DLC/season resource, exact line ID | Locate the scene's resource and preserve timing/markup; do not infer success from menu translation |
| Import succeeds, game ignores it | Exported compiled strings, correct culture/mount order and source hashes | Compare all imported targets against a fresh export and inspect the final installed archive |
| Extraction fails or produces no rows | Tool version, format/version, encryption/signature error | Stop at an unsupported-format report; use a documented compatible extractor or add a tested adapter |
| Works before a game update | Old/new build, source hashes and key-set diff | Re-import the new resource, review changed lines and rebuild against the new originals |
| Game rejects altered archive | Actual rejection log and archive format requirements | Investigate the supported loading/packaging path; no automatic key discovery or signature bypass is included |

Keep a local research folder containing inspection results, format/tool versions, source SHA256, compiler logs, an install manifest, screenshots and rollback instructions. Remove paths, usernames, keys and game text before posting a public issue.

## How to investigate a game that has no working mod yet

1. Gather read-only engine/format evidence using `inspect`, then verify with a compatible parser rather than trusting filenames.
2. Locate the localization storage and distinguish genuine text resources from textures, embedded UI assets and script-generated text.
3. Establish an unmodified extract/rebuild round-trip before translating. Verify a separate copy and never test by overwriting the only original.
4. Prove a single key replacement in the chosen culture. Record how the game loads that replacement.
5. Prove Thai rendering, shaping and clipping with a small test set.
6. Only then scale up batches and add a game-specific build/install adapter with verification and rollback.

This process helps turn an unknown failure into a repeatable engineering problem. It cannot promise a workaround for every proprietary, encrypted or signed format. A working archive technique for one game/build requires independent testing before it can be offered as an adapter for another.
