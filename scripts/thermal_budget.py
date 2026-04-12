#!/usr/bin/env python3
"""
Cryogenic Thermal Budget Calculator

Computes heat loads for each subsystem of the cryo-rack demo system and
compares totals against the Sumitomo RDK-101D cryocooler capacity.

All inputs are loaded from data/thermal_inputs.yaml — no hardcoded
physical constants or geometry in this script.

Usage:
    python scripts/thermal_budget.py
    python scripts/thermal_budget.py --inputs data/thermal_inputs.yaml
    python scripts/thermal_budget.py --plot         # Include pie chart
    python scripts/thermal_budget.py --json         # Machine-readable output

References:
    - docs/thermal-budget.md (hand calculations for validation)
    - decisions/002-cryocooler-selection.md
    - decisions/004-ground-isolation.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class HeatLoad:
    """A single heat load contribution."""
    name: str
    subsystem: str       # category: wiring_dc, wiring_rf, radiation, etc.
    stage: str           # "1st" or "2nd" — which cryocooler stage absorbs it
    load_w: float
    details: str = ""

    @property
    def load_mw(self) -> float:
        return self.load_w * 1e3


@dataclass
class ThermalBudget:
    """Complete thermal budget result."""
    loads: list[HeatLoad] = field(default_factory=list)
    cryocooler_model: str = ""
    stage_capacities: dict[str, float] = field(default_factory=dict)
    # stage name -> capacity in watts

    def add(self, load: HeatLoad) -> None:
        self.loads.append(load)

    def total_by_stage(self, stage: str) -> float:
        return sum(h.load_w for h in self.loads if h.stage == stage)

    def loads_by_stage(self, stage: str) -> list[HeatLoad]:
        return [h for h in self.loads if h.stage == stage]

    def margin_fraction(self, stage: str) -> float:
        cap = self.stage_capacities.get(stage, 0.0)
        if cap <= 0:
            return 0.0
        return 1.0 - self.total_by_stage(stage) / cap

    def utilization_fraction(self, stage: str) -> float:
        cap = self.stage_capacities.get(stage, 0.0)
        if cap <= 0:
            return float("inf")
        return self.total_by_stage(stage) / cap


# ---------------------------------------------------------------------------
# Physics helpers
# ---------------------------------------------------------------------------

def thermal_conductivity_integral(
    material_data: dict[str, Any],
    t_cold_k: float,
    t_hot_k: float,
) -> float:
    """
    Compute the thermal conductivity integral from t_cold to t_hot
    using the tabulated cumulative integrals (0->T) in material_data.

    Returns the integral in W/m (i.e., integral of k(T) dT from T_cold to T_hot).

    The table maps temperature (K) -> cumulative integral from 0 K (W/m).
    We interpolate linearly between tabulated points.
    """
    table = material_data["conductivity_integral"]
    # Convert keys to float and sort
    points = sorted((float(t), float(v)) for t, v in table.items())

    def interp(t: float) -> float:
        if t <= points[0][0]:
            return points[0][1] * (t / points[0][0]) if points[0][0] > 0 else 0.0
        if t >= points[-1][0]:
            return points[-1][1]
        for i in range(len(points) - 1):
            t0, v0 = points[i]
            t1, v1 = points[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / (t1 - t0)
                return v0 + frac * (v1 - v0)
        return points[-1][1]

    return interp(t_hot_k) - interp(t_cold_k)


def conduction_heat_load(
    material_data: dict[str, Any],
    cross_section_m2: float,
    length_m: float,
    t_cold_k: float,
    t_hot_k: float,
) -> float:
    """
    Compute conduction heat load: Q = (A/L) * integral(k(T), T_cold, T_hot).

    Returns heat load in watts.
    """
    integral = thermal_conductivity_integral(material_data, t_cold_k, t_hot_k)
    return (cross_section_m2 / length_m) * integral


def radiation_heat_load(
    sigma: float,
    emissivity: float,
    area_m2: float,
    t_hot_k: float,
    t_cold_k: float,
) -> float:
    """
    Compute radiation heat load: Q = eps * sigma * A * (T_h^4 - T_c^4).

    Returns heat load in watts.
    """
    return emissivity * sigma * area_m2 * (t_hot_k**4 - t_cold_k**4)


# ---------------------------------------------------------------------------
# Budget computation
# ---------------------------------------------------------------------------

def compute_budget(inputs: dict[str, Any]) -> ThermalBudget:
    """Compute the full thermal budget from YAML inputs."""
    budget = ThermalBudget()
    materials = inputs["materials"]
    temps = inputs["temperatures"]

    # Cryocooler
    cryo = inputs["cryocooler"]
    budget.cryocooler_model = cryo["model"]
    for stage in cryo["stages"]:
        budget.stage_capacities[stage["name"]] = stage["capacity_w"]

    # Helper: determine which cryocooler stage absorbs a load
    def stage_for_interval(t_cold_k: float) -> str:
        """Map the cold-side temperature of a conduction path to a stage."""
        if t_cold_k <= temps["second_stage"] + 1.0:
            return "2nd stage"
        return "1st stage"

    # --- DC Wiring ---
    dc = inputs["dc_wiring"]
    mat = materials[dc["material"]]
    n_wires = dc["count"]
    a_wire = dc["wire_cross_section_m2"]
    for seg in dc["segments"]:
        q_one = conduction_heat_load(
            mat, a_wire, seg["length_m"], seg["t_cold_k"], seg["t_hot_k"]
        )
        q_total = n_wires * q_one
        stage = stage_for_interval(seg["t_cold_k"])
        budget.add(HeatLoad(
            name=f"DC wiring: {seg['name']}",
            subsystem="wiring_dc",
            stage=stage,
            load_w=q_total,
            details=(
                f"{n_wires}x {dc['material']} 36AWG, "
                f"A={a_wire:.2e} m^2, L={seg['length_m']} m, "
                f"{seg['t_hot_k']:.0f}K->{seg['t_cold_k']:.0f}K"
            ),
        ))

    # --- RF Coax ---
    rf = inputs["rf_coax"]
    mat = materials[rf["material"]]
    n_coax = rf["count"]
    a_coax = rf["cable_cross_section_m2"]
    for seg in rf["segments"]:
        q_one = conduction_heat_load(
            mat, a_coax, seg["length_m"], seg["t_cold_k"], seg["t_hot_k"]
        )
        q_total = n_coax * q_one
        stage = stage_for_interval(seg["t_cold_k"])
        budget.add(HeatLoad(
            name=f"RF coax: {seg['name']}",
            subsystem="wiring_rf",
            stage=stage,
            load_w=q_total,
            details=(
                f"{n_coax}x SS304 0.086\" coax, "
                f"A={a_coax:.2e} m^2, L={seg['length_m']} m, "
                f"{seg['t_hot_k']:.0f}K->{seg['t_cold_k']:.0f}K"
            ),
        ))

    # --- Radiation ---
    sigma = inputs["radiation"]["stefan_boltzmann_constant"]
    for rad in inputs["radiation"]["loads"]:
        if rad.get("use_mli"):
            q = rad["mli_heat_flux_w_per_m2"] * rad["area_m2"]
            detail_str = (
                f"MLI flux={rad['mli_heat_flux_w_per_m2']} W/m^2, "
                f"A={rad['area_m2']} m^2"
            )
        else:
            q = radiation_heat_load(
                sigma, rad["emissivity"], rad["area_m2"],
                rad["t_hot_k"], rad["t_cold_k"],
            )
            detail_str = (
                f"eps={rad['emissivity']}, A={rad['area_m2']} m^2, "
                f"{rad['t_hot_k']:.0f}K->{rad['t_cold_k']:.0f}K"
            )
        stage = stage_for_interval(rad["t_cold_k"])
        budget.add(HeatLoad(
            name=f"Radiation: {rad['name']}",
            subsystem="radiation",
            stage=stage,
            load_w=q,
            details=detail_str,
        ))

    # --- Mechanical supports ---
    mech = inputs["mechanical_supports"]
    for item in mech["items"]:
        mat = materials[mech["material"]]
        q_one = conduction_heat_load(
            mat, item["cross_section_m2"], item["length_m"],
            item["t_cold_k"], item["t_hot_k"],
        )
        q_total = item["count"] * q_one
        stage = stage_for_interval(item["t_cold_k"])
        budget.add(HeatLoad(
            name=f"Mech support: {item['name']}",
            subsystem="mechanical",
            stage=stage,
            load_w=q_total,
            details=(
                f"{item['count']}x SS304, "
                f"A={item['cross_section_m2']:.2e} m^2, "
                f"L={item['length_m']} m, "
                f"{item['t_hot_k']:.0f}K->{item['t_cold_k']:.0f}K"
            ),
        ))

    # --- Ground isolation disk (alumina) ---
    gi = inputs["ground_isolation"]
    mat = materials[gi["material"]]
    area = math.pi * (gi["diameter_m"] / 2.0) ** 2
    q = conduction_heat_load(
        mat, area, gi["thickness_m"], gi["t_cold_k"], gi["t_hot_k"],
    )
    stage = stage_for_interval(gi["t_cold_k"])
    budget.add(HeatLoad(
        name="Ground isolation: alumina disk",
        subsystem="ground_isolation",
        stage=stage,
        load_w=q,
        details=(
            f"Alumina {gi['diameter_m']*1e3:.0f}mm dia x "
            f"{gi['thickness_m']*1e3:.0f}mm thick, "
            f"{gi['t_hot_k']:.0f}K->{gi['t_cold_k']:.0f}K"
        ),
    ))

    # --- Optical I/O ---
    opt = inputs.get("optical_io", {})
    if opt.get("enabled", False):
        n_fibers = opt["fiber_count"]
        p_optical = opt["optical_power_per_fiber_w"]
        abs_frac = opt["absorption_fraction"]
        q_absorbed = n_fibers * p_optical * abs_frac
        budget.add(HeatLoad(
            name="Optical I/O: absorbed power at 4K",
            subsystem="optical_io",
            stage="2nd stage",
            load_w=q_absorbed,
            details=(
                f"{n_fibers} fibers x {p_optical*1e3:.1f} mW x "
                f"{abs_frac:.0%} absorption"
            ),
        ))
        q_fiber_cond = n_fibers * opt.get("fiber_conduction_per_fiber_w", 0.0)
        if q_fiber_cond > 0:
            budget.add(HeatLoad(
                name="Optical I/O: fiber conduction",
                subsystem="optical_io",
                stage="2nd stage",
                load_w=q_fiber_cond,
                details=f"{n_fibers} fibers conduction",
            ))

    # --- DUT dissipation ---
    dut = inputs.get("dut", {})
    dut_power = dut.get("power_w", 0.0)
    if dut_power > 0:
        budget.add(HeatLoad(
            name="DUT dissipation",
            subsystem="dut",
            stage="2nd stage",
            load_w=dut_power,
            details=dut.get("notes", ""),
        ))

    return budget


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_report(budget: ThermalBudget) -> str:
    """Format the thermal budget as a human-readable text report."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("CRYOGENIC THERMAL BUDGET REPORT")
    lines.append(f"Cryocooler: {budget.cryocooler_model}")
    lines.append("=" * 72)

    for stage_name in ["1st stage", "2nd stage"]:
        cap = budget.stage_capacities.get(stage_name, 0.0)
        total = budget.total_by_stage(stage_name)
        util = budget.utilization_fraction(stage_name)
        margin = budget.margin_fraction(stage_name)
        stage_loads = budget.loads_by_stage(stage_name)

        lines.append("")
        lines.append(f"--- {stage_name.upper()} ---")
        lines.append(f"Capacity: {cap*1e3:.1f} mW")
        lines.append("")

        if not stage_loads:
            lines.append("  (no heat loads)")
        else:
            # Header
            lines.append(f"  {'Source':<45s}  {'Load (mW)':>10s}  {'% of cap':>8s}")
            lines.append(f"  {'-'*45}  {'-'*10}  {'-'*8}")
            for h in stage_loads:
                pct = (h.load_w / cap * 100) if cap > 0 else float("inf")
                lines.append(
                    f"  {h.name:<45s}  {h.load_mw:>10.3f}  {pct:>7.1f}%"
                )
            lines.append(f"  {'-'*45}  {'-'*10}  {'-'*8}")
            lines.append(
                f"  {'TOTAL':<45s}  {total*1e3:>10.3f}  {util*100:>7.1f}%"
            )

        lines.append("")
        lines.append(f"  Utilization: {util*100:.1f}%")
        lines.append(f"  Margin:      {margin*100:.1f}%")

        if util > 1.0:
            lines.append("  *** WARNING: HEAT LOAD EXCEEDS CAPACITY ***")
        elif util > 0.7:
            lines.append("  ** CAUTION: utilization above 70% **")

    # Summary
    lines.append("")
    lines.append("=" * 72)
    lines.append("SUMMARY BY SUBSYSTEM")
    lines.append("=" * 72)

    subsystems: dict[str, float] = {}
    for h in budget.loads:
        subsystems[h.subsystem] = subsystems.get(h.subsystem, 0.0) + h.load_w

    for sub, total_w in sorted(subsystems.items(), key=lambda x: -x[1]):
        lines.append(f"  {sub:<25s}  {total_w*1e3:>10.3f} mW")

    grand_total = sum(h.load_w for h in budget.loads)
    lines.append(f"  {'-'*25}  {'-'*10}")
    lines.append(f"  {'GRAND TOTAL':<25s}  {grand_total*1e3:>10.3f} mW")
    lines.append("")

    return "\n".join(lines)


def budget_to_dict(budget: ThermalBudget) -> dict[str, Any]:
    """Convert budget to a JSON-serializable dict."""
    result: dict[str, Any] = {
        "cryocooler_model": budget.cryocooler_model,
        "stages": {},
    }
    for stage_name in ["1st stage", "2nd stage"]:
        cap = budget.stage_capacities.get(stage_name, 0.0)
        total = budget.total_by_stage(stage_name)
        result["stages"][stage_name] = {
            "capacity_w": cap,
            "total_load_w": total,
            "utilization": budget.utilization_fraction(stage_name),
            "margin": budget.margin_fraction(stage_name),
            "loads": [
                {
                    "name": h.name,
                    "subsystem": h.subsystem,
                    "load_w": h.load_w,
                    "details": h.details,
                }
                for h in budget.loads_by_stage(stage_name)
            ],
        }
    return result


# ---------------------------------------------------------------------------
# Plotting (optional)
# ---------------------------------------------------------------------------

def plot_budget(budget: ThermalBudget, output_path: str | None = None) -> None:
    """Generate a pie chart of heat loads by subsystem for each stage."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("WARNING: matplotlib not installed, skipping plot.", file=sys.stderr)
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        f"Thermal Budget: {budget.cryocooler_model}",
        fontsize=14, fontweight="bold",
    )

    for ax, stage_name in zip(axes, ["1st stage", "2nd stage"]):
        stage_loads = budget.loads_by_stage(stage_name)
        if not stage_loads:
            ax.text(0.5, 0.5, "No loads", ha="center", va="center")
            ax.set_title(stage_name)
            continue

        labels = [h.name for h in stage_loads]
        values = [h.load_mw for h in stage_loads]
        cap_mw = budget.stage_capacities.get(stage_name, 0.0) * 1e3
        util = budget.utilization_fraction(stage_name)

        # Add "Available margin" as a slice
        margin_mw = cap_mw - sum(values)
        if margin_mw > 0:
            labels.append("Available margin")
            values.append(margin_mw)

        colors = plt.cm.Set3.colors  # type: ignore[attr-defined]
        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            autopct=lambda pct: f"{pct:.1f}%" if pct > 2 else "",
            colors=colors[: len(values)],
            startangle=90,
        )
        ax.legend(
            wedges, labels,
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=8,
        )
        ax.set_title(
            f"{stage_name}: {sum(v for v in values[:len(stage_loads)]):.2f} mW "
            f"/ {cap_mw:.0f} mW ({util*100:.1f}% used)"
        )

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {output_path}")
    else:
        plt.show()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_inputs(path: str | Path) -> dict[str, Any]:
    """Load and return the YAML inputs file."""
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cryogenic thermal budget calculator for the cryo-rack demo system",
    )
    parser.add_argument(
        "--inputs", "-i",
        default=str(Path(__file__).resolve().parent.parent / "data" / "thermal_inputs.yaml"),
        help="Path to thermal inputs YAML file (default: data/thermal_inputs.yaml)",
    )
    parser.add_argument(
        "--plot", "-p",
        nargs="?",
        const="thermal_budget.png",
        default=None,
        help="Generate pie chart (optionally specify output file path)",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output machine-readable JSON instead of text report",
    )
    args = parser.parse_args()

    inputs = load_inputs(args.inputs)
    budget = compute_budget(inputs)

    if args.json:
        print(json.dumps(budget_to_dict(budget), indent=2))
    else:
        print(format_report(budget))

    if args.plot:
        plot_budget(budget, output_path=args.plot)


if __name__ == "__main__":
    main()
