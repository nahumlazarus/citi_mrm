# Claude Code Setup

## What This Repository Now Includes

- Project instructions in `CLAUDE.md`
- Shared Claude Code settings in `.claude/settings.json`
- Project subagents in `.claude/agents/`
- Python 3.7.4 compatibility rules in `.claude/rules/`

## Recommended Claude Code Setup

1. Install or update Claude Code.
2. Start Claude Code in this repository root.
3. Make sure the official marketplace is current:

```text
/plugin marketplace update claude-plugins-official
```

4. Install the required plugins if Claude Code has not already prompted you to do so:

```text
/plugin install superpowers@claude-plugins-official
/plugin install serena@claude-plugins-official
```

5. Reload plugins after installation:

```text
/reload-plugins
```

6. Confirm the session picked up the project configuration:

```text
/status
/agents
/plugin
```

## Recommended Local Python Environment

Use a local venv that is as close as possible to the target offline environment.

If Python 3.7 is installed locally:

```powershell
py -3.7 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python --version
```

If Python 3.7 is not available locally, use the Conda environment already defined in `environment.yml` and keep all code compatible with Python 3.7.4.

## Intended Agent Workflow

- Main session: orchestration, planning, design, task breakdown
- `python-implementation-worker`: focused script changes
- `validation-runner`: targeted validation and smoke checks
- `docs-maintainer`: setup and usage documentation
- `git-github-operator`: git status, commit, PR, and GitHub preparation

## Notes For This Repository

- Keep scripts runnable in an offline Conda Python 3.7.4 base environment.
- Avoid adding third-party packages that are not already part of the current project baseline.
- Favor simple, reliable scripts over heavy abstractions.
- When delegating to a low-cost subagent, provide exact file targets, concrete acceptance criteria, and the narrow validation command.