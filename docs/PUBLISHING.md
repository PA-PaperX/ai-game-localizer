# Publishing this toolkit

Publish only the `ai-game-localizer` directory. It is a standalone Python package with no dependency on any game's working project.

Before uploading:

1. Run `python -m unittest discover -s tests -v` and `python examples/demo.py` after installation.
2. Run `python scripts/package_release.py`. It creates an allowlisted source ZIP under `dist/` and prints its SHA256. Upload that archive's contents or the clean source directory.
3. Inspect `git status` before committing. Do not force-add ignored work/, staging/, dist/, assets, archives, external executables, keys or models.
4. State 0.1.1 limitations and tested versions in your release description. The CLI is a text translation workflow, not a universal mod installer.

Suggested first release title: `v0.1.1 — AI translation batches, review gates and exported-resource adapters`.

On a copied clean folder, these commands create a new local Git repository. Set your own repository URL before pushing:

```powershell
git init
git add README.md AGENTS.md CONTRIBUTING.md LICENSE pyproject.toml .gitignore .github src tests examples docs scripts
git commit -m "Initial AI game localization toolkit"
# Create your GitHub repository, add its remote, then push when ready.
```

No GitHub publication, repository creation or account action is performed by the package builder.
