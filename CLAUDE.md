# Citi MRM Claude Code Guide

## Operating Model

- The main Claude Code session is the orchestrator for this repository.
- Use a strong main-session model for planning and design. This project pins the default Claude Code model to `claude-opus-4-7` in `.claude/settings.json`.
- Keep planning, design decisions, and task decomposition in the main session.
- Delegate implementation, validation, documentation, and git or GitHub work to subagents so the main context stays clean.
- When delegating to a simpler subagent, provide a complete brief:
  - exact files or directories to inspect
  - the specific change to make or check to run
  - acceptance criteria
  - the narrow validation command to run
  - the expected return format
- Do not ask low-context subagents to infer broad repository intent from scratch.

## Preferred Delegation

- Use the built-in `Explore` subagent for read-only discovery.
- Use `repo-bootstrap-operator` for Claude Code setup, local environment setup, `.gitignore` hygiene, and local git initialization before GitHub is configured.
- Use `python-implementation-worker` for Python script changes and focused refactors.
- Use `validation-runner` for tests, import checks, and compile checks.
- Use `docs-maintainer` for setup notes, usage docs, and change explanations.
- Use `git-github-operator` for git hygiene, commit preparation, PR text, and GitHub follow-up.

## Plugin Expectations

- This project expects these plugins at minimum:
  - `superpowers@claude-plugins-official`
  - `serena@claude-plugins-official`
- Prefer Serena when symbol-aware navigation, reference lookup, or precise refactoring is helpful.
- Prefer Superpowers when structured brainstorming, plan execution, debugging discipline, or code review adds value.
- If a plugin is unavailable in the current session, continue with built-in tools rather than blocking work.

## Python Runtime Contract

- The target deployment environment is an offline Conda base environment running Python 3.7.4.
- Local development should use a project venv based on Python 3.7 when possible.
- If the exact interpreter is not available locally, keep all code and dependencies compatible with Python 3.7.4.
- Do not introduce new third-party packages unless they are already available in the target baseline.
- Prefer the standard library first.
- The approved external packages already used in this repository are:
  - `pandas`
  - `numpy`
  - `matplotlib`
  - `scikit-learn`
  - `tqdm`

## Python Style Priorities

- Favor simple, reliable scripts over clever abstractions.
- Keep functions small and explicit.
- Prefer deterministic file handling and explicit path logic.
- Reuse existing logging patterns instead of adding new frameworks.
- Preserve compatibility with Python 3.7 syntax and typing.
- Avoid Python 3.8+ only features such as:
  - assignment expressions
  - structural pattern matching
  - `list[str]` and other built-in generic type syntax
  - `X | Y` union syntax
  - `typing.Self`

## Validation Expectations

- After changing Python files, run the narrowest relevant validation before widening scope.
- If no targeted test exists, use a narrow import or compile check for the touched files.
- Do not add dependency-heavy tooling just to validate a small script change.
- If behavior or output contracts change, update the relevant project documentation in the same task.

## Repository Notes

- This repository contains small MRM utility scripts in the project root rather than a package layout.
- Existing documentation files describe script purpose, environment assumptions, and usage patterns.
- Maintain that lightweight structure unless there is a strong reason to change it.