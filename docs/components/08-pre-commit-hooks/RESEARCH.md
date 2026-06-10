# Component 08 - Pre-Commit Hooks (Code Hygiene) - Research

> Alternatives considered, decisions made, references.

## pre-commit framework
- Language-agnostic.
- Manages its own venvs for each hook.
- Used by ~every serious Python project (Astral, Hugging Face, FastAPI).

## detect-secrets vs git-secrets vs gitleaks
- detect-secrets is Python-based, works as a pre-commit hook, has a baseline file for known-OK matches.
- git-secrets is AWS-focused.
- gitleaks is great but requires extra config.

## Why mypy in pre-commit at all
- Catches issues before push.
- Slower hook (a few seconds) but worth it.

## References
- pre-commit: https://pre-commit.com/
- detect-secrets: https://github.com/Yelp/detect-secrets

