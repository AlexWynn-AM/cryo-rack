#!/usr/bin/env python3
"""
Signal Chain Waterfall Plot

Renders a brand-compliant (Adiabatic Machines BRAND.md) waterfall chart
of signal amplitude and noise floor at each stage of the signal chain
from `scripts/signal_chain.py`.

Usage:
    python3 scripts/signal_chain_plot.py
    python3 scripts/signal_chain_plot.py --out docs/assets/signal_chain_waterfall.png
    python3 scripts/signal_chain_plot.py --scenario worst_loss

Outputs a PNG to `docs/assets/signal_chain_waterfall.png` by default.
The figure is committed to the repo as a fixture for documentation and
dashboard discoverability.

Brand compliance (BRAND.md):
  - White background, Geist font (falls back to sans-serif)
  - #4d65ff accent for signal trace
  - #fb5353 for noise floor
  - 16:9 aspect ratio, 150 DPI
  - Title, axis labels with units, subtle grid alpha=0.3
  - Source citation in small italic at bottom-right
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure we can import the simulator from the same dir
sys.path.insert(0, str(Path(__file__).resolve().parent))

from signal_chain import (  # noqa: E402
    AQFPOutput,
    CoaxCable,
    PCBTrace,
    RoomTempAmplifier,
    SignalChain,
    Wirebond,
    default_chain,
)


# ---------------------------------------------------------------------------
# Brand palette (BRAND.md, single source of truth in planner-repo)
# ---------------------------------------------------------------------------

BRAND = {
    "accent":      "#4d65ff",  # Primary accent: signal trace
    "background":  "#ffffff",
    "foreground":  "#171717",
    "text_sec":    "#525252",
    "text_muted":  "#737373",
    "border":      "#e5e5e5",
    "success":     "#27ae60",  # SNR > 10 dB margin
    "warning":     "#f39c12",
    "error":       "#e74c3c",  # SNR < 10 dB target
    "aqfp_teal":   "#2a9d8f",
    "noise_red":   "#fb5353",
    "baseline":    "#264653",
}


def _resolve_font_family() -> List[str]:
    """Return Geist if installed, else fall back to system sans-serif silently."""
    try:
        from matplotlib import font_manager
        installed = {f.name for f in font_manager.fontManager.ttflist}
    except Exception:
        installed = set()
    chain = []
    for candidate in ("Geist", "Inter", "Helvetica Neue", "Arial"):
        if candidate in installed:
            chain.append(candidate)
    chain.append("sans-serif")
    return chain


def _setup_brand_style() -> None:
    """Apply BRAND.md typography and figure defaults to matplotlib."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.facecolor":  BRAND["background"],
        "axes.facecolor":    BRAND["background"],
        "savefig.facecolor": BRAND["background"],
        "savefig.dpi":       150,
        "figure.dpi":        150,
        "font.family":       _resolve_font_family(),
        "axes.edgecolor":    BRAND["border"],
        "axes.labelcolor":   BRAND["foreground"],
        "axes.titlecolor":   BRAND["foreground"],
        "axes.titlesize":    20,
        "axes.titleweight":  "bold",
        "axes.labelsize":    14,
        "axes.labelweight":  "bold",
        "xtick.color":       BRAND["foreground"],
        "ytick.color":       BRAND["foreground"],
        "xtick.labelsize":   12,
        "ytick.labelsize":   12,
        "legend.fontsize":   12,
        "legend.frameon":    False,
        "grid.color":        BRAND["text_muted"],
        "grid.alpha":        0.3,
        "grid.linewidth":    0.5,
    })


# ---------------------------------------------------------------------------
# Scenarios (used for both plotting and testing)
# ---------------------------------------------------------------------------

def scenario_nominal() -> SignalChain:
    """Default chain: 10 uA AQFP, nominal component specs."""
    return default_chain()


def scenario_worst_loss() -> SignalChain:
    """Worst-case loss: longer cables, higher-attenuation coax, longer wirebond."""
    chain = default_chain()
    for comp in chain.components:
        if isinstance(comp, Wirebond):
            comp.length_mm = 4.0  # 2x longer bond
        elif isinstance(comp, PCBTrace):
            comp.length_mm = 60.0      # 3x longer trace
            comp.width_um = 50.0       # narrower (higher R)
            comp.copper_rrr = 20.0     # poorer copper
        elif isinstance(comp, CoaxCable):
            comp.length_m = 3.0                          # 3 m cable run
            comp.attenuation_dB_per_m_per_GHz = 1.5      # 3x lossy
    return chain


def scenario_worst_noise() -> SignalChain:
    """Worst-case noise: warm chip, noisy amplifier, lower AQFP drive."""
    chain = default_chain()
    for comp in chain.components:
        if isinstance(comp, AQFPOutput):
            comp.signal_current_A = 5.0e-6   # half the nominal drive
            comp.temperature_K = 6.0         # warm-up margin (still <Tc)
        elif isinstance(comp, RoomTempAmplifier):
            comp.noise_figure_dB_val = 5.0   # noisy LNA (vs 2 dB nominal)
            comp.gain_dB = 50.0              # less gain
    return chain


SCENARIOS = {
    "nominal":     scenario_nominal,
    "worst_loss":  scenario_worst_loss,
    "worst_noise": scenario_worst_noise,
}


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def _signal_dBuA(amps_A: List[float]) -> List[float]:
    """Convert current in amperes to dBuA (dB relative to 1 uA)."""
    return [20.0 * math.log10(a / 1e-6) if a > 0 else -200.0 for a in amps_A]


def render_waterfall(
    chain: SignalChain,
    out_path: Path,
    title: str = "AQFP Signal Chain: Amplitude and Noise vs Stage",
    subtitle: str | None = None,
) -> Path:
    """Render a brand-compliant waterfall chart of signal and noise vs stage.

    The y-axis is in dBuA (dB relative to 1 uA): this is a current-mode
    measurement chain, and dBuA puts the AQFP source (10 uA = +20 dBuA),
    the amplifier output (~mA = +60 dBuA), and the thermal noise floor
    (sub-uA) on the same intuitive scale.

    Returns the path the figure was written to.
    """
    import matplotlib.pyplot as plt

    _setup_brand_style()

    states = chain.propagate()
    names = [c.name for c in chain.components]
    sig_dBuA   = _signal_dBuA([s.amplitude_A for s in states])
    noise_dBuA = _signal_dBuA([s.noise_A for s in states])
    snrs       = [s.snr_dB for s in states]

    fig, (ax, ax_snr) = plt.subplots(
        2, 1,
        figsize=(10, 5.6),
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.15},
        sharex=True,
    )

    x = list(range(len(names)))

    # Top: signal & noise waterfall
    ax.plot(x, sig_dBuA, color=BRAND["accent"], marker="o", markersize=7,
            linewidth=2.5, label="Signal amplitude", zorder=3)
    ax.plot(x, noise_dBuA, color=BRAND["noise_red"], marker="s", markersize=6,
            linewidth=2.0, linestyle="--", label="Noise floor (RMS)", zorder=2)
    ax.fill_between(x, noise_dBuA, sig_dBuA,
                    where=[s > n for s, n in zip(sig_dBuA, noise_dBuA)],
                    color=BRAND["accent"], alpha=0.08, zorder=1)

    ax.set_ylabel("Current level (dBuA)")
    ax.set_title(title, pad=14)
    if subtitle:
        ax.text(0.0, 1.01, subtitle, transform=ax.transAxes,
                fontsize=11, color=BRAND["text_sec"])
    ax.grid(True, axis="y")
    ax.legend(loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # Bottom: SNR bar
    bar_colors = [BRAND["success"] if s >= 10.0 else BRAND["error"] for s in snrs]
    ax_snr.bar(x, snrs, color=bar_colors, width=0.65, zorder=2)
    ax_snr.axhline(10.0, color=BRAND["text_muted"], linewidth=1.0,
                   linestyle=":", zorder=1)
    ax_snr.text(len(x) - 0.4, 10.5, "10 dB target",
                fontsize=10, color=BRAND["text_muted"], ha="right")
    ax_snr.set_ylabel("SNR (dB)")
    ax_snr.set_xticks(x)
    ax_snr.set_xticklabels(names, rotation=30, ha="right", fontsize=10)
    ax_snr.grid(True, axis="y")
    for spine in ("top", "right"):
        ax_snr.spines[spine].set_visible(False)

    # Source citation: place below the rotated x-tick labels so it never overlaps
    fig.subplots_adjust(bottom=0.22, top=0.90)
    fig.text(0.99, 0.01,
             "Source: cryo-rack scripts/signal_chain.py  |  AM internal",
             fontsize=8, style="italic", color=BRAND["text_muted"],
             ha="right", va="bottom")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=BRAND["background"])
    plt.close(fig)
    return out_path


def headline_numbers(chain: SignalChain) -> Tuple[float, float, str]:
    """Return (final_snr_dB, cascaded_NF_dB, bottleneck_name) for a chain."""
    states = chain.propagate()
    return (
        states[-1].snr_dB,
        chain.total_noise_figure(),
        chain.bandwidth_bottleneck()[0],
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Render brand-compliant waterfall chart of the AQFP signal "
            "chain. Default: nominal scenario, saved to "
            "docs/assets/signal_chain_waterfall.png"
        ),
    )
    parser.add_argument(
        "--scenario", choices=sorted(SCENARIOS.keys()),
        default="nominal",
        help="Which scenario to render (default: nominal)",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Output PNG path (default: docs/assets/signal_chain_waterfall.png "
             "for nominal; per-scenario filename otherwise)",
    )
    args = parser.parse_args()

    chain = SCENARIOS[args.scenario]()

    if args.out is None:
        repo_root = Path(__file__).resolve().parent.parent
        if args.scenario == "nominal":
            out = repo_root / "docs" / "assets" / "signal_chain_waterfall.png"
        else:
            out = repo_root / "docs" / "assets" / f"signal_chain_waterfall_{args.scenario}.png"
    else:
        out = args.out

    snr, nf, bottleneck = headline_numbers(chain)
    subtitles = {
        "nominal":     "Nominal: 10 uA AQFP drive, 2 mm wirebond, 1 m coax, SRS-560 LNA",
        "worst_loss":  "Worst-case loss: 4 mm bond, 60 mm narrow trace, 3 m lossy coax",
        "worst_noise": "Worst-case noise: 5 uA drive, 6 K chip, 5 dB NF / 50 dB LNA",
    }
    title = "AQFP Signal Chain: Amplitude and Noise vs Stage"
    path = render_waterfall(chain, out, title=title,
                            subtitle=subtitles.get(args.scenario))

    print(f"Wrote {path}")
    print(f"Scenario:    {args.scenario}")
    print(f"Final SNR:   {snr:.1f} dB")
    print(f"Cascaded NF: {nf:.2f} dB")
    print(f"BW bottleneck: {bottleneck}")


if __name__ == "__main__":
    main()
