# Cryo Rack Repo Setup Plan

Execute these steps in Claude Code to bootstrap the repository.

## Step 1: Create and initialize the repo

```bash
mkdir cryo-rack && cd cryo-rack
git init
```

If you want it on GitHub from the start:

```bash
gh repo create adiabatic-machines/cryo-rack --private --clone
cd cryo-rack
```

(Use `--private` since this will contain vendor pricing and system design details.)

## Step 2: Copy in the scaffold files

All the starter files are included alongside this plan. Copy the entire directory contents into your repo root. The structure is:

```
cryo-rack/
├── README.md
├── .gitignore
├── bom/
│   ├── bom.yaml              # Master BOM
│   ├── bom-cba.yaml          # CBA-specific overrides
│   ├── bom-vertiv.yaml       # Vertiv-specific overrides
│   └── vendors/              # Quote PDFs, correspondence
│       └── .gitkeep
├── decisions/
│   ├── template.md
│   ├── 001-bom-format.md
│   └── 002-cryocooler-selection.md
├── docs/
│   ├── system-architecture.md
│   ├── integration-notes.md
│   └── timeline.md
├── scripts/
│   ├── bom_summary.py
│   └── requirements.txt
└── specs/
    ├── thermal-budget.md
    └── requirements.md
```

## Step 3: Install script dependencies

```bash
pip install -r scripts/requirements.txt
```

## Step 4: Verify the BOM tooling works

```bash
python scripts/bom_summary.py bom/bom.yaml
```

This should parse the starter BOM and print a summary table with cost and status rollups.

## Step 5: Start filling in the BOM

The master `bom/bom.yaml` has placeholder entries organized by subsystem. Work through each assembly, filling in part numbers, vendors, costs, and lead times as you get quotes. Use Claude Code to help you add entries, run the summary script, and flag gaps.

## Step 6: Record decisions as you make them

When you choose a specific cryocooler, shielding approach, or wiring scheme, create a decision record in `decisions/` using the template. Even a few sentences is fine. The point is traceability.

## Day-to-day workflow with Claude Code

Typical commands you'll issue:

- "Add a line item to the cryocooler assembly for the compressor water chiller"
- "Run the BOM summary and show me what's still missing quotes"
- "Create a decision record for why we chose the RDK-101D over the PT410"
- "Export the BOM to xlsx for the Vertiv procurement team"
- "What's our total estimated heat load at the 4K stage?"
- "Show me all items with lead time over 3 weeks"

Claude Code can read the YAML, modify it, run the scripts, and generate new documents directly.
