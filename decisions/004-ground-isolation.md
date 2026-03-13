# ADR-004: Ground Isolation Architecture

**Status:** proposed  
**Date:** 2026-03-13  
**Deciders:** Team

See also: [docs/ground_isolation_memo.docx](../docs/ground_isolation_memo.docx) for full analysis.

## Context

The RDK-101D cold head is galvanically continuous with the CNA-11RC compressor chassis through the stainless steel body and flex lines. The compressor chassis is earth-grounded through its AC power cord. The GM cycle valve motor produces periodic current transients (~1 Hz) that propagate through this ground structure.

If the AQFP copper backplane at 4 K is bolted directly to the second-stage cold finger, the circuit ground reference is defined in part by the compressor ground, injecting motor noise into the measurement return path.

Two isolation points are needed: one at the cold interface (4 K) and one at the room-temperature power entry.

## Options Considered

### Option A: Single isolation transformer for everything

Compressor, cold head, and readout electronics all sit behind one isolation transformer, sharing a single isolated ground domain. Eliminates building mains noise and is simple (one transformer, one plug). However, the compressor motor's switching currents still flow through the shared ground bus, and the readout electronics see this as noise on their voltage reference. Trades building mains noise for compressor motor noise.

### Option B: Isolate only the readout (Recommended)

Compressor stays on building mains, earth-grounded for safety and code compliance. Readout electronics get their own small isolation transformer (500 W–1 kW) with a clean, quiet, isolated ground reference. The alumina disk isolates the 4 K backplane from the cold head structure. The only connection between the readout ground domain and the 4 K circuit is the dedicated ground wires through the DC feedthrough pins.

No shared conductor carries both motor current and signal return current at any point in the system. This is the standard approach used in SQUID magnetometry and other sensitive superconducting measurements.

COTS units: Tripp Lite IS500HG (500 W, 120 V, UL 60601-1, Faraday-shielded, ~$200–300) or IS1000HG (1 kW). Compact enough for a 1U–2U rack shelf.

### Option C: Two separate isolation transformers

Compressor on one isolation transformer, readout on another. Provides maximum isolation from building mains for both, but introduces a ground loop risk. If the compressor's isolated ground and the readout's isolated ground are inadvertently connected through the cryostat body (compressor → flex lines → cold head → vacuum jacket → feedthrough shell → readout ground), a ground loop forms. The alumina disk breaks one leg of that loop, but any feedthrough shield, cable braid, or debug probe touching the vacuum jacket re-establishes it. Two separate isolated ground domains with an accidental single-point connection is worse than a deliberate single-point design. Not recommended.

## Decision

**Select Option B: isolate only the readout electronics.**

Two ground domains with a single, well-defined interface:

- **Domain 1 (earth ground):** Building mains earth → compressor chassis → stainless flex lines → cold head body → cryostat vacuum jacket → rack chassis. Carries compressor motor currents. No measurement signals.
- **Domain 2 (isolated measurement ground):** Isolation transformer secondary → readout electronics ground bus → dedicated ground wires through DC feedthrough pins → copper backplane at 4 K → AQFP circuit ground. Carries only signal and bias currents.

Isolation between domains is maintained by:
- Alumina disk at 4 K (between cold finger and backplane)
- Ceramic seals in hermetic feedthroughs at 300 K (pins isolated from flange body by design)

## Consequences

- **BOM additions:** alumina disk (~$30, off-the-shelf), indium foil for both faces (already in BOM), Tripp Lite IS500HG isolation transformer (~$250).
- **Assembly discipline:** No readout cable shield, coax braid, ground lug, or debug probe ground may touch the cryostat body, vacuum jacket, or rack chassis. Every electrical connection between the readout and the cryostat must pass through the feedthrough pins only. Document this in the integration checklist.
- **Thermal impact:** Alumina disk adds a fraction of a kelvin to the base temperature at the backplane. Negligible given >90% thermal margin.
- **Cryostat assembly change:** Sample stage is no longer bolted directly to cold finger. Stack is now: cold finger → indium foil → alumina disk → indium foil → copper backplane.
- **Feedthrough selection:** Standard ceramic-to-metal hermetic feedthroughs (Ceramaseal, Lesker) maintain isolation by design. Any shielded/coax lines where the shield connects to the flange must be avoided or modified.

## Open Questions

1. Confirm RDK-101D CF flange size (believed CF4.50 / DN63CF) — affects zero-length reducer selection if vessel is upsized.
2. Isolation transformer sizing — 500 W likely sufficient for readout alone; verify total draw of DAC/ADC, bias sources, clock generator.
3. Establish debug access protocol: no scope probe ground or clip lead may touch cryostat body during measurement. Label feedthrough connectors accordingly.
