# Norm scaffold index

```text
backend
└── python
    ├── backend.python.api_design
    ├── backend.python.background_jobs
    └── backend.python.testing
```

- `backend.python.api_design`: API-specific authoring scaffold.
- `backend.python.background_jobs`: cron and background-job authoring scaffold.
- `backend.python.testing`: testing-specific authoring scaffold.

Generate runtime indexes from norm metadata rather than parsing this human navigation page.
This hierarchy is one authoring level, not a recursive model-facing router. Deterministic selectors
choose applicable norms; `related_to` edges do not automatically load sibling files.
