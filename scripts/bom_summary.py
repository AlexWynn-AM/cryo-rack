#!/usr/bin/env python3
"""
BOM Summary Tool

Parses the cryo-rack YAML BOM and produces summary tables:
- Cost rollup by assembly
- Status breakdown
- Missing data flags (null costs, lead times, part numbers)
- Items exceeding a configurable lead time threshold

Usage:
    python bom_summary.py bom/bom.yaml
    python bom_summary.py bom/bom.yaml --max-lead-weeks 3
    python bom_summary.py bom/bom.yaml --export bom_export.xlsx
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import yaml


def load_bom(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def summarize(bom: dict, max_lead_weeks: Optional[int] = None) -> None:
    assemblies = bom.get("assemblies", [])
    total_cost = 0.0
    total_items = 0
    missing_cost = []
    missing_pn = []
    missing_lead = []
    long_lead = []
    status_counts: dict[str, int] = {}

    print(f"Project: {bom.get('project', 'unknown')}")
    print(f"Revision: {bom.get('revision', '?')}")
    print(f"Date: {bom.get('date', '?')}")
    print(f"Target build: {bom.get('target_build_date', '?')}")
    print()

    for asm in assemblies:
        asm_name = asm["name"]
        asm_cost = 0.0
        asm_items = asm.get("items", [])
        asm_missing_cost = 0

        for item in asm_items:
            total_items += 1
            part = item.get("part", "???")
            cost = item.get("unit_cost_usd")
            qty = item.get("qty") if item.get("qty") is not None else 1
            lead = item.get("lead_time_weeks")
            pn = item.get("pn")
            status = item.get("status", "unknown")

            status_counts[status] = status_counts.get(status, 0) + 1

            if cost is not None:
                line_cost = cost * qty
                asm_cost += line_cost
                total_cost += line_cost
            else:
                missing_cost.append(f"  {asm_name} / {part}")
                asm_missing_cost += 1

            if pn is None:
                missing_pn.append(f"  {asm_name} / {part}")

            if lead is None:
                missing_lead.append(f"  {asm_name} / {part}")
            elif max_lead_weeks and lead > max_lead_weeks:
                long_lead.append(f"  {asm_name} / {part}: {lead} weeks")

        cost_str = f"${asm_cost:,.0f}" if asm_missing_cost == 0 else f"${asm_cost:,.0f} (incomplete)"
        print(f"  {asm_name:<30s}  {len(asm_items):>3d} items  {cost_str}")

    print()
    print(f"Total items: {total_items}")
    print(f"Total estimated cost: ${total_cost:,.0f}" + (" (incomplete)" if missing_cost else ""))
    print()

    # Status breakdown
    print("Status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status:<20s} {count}")
    print()

    # Flags
    if missing_cost:
        print(f"Missing cost ({len(missing_cost)} items):")
        for m in missing_cost:
            print(m)
        print()

    if missing_pn:
        print(f"Missing part number ({len(missing_pn)} items):")
        for m in missing_pn:
            print(m)
        print()

    if missing_lead:
        print(f"Missing lead time ({len(missing_lead)} items):")
        for m in missing_lead:
            print(m)
        print()

    if long_lead:
        print(f"Long lead items (> {max_lead_weeks} weeks):")
        for m in long_lead:
            print(m)
        print()


def export_xlsx(bom: dict, output_path: str) -> None:
    """Export BOM to Excel for procurement teams."""
    try:
        import openpyxl
    except ImportError:
        print("ERROR: openpyxl required for XLSX export. Install with: pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BOM"

    headers = ["Assembly", "Part", "P/N", "Vendor", "Qty", "Unit Cost (USD)",
               "Line Cost (USD)", "Lead Time (wk)", "Stage", "Status", "Notes"]
    ws.append(headers)

    for asm in bom.get("assemblies", []):
        for item in asm.get("items", []):
            qty = item.get("qty") if item.get("qty") is not None else 1
            cost = item.get("unit_cost_usd")
            line_cost = cost * qty if cost else None
            notes = item.get("notes", "")
            if isinstance(notes, str):
                notes = notes.strip()

            ws.append([
                asm["name"],
                item.get("part", ""),
                item.get("pn", ""),
                item.get("vendor", ""),
                qty,
                cost,
                line_cost,
                item.get("lead_time_weeks"),
                item.get("stage", ""),
                item.get("status", ""),
                notes,
            ])

    # Auto-size columns (approximate)
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    wb.save(output_path)
    print(f"Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Summarize cryo-rack BOM")
    parser.add_argument("bom_file", help="Path to BOM YAML file")
    parser.add_argument("--max-lead-weeks", type=int, default=None,
                        help="Flag items with lead time exceeding this many weeks")
    parser.add_argument("--export", type=str, default=None,
                        help="Export BOM to XLSX at this path")
    args = parser.parse_args()

    bom = load_bom(args.bom_file)
    summarize(bom, max_lead_weeks=args.max_lead_weeks)

    if args.export:
        export_xlsx(bom, args.export)


if __name__ == "__main__":
    main()
