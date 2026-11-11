# Documentation Maintenance Guidelines

Follow these 7 mandatory rules across the entire project lifecycle:

1. **Sync on Completion**: Update relevant `docs/` and `agents/` files whenever a phase, feature, or refactor is completed.
2. **Record Decisions**: Log every non-obvious technical or architectural choice in [`docs/technical-decisions.md`](../docs/technical-decisions.md) and [`agents/decision-log.md`](decision-log.md).
3. **Keep Roadmaps Accurate**: Keep [`docs/implementation-plan.md`](../docs/implementation-plan.md) and [`docs/implementation-results.md`](../docs/implementation-results.md) aligned with actual repository state.
4. **Document Discoveries**: Record newly discovered dataset anomalies, dependency constraints, or runtime caveats in [`docs/known-issues.md`](../docs/known-issues.md) and [`agents/troubleshooting.md`](troubleshooting.md).
5. **No Unverified Claims**: Never present planned functionality, guesses, or unrun benchmarks as implemented facts. Use explicit `Implemented`, `Prototype`, or `Planned` tags.
6. **Single Source of Truth**: Avoid copy-pasting long tables or specifications across multiple markdown files; cross-reference the canonical file instead.
7. **Zero Secrets**: Never write credentials, API keys, tokens, or private infrastructure secrets into any markdown file.
