# GUI QA — 0.2.1

Verified on 2026-10-06 in a local browser. Write operations used an isolated synthetic workspace with 60 CSV rows, placeholders, subtitle markers and an extra metadata column. The private pilot was used only for read-only layout verification. No installed-game files were changed.

| Area | Verification |
| --- | --- |
| Overview / Text | Switch pages, open a resource, continue draft work; only two primary tabs remain |
| List | Independent scrolling, End reaches last loaded row, fixed heading/footer, next/previous page, 50 rows per page |
| Filters | Resource, namespace/group, reviewed status, Thai search, no-results state and reset |
| Editor | Save draft, save-and-next, placeholder rejection, split numeric brace markers without changing source |
| Context / review | Save evidence and readiness; refuse review without context; explicit review succeeds |
| History | Restore an old value as draft |
| AI | Create/download batch, copy research prompt, reject malformed results, apply valid drafts, reject stale batch; invalid size followed by success replaces modal feedback |
| Export | Download CSV; 60 rows, reviewed target included, unreviewed source fallback and extra metadata preserved |
| Unsaved edits | Cancel keeps target; discard permits navigation; Escape in changed context opens confirmation; cancel keeps context; discard closes it |
| Keyboard | Ctrl+K focuses search; list receives scrolling keys; visible focus styles |
| Responsive | Desktop 1280×720, narrow 760×720, mobile 390×844; no horizontal document overflow; list pagination accessible |
| Console | No captured warning/error messages during completed QA |

Automated validation: all 32 Python tests pass; JavaScript passes `node --check`. 21st local review reports informational hardcoded-color findings, not blocking defects. Catalog inspiration search requires sign-in, so public professional guidance was used directly.

The browser tool did not receive a download event despite successful files on disk; exported JSON and CSV were inspected separately. An old native confirmation interrupted testing temporarily; after dismissal, the new in-app unsaved dialog was verified. This is manual QA, not a committed browser automation suite. These checks do not certify translation accuracy, game packaging, every browser, or every engine.

To repeat: launch with a new workspace, import synthetic CSV, perform the checks above, inspect exported data, and keep the real project separate.
