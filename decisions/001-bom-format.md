# ADR-001: BOM Format and Tooling

**Date:** 2026-03-10
**Status:** accepted
**Deciders:** Alex Wynn

## Context

We need a bill of materials format that supports version control, diffing, scripted analysis, and eventual export to spreadsheet formats for procurement. The BOM must accommodate multiple deployment sites (CBA, Vertiv, future AM) with shared and site-specific items.

## Options Considered

1. **Google Sheets** -- Familiar, collaborative. Poor version control, hard to script against reliably, no good branching story.
2. **Excel in git** -- Binary diffs are useless. Merge conflicts are unresolvable.
3. **YAML in git with Python tooling** -- Human-readable, excellent diffs, scriptable, supports comments for rationale. Requires a small upfront investment in parsing scripts.

## Decision

YAML in a git repository, with Python scripts for summary, validation, and XLSX export. Site-specific overrides in separate YAML files that reference the master BOM.

## Consequences

Need to maintain the parsing scripts, but Claude Code can handle this with minimal friction. Procurement staff who need spreadsheets get them via the export script. All changes are tracked with full history.
