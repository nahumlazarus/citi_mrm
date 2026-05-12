---
paths:
  - "**/*.py"
  - "requirements.txt"
  - "environment.yml"
---

# Python 3.7.4 Compatibility Rules

- All code must remain compatible with the offline target environment: Conda base Python 3.7.4.
- Prefer local development with a Python 3.7 venv when available.
- Do not introduce dependencies beyond the current approved baseline unless the user explicitly approves a target-environment change.
- Prefer the standard library first.
- Keep scripts simple, stable, and easy to run without extra infrastructure.
- Avoid Python 3.8+ only syntax and typing forms.
- When changing dependency files, keep versions within Python 3.7 support bounds.
- After touching Python files, run a narrow compile or import validation step.