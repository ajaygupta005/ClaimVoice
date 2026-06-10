# Component 01 - Monorepo Foundation - Research

> Alternatives considered, decisions made, references.

## pnpm vs npm vs yarn
pnpm wins on disk usage (content-addressable store) and strict node_modules (no phantom dependencies). npm and yarn create hoisted node_modules that hide bugs.

## uv vs Poetry vs Hatch
uv is 10-100x faster than Poetry on installs, has native workspace support, and does not require env activation. Poetry was the standard but uv (by Astral, same team as Ruff) has rapidly become best-in-class.

## Turborepo vs Nx
Turbo is lighter for JS/TS-only graphs. Nx is more powerful for polyglot but has more ceremony. We have polyglot but our Python services are isolated by uv, so Turbo is enough.

## Justfile vs Makefile
Makefile tabs are error-prone; recipes break on cross-platform line endings. Just is OS-neutral, parses YAML-like syntax, ships with helpful errors. Used by HuggingFace, Astral, Vercel.

## References
- pnpm workspaces: https://pnpm.io/workspaces
- uv workspaces: https://docs.astral.sh/uv/concepts/projects/workspaces/
- Turborepo: https://turbo.build/repo/docs
- Just: https://github.com/casey/just

