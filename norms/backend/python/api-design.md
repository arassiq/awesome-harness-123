+++
schema_version = 1
id = "backend.python.api_design"
version = 1
title = "Python API design scaffold"
summary = "Draft location for repository-approved Python API design requirements."
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

Replace this draft with the repository's reviewed API design requirements before activation.

## Rationale

The scaffold keeps API guidance separate from general Python, background-job, and testing norms so
only applicable guidance needs to be selected.
