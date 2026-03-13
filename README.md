# Cryo Rack System

Cryogenic rack system design and BOM for the CBA-Vertiv collaboration, with applicability to future Adiabatic Machines deployments.

## Project Goal

Design and procure a cryogenic demonstration rack using off-the-shelf components, targeting a one-month build timeline. The system provides a 4K environment suitable for AQFP processor testing and demonstration.

## Deployments

| Site              | Status  | Notes                          |
|-------------------|---------|--------------------------------|
| Vertiv            | Planned | Demo system, primary target    |
| CBA               | Planned | Independent test infrastructure|
| Adiabatic Machines| Planned |                                |

## Repository Structure

- `bom/` -- Bill of materials in machine-readable YAML, with site-specific overrides
- `decisions/` -- Architecture Decision Records (ADRs) capturing design choices and rationale
- `docs/` -- System architecture, integration notes, and project timeline
- `scripts/` -- Python tooling for BOM analysis, cost rollups, and export
- `specs/` -- Thermal budget, functional requirements, and constraints

## Quick Start

```bash
pip install -r scripts/requirements.txt
python scripts/bom_summary.py bom/bom.yaml
```

## BOM Workflow

The master BOM lives in `bom/bom.yaml`. Site-specific overrides (different cryocooler models, shielding configurations, etc.) are in `bom-cba.yaml` and `bom-vertiv.yaml`. Use the summary script to check status, flag missing quotes, and compute cost totals.
