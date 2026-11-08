+++
schema_version = 1
id = "backend.python.background_jobs"
version = 1
title = "Python background-job scaffold"
summary = "Draft location for repository-approved cron and background-job requirements."
status = "draft"
priority = "advisory"
delivery = "scoped"

[scope]
areas = ["backend"]
languages = ["python"]
paths = ["**/*.py"]
tasks = ["implementation", "review"]

[[relations]]
type = "related_to"
target = "backend.python.testing"

[provenance]
kind = "repository"
source = "docs/specs/norm-library.md"
owner = "project-maintainers"
+++

## Rule

Replace this draft with the repository's reviewed cron and background-job requirements before
activation.

## Rationale

Background execution has concerns distinct from request-driven APIs. A separate norm prevents those
details from being injected into unrelated Python work.
