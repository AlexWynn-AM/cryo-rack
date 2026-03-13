#!/usr/bin/env python3
"""
Build PDF design package from markdown source + BOM YAML.

Reads docs/vertiv-design-package.md, injects BOM tables from bom/bom.yaml,
optionally renders Mermaid diagrams, and produces a styled PDF.

Usage:
    .venv/bin/python scripts/build_pdf.py              # default output
    .venv/bin/python scripts/build_pdf.py -o out.pdf   # custom filename
    .venv/bin/python scripts/build_pdf.py --html-only  # HTML only (no PDF deps)

Setup (one time):
    python3 -m venv .venv
    .venv/bin/pip install markdown pyyaml weasyprint

    For Mermaid diagram rendering (optional):
        npm install -g @mermaid-js/mermaid-cli
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

try:
    import markdown as md_lib
except ImportError:
    sys.exit("ERROR: 'markdown' package required. Install with: pip install markdown")

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = REPO_ROOT / "docs" / "vertiv-design-package.md"
BOM_PATH = REPO_ROOT / "bom" / "bom.yaml"
CSS_PATH = Path(__file__).resolve().parent / "style.css"


def load_bom() -> dict:
    with open(BOM_PATH) as f:
        return yaml.safe_load(f)


def generate_bom_markdown(bom: dict) -> str:
    """Generate BOM tables in markdown from the YAML source."""
    lines: list[str] = []
    grand_total = 0.0
    assembly_summaries = []

    for asm in bom.get("assemblies", []):
        name = asm["name"]
        items = asm.get("items", [])
        asm_cost = 0.0
        active_count = 0
        for item in items:
            qty = item.get("qty") if item.get("qty") is not None else 1
            if qty == 0:
                continue
            active_count += 1
            cost = item.get("unit_cost_usd")
            if cost is not None:
                asm_cost += cost * qty
        assembly_summaries.append((name, active_count, asm_cost))
        grand_total += asm_cost

    lines.append("### Cost summary\n")
    lines.append("| Assembly | Items | Est. Cost |")
    lines.append("|---|---:|---:|")
    for name, count, cost in assembly_summaries:
        lines.append(f"| {name} | {count} | ${cost:,.0f} |")
    lines.append(f"| **Total** | | **${grand_total:,.0f}** |")
    lines.append("")

    for asm in bom.get("assemblies", []):
        name = asm["name"]
        items = asm.get("items", [])
        active = [i for i in items
                  if (i.get("qty") if i.get("qty") is not None else 1) > 0]
        if not active:
            continue

        lines.append(f"### {name}\n")
        lines.append("| Part | Vendor | Qty | Unit Cost | Lead (wk) | Status |")
        lines.append("|---|---|---:|---:|---:|---|")
        for item in active:
            part = item.get("part", "")
            vendor = item.get("vendor", "") or ""
            qty = item.get("qty") if item.get("qty") is not None else 1
            cost = item.get("unit_cost_usd")
            cost_s = f"${cost:,.0f}" if cost is not None else "TBD"
            lead = item.get("lead_time_weeks")
            lead_s = str(lead) if lead is not None else "TBD"
            status = item.get("status", "")
            lines.append(f"| {part} | {vendor} | {qty} | {cost_s} | {lead_s} | {status} |")
        lines.append("")

    return "\n".join(lines)


def _find_mmdc() -> list[str] | None:
    """Locate mmdc binary — global install or local npx."""
    path = shutil.which("mmdc")
    if path:
        return [path]
    npx = shutil.which("npx")
    if npx:
        r = subprocess.run([npx, "mmdc", "--version"], capture_output=True, timeout=10)
        if r.returncode == 0:
            return [npx, "mmdc"]
    return None


def render_mermaid_blocks(html: str, tmp_dir: Path) -> str:
    """Find <code class='language-mermaid'> blocks, render to PNG via mmdc."""
    mmdc_cmd = _find_mmdc()
    if not mmdc_cmd:
        print("INFO: mmdc not found — Mermaid diagrams kept as code blocks.")
        print("      Install with: npm install @mermaid-js/mermaid-cli")
        return html

    pattern = re.compile(
        r"<pre><code class=\"language-mermaid\">(.*?)</code></pre>",
        re.DOTALL,
    )
    counter = 0

    def _replace(match: re.Match) -> str:
        nonlocal counter
        counter += 1
        mmd_text = match.group(1)
        # Unescape HTML entities that markdown may have introduced
        for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                             ("&quot;", '"'), ("&#x27;", "'")]:
            mmd_text = mmd_text.replace(entity, char)

        mmd_file = tmp_dir / f"diagram_{counter}.mmd"
        png_file = tmp_dir / f"diagram_{counter}.png"
        mmd_file.write_text(mmd_text)

        result = subprocess.run(
            [*mmdc_cmd, "-i", str(mmd_file), "-o", str(png_file),
             "-b", "white", "-w", "800", "-s", "2"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and png_file.exists():
            return f'<img src="{png_file}" alt="Diagram {counter}" />'
        print(f"WARNING: Failed to render diagram {counter}: {result.stderr[:200]}")
        return match.group(0)

    rendered = pattern.sub(_replace, html)
    if counter:
        print(f"Rendered {counter} Mermaid diagram(s).")
    return rendered


def build_title_html(bom: dict) -> str:
    rev = bom.get("revision", "?")
    return f"""
<div class="title-block">
    <h1>AQFP Cryogenic Rack</h1>
    <div class="subtitle">Design Package</div>
    <div class="subtitle">Revision {rev} &mdash; {date.today().strftime("%B %Y")}</div>
    <div class="meta">
        Prepared for deployment at Vertiv, CBA, and AM
    </div>
</div>
"""


def markdown_to_html(md_text: str) -> str:
    extensions = ["tables", "fenced_code", "toc", "smarty", "sane_lists"]
    return md_lib.markdown(md_text, extensions=extensions)


def build(output: Path, html_only: bool = False) -> None:
    if not DOC_PATH.exists():
        sys.exit(f"ERROR: Source not found: {DOC_PATH}")
    if not BOM_PATH.exists():
        sys.exit(f"ERROR: BOM not found: {BOM_PATH}")

    print(f"Reading {DOC_PATH.name} ...")
    md_text = DOC_PATH.read_text()

    # Strip YAML front matter
    if md_text.startswith("---"):
        end = md_text.find("---", 3)
        if end != -1:
            md_text = md_text[end + 3:].lstrip("\n")

    # Strip the top-level title + revision line (title page replaces it)
    md_text = re.sub(
        r"^#\s+AQFP Cryogenic\s+(?:Test\s+)?Rack.*?\n\n\*\*Revision.*?\*\*\n+---\n*",
        "", md_text, count=1, flags=re.DOTALL,
    )

    print(f"Reading {BOM_PATH.name} ...")
    bom = load_bom()
    bom_md = generate_bom_markdown(bom)

    md_text = md_text.replace("<!-- BOM_TABLES -->", bom_md)

    print("Converting markdown to HTML ...")
    body_html = markdown_to_html(md_text)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        body_html = render_mermaid_blocks(body_html, tmp_dir)

        css_text = CSS_PATH.read_text() if CSS_PATH.exists() else ""
        title_html = build_title_html(bom)

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <title>AQFP Cryo Rack — Design Package</title>
    <style>{css_text}</style>
</head>
<body>
{title_html}
{body_html}
</body>
</html>"""

        html_out = output.with_suffix(".html")
        html_out.write_text(full_html)
        print(f"HTML written to {html_out}")

        if html_only:
            return

        try:
            from weasyprint import HTML as WPHTML
        except ImportError:
            print("\nWeasyprint not installed — HTML generated but PDF skipped.")
            print("Install with: pip install weasyprint")
            print("macOS also needs: brew install pango")
            return

        print("Generating PDF ...")
        WPHTML(filename=str(html_out)).write_pdf(str(output))
        print(f"PDF written to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Cryo Rack design package PDF"
    )
    parser.add_argument(
        "-o", "--output", type=str,
        default=str(REPO_ROOT / "docs" / "cryo-rack-design-package.pdf"),
        help="Output PDF path (default: docs/cryo-rack-design-package.pdf)",
    )
    parser.add_argument(
        "--html-only", action="store_true",
        help="Generate HTML only (no weasyprint dependency needed)",
    )
    args = parser.parse_args()
    build(Path(args.output), html_only=args.html_only)


if __name__ == "__main__":
    main()
