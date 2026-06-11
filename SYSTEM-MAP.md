# System Map

This document is the local orientation and signposting map for the repositories and runtimes that are easiest to confuse.

## Canonical Map

| Name | Machine | Path | Role | Editable | Runtime-authoritative |
| --- | --- | --- | --- | --- | --- |
| CCE Lite code | Black Air | `/Volumes/kevinmattice/cce` | Source checkout | Yes | Yes |
| CCE Lite runtime | Colossus | `/Users/kevinmattice/cce` | Runtime checkout | Cautious | Yes |
| PEM source | Black Air | `/Users/kevinmattice/dev/anon/pem-mcp` | Source checkout | Yes | Source only |
| PEM runtime | Colossus | `/Users/kevinmattice/pem-mcp` | Runtime checkout | Cautious | Yes |
| Cognitive Environment Atlas | Black Air | `/Users/kevinmattice/cognitive-environment` | Vault / notes / Tolaria surface | Yes | No |

## Repo Identity Rules

- Treat `/Users/kevinmattice/cognitive-environment` as the atlas and notes surface, not the live CCE Lite runtime checkout.
- Do not diagnose live CCE Lite runtime behavior from this tree unless you are explicitly inspecting historical notes or committed Git history.
- Do not assume a canonical path is mounted. Prove the actual accessible path before making changes.

## Agent Preflight

Run this before touching CCE or PEM:

1. `pwd`
2. `git rev-parse --show-toplevel`
3. `git remote -v`
4. `git status --short`
5. `git log -1 --oneline`
6. `ls` expected key files or directories
7. `./whereami` if the repo provides it

Expected key paths:

- CCE Lite: `gateway/`, `models/`, `workspace_runtime/`, `tests/`
- PEM source: project-specific runtime/source files
- Cognitive environment vault: `AGENTS.md`, `types/`, `entities/`, `views/`

## Do Not Proceed Unless

Do not proceed unless all of the following are true:

- the current path matches the intended target or an explicitly approved equivalent
- the repo identity matches the requested task
- the expected key files are present in the working tree
- the tree is authoritative for the requested diagnosis or edit

If any check fails, stop and report the mismatch before editing.

## Common Confusions

- The cognitive-environment vault may contain useful notes and Git history, but that does not make it the live CCE Lite checkout.
- Runtime paths and source paths may differ across Black Air and Colossus.
- Code that exists in Git history is not the same thing as code that exists in the current working tree.
