# Context research protocol

Establish evidence sufficient to translate each scene accurately **before drafting**. A plot synopsis or character stereotype cannot resolve an individual line.

## Inputs and grouping

Start with game title, build/edition, source language, scope, available exports, screenshots/footage, glossary and style requirements. Use resource names, IDs, neighboring lines and event markers to locate scenes. Resolve missing game identity before searching; an engine name does not identify a game.

Group entries by scene, speaker or screen when evidence supports it. File order alone does not prove dialogue order. Reused strings and alternate branches may require multiple contexts.

## Source priorities

1. Direct local evidence: original resources, neighboring dialogue, event metadata and supplied screenshots/recordings.
2. Official scripts, developer material or official gameplay depicting the scene.
3. Gameplay footage of the matching scene/build, cited with timestamps; verify the spoken line and visible action.
4. Community transcripts, walkthroughs and character references where direct evidence is unavailable. Cross-check meaningful claims and note version differences.

Search using the game title, a distinctive short source phrase, verified character name, mission/chapter and build details. Do not use search snippets, unsupported fan theories or another game's translated line as evidence. Cite only what a source supports. Consult existing Thai translations for terminology after checking context/provenance; do not copy another translator's corpus.

## Scene questions

| Area | Questions |
| --- | --- |
| Identity | Which game/build, chapter/mission, branch and scene or UI screen? |
| Participants | Who speaks/hears it? One person or a group? What relationship and power dynamic? |
| Action | What happens immediately before/during the line? What triggers it? |
| Reference | What do pronouns, nicknames, objects, jokes and ambiguous words refer to? |
| Delivery | Threat, reassurance, sarcasm, routine instruction, performance or literal statement? |
| Continuity | Which neighboring lines or later payoff constrain the wording? |
| Constraints | Subtitle timing, character limits, input tokens, branches or player-variable identity? |

UI may need only screen/function evidence, without an invented speaker. Lore may require document author, recipient, period and narrative framing.

## Report format

Keep reports in `work/research/`. Map every ID to a scene dossier and preserve source hashes. This example contains placeholders, not evidence of a real scene:

```json
{
  "game": "PROJECT_GAME_TITLE",
  "build": "PROJECT_BUILD",
  "scenes": [{
    "scene_id": "chapter-01-scene-02",
    "entry_ids": ["line.001"],
    "summary": "Observed scene action",
    "speaker": "Verified speaker or unknown",
    "listener": "Verified listener or unknown",
    "relationship": "Evidence-supported relationship",
    "tone": "Evidence-supported delivery",
    "references": [{
      "type": "gameplay_video",
      "uri": "DIRECT_SOURCE_URL",
      "locator": "00:12:34–00:12:45",
      "supports": "Speaker identity and action at this line"
    }],
    "observations": ["Directly supported facts"],
    "inferences": ["Interpretations with reasoning and uncertainty"],
    "unresolved": [],
    "confidence": "high"
  }],
  "items": [{
    "id": "line.001",
    "source_sha256": "COPY_EXACT_BATCH_HASH",
    "context": {
      "scene_id": "chapter-01-scene-02",
      "string_type": "dialogue",
      "translation_readiness": "ready",
      "line_specific_notes": "Referent or branch-specific exception",
      "unresolved": []
    }
  }]
}
```

Local references use `type: local_resource`, a relative path as `uri`, and a key/line/screenshot locator. Each reference states its supported claim. Never fabricate URLs or timestamps. Transfer relevant dossier details/references into translation result `context`; scene_id alone is insufficient if reviewers cannot access its report.

## Readiness

- **Ready:** evidence resolves facts affecting meaning; state confidence and minor remaining uncertainty.
- **Pending:** identity, referent, intent or relationship could change the translation. List missing evidence and defer the line.
- **Conflicting:** sources disagree, perhaps due to build/branch differences. Resolve the conflict or keep it pending.

Confidence is an editorial assessment, not an automatic score. Without web access, inspect local evidence and state the access limitation. Never replace missing research with invented details.

The CLI generates research-first prompts and stores supplied context. It does not perform searches, authenticate citations or automatically gate translation on readiness. The reviewer checks the research before proceeding.
