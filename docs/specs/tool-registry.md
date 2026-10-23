# Canonical tool registry

The harness should own one runtime-neutral tool definition and project it into multiple interfaces:

```text
canonical registry
├── CLI command metadata
├── OpenCode custom tools
├── MCP tools and resources
├── permissions and mode bundles
├── runbook pages
└── eval fixtures
```

The registry is not an MCP document. MCP is one adapter. This prevents protocol-specific concepts from becoming permanent harness policy.

Required properties include a stable identifier, concise description, input and output schemas, side-effect classification, approval policy, output bounds, and mode membership. Large results should return a durable reference rather than being copied into model context.

See `schemas/tool-registry.schema.json` for the initial machine-readable contract.
