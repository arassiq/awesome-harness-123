+++
schema_version = 1
id = "backend.python.testing"
version = 1
title = "Python backend testing scaffold"
summary = "Draft location for repository-approved Python backend testing requirements."
status = "draft"
priority = "advisory"
delivery = "scoped"

[scope]
areas = ["backend"]
languages = ["python"]
paths = ["**/*.py"]
tasks = ["testing", "review"]

[[relations]]
type = "related_to"
target = "backend.python.api_design"

[[relations]]
type = "related_to"
target = "backend.python.background_jobs"

[provenance]
kind = "repository"
source = "docs/specs/norm-library.md"
owner = "project-maintainers"
+++

## Rule

Replace this draft with the repository's reviewed Python backend testing requirements before
activation.

## Rationale

Testing guidance is modeled independently so implementation and review tasks can request it without
loading API or background-job details by default.
