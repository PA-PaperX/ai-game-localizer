# Engine support, with evidence

Engine labels select project metadata; 0.1.1 uses shared CSV/JSON text adapters. They do not switch on a universal binary extractor. `inspect` reports filename candidates, examines no binary payloads and may report more than one engine.

| Engine | Input supported here | Needed outside this tool | Current blocker |
| --- | --- | --- | --- |
| Unreal | UnrealLocres CSV and external tool bridge | Compatible extraction, correct localization target/culture, build/pack/install | PAK/IoStore version, signing/encryption, game loading behavior, font assets |
| Unity | Exported Localization String Table CSV | Unity project import, or resource-aware mod tooling for that particular shipped game | Custom localization tables, serialized assets, bundles, IL2CPP/Mono differences |
| Godot | Exported translation CSV or selected locale JSON | Translation import/registration and project/game-compatible packaging | Shipped PCK access and remap/imported resource paths |
| Ren'Py | CSV/JSON exported by another tool | Native script/translation workflow | `.rpy`, `.rpyc`, `.rpa` are detected but not parsed |
| RPG Maker | Explicitly selected locale JSON strings | Event-aware extraction, reinsertion and packaging | Event arrays contain code/IDs as well as dialogue; no automatic whole-game translation |
| GameMaker/custom | Exported CSV/JSON only | Format-specific parser and packing | `data.win` is detected but not parsed |

## Why exported text is a useful boundary

Unreal's official localization workflow uses localization resources and compilation/staging. A shipped game's resource loading still needs independent investigation. See [Epic localization overview](https://dev.epicgames.com/documentation/unreal-engine/localization-overview-for-unreal-engine).

Unity Localization exports String Table Collections as CSV, with Key, Id and locale columns and optional comments. Column names may differ; configure them explicitly. See [Unity CSV import/export](https://docs.unity3d.com/Packages/com.unity.localization@1.5/manual/CSV.html).

Godot supports CSV-based translation imports and localization registration. That project workflow does not guarantee that an arbitrary shipped game accepts a loose replacement file. See [Godot internationalization](https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html).

The optional `.locres` bridge targets [akintos/UnrealLocres](https://github.com/akintos/UnrealLocres). Supply an executable you have independently checked and record its version/hash. Third-party tools are not covered by this project's MIT license.

## New adapter acceptance

Document the exact format and tested versions. Add synthetic fixtures covering Unicode, empty text, duplicate IDs, missing keys, tokenized dialogue and additional locales/metadata. Verify source preservation, deterministic output and parser round-trip. Demonstrate a game-specific staging and runtime test separately before claiming mod support. Provide actionable errors for unknown versions; never interpret an encrypted blob as an empty translation table.
