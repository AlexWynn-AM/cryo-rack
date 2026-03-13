# ADR-003: Test Instrumentation Selection

**Status:** accepted  
**Date:** 2026-03-10  
**Deciders:** Team

## Context

The cryo rack needs DC bias sourcing and voltage readout for AQFP superconducting circuit characterization. Superconducting circuits are extremely sensitive to electromagnetic interference — standard bench supplies (Rigol, Keysight bench PSUs) and general-purpose SMUs (Keithley 2400 series) are too noisy. Instrument selection must reflect what the SC electronics community actually uses.

Phase 1 is basic IV characterization and functional bring-up. Phase 2 is low-speed digital functional testing (1 kHz – 1 MHz pattern generation and capture).

## Phase 1: Characterization

### Minimum Viable — Yokogawa GS200 + Keithley 2182A

- **GS200** (~$4k): Low-noise DC source, ±32 V / ±200 mA, 100 µVp-p noise. Industry standard across quantum/SC labs for Josephson junction biasing.
- **2182A** (~$6.7k): Dual-channel nanovoltmeter, 1 nV sensitivity, 15 nV p-p noise at 1s. The standard readout for SC voltage measurements.
- Together they cover single-channel IV curves and basic characterization.

### Budget Alternative — GS200 + Keithley DMM6500

- **DMM6500** (~$1.9k): 6.5-digit DMM, 100 nV sensitivity. Can replace the 2182A for initial bring-up and functional checks.
- Tradeoffs: 10x worse noise floor, no delta-mode. Fine for "does the chip respond?" testing.
- Upgrade path to 2182A is clean when precision matters.

### Not Suitable

- **Keithley 2400 series** — too noisy for SC circuits.
- **Rigol / Keysight bench supplies** — not low-noise sources; only suitable for non-SC power delivery.
- **Keithley 6221** — purpose-built AC/DC precision current source, pairs with 2182A for delta-mode. Standard at Hypres/NIST. Not selected because team doesn't use them and GS200 covers the need.

## Phase 2: Digital Functional Testing

Low-speed digital testing of AQFP circuits requires multi-channel stimulus (pattern generation at kHz–MHz rates) and synchronized readout (pattern capture and analysis).

### Option A: OCTOPUX (RedHiTech)

- **Stimulus:** Multi-channel digital pattern generation, up to 1 MHz
- **Readout:** 2 MS/s multi-channel ADC, 0.5 µV differential accuracy, pattern analysis
- **Channels:** 32 / 64 / 128 universal I/O
- **Ecosystem:** MATLAB-based, automated measurement scripts
- **Strengths:** Purpose-built for SC circuit testing since 1997. Used at Hypres and NIST. Complete test loop — generate, acquire, analyze. The only COTS system designed specifically for RSFQ/AQFP digital testing.
- **Weaknesses:** Niche product, likely long lead time. Pricing unknown (contact RedHiTech).
- **URL:** https://www.redhitech.com/octopux.html

### Option B: QDAC-II (Quantum Machines / QDevil)

- **Stimulus:** 24-channel AWG, 1 MS/s per channel, up to 300 kHz (filter limited). DC + sine + triangle + square + arbitrary waveforms. Ultra-low noise (<10 nV/√Hz), 25-bit DC resolution.
- **Readout:** DC current sensors only (pA-level per channel). **No ADC** — cannot capture circuit output at speed. Needs external digitizer to close the test loop.
- **Channels:** 24
- **Ecosystem:** Python/QCoDeS, integrates with Quantum Machines OPX
- **Strengths:** Excellent multi-channel low-noise stimulus. Good for bias + low-speed waveform generation. 1U compact form factor.
- **Weaknesses:** Output only — no acquisition path. 300 kHz bandwidth limit. ~$18-21k for stimulus alone; still need a digitizer (~$2-5k) for readout.
- **URL:** https://quantum-machines.co/products/qdac
- **Quote:** https://www.quantum-machines.co/request-a-quote-qdac/

### Option C: Custom FPGA / Red Pitaya

- Low-cost digitizer + DAC approach. Red Pitaya STEMlab 125-14 is ~$500 with 2-ch 125 MS/s ADC + 2-ch 14-bit DAC. Could pair with QDAC-II for stimulus.
- Requires custom firmware/software development.
- Most flexibility, lowest cost, highest effort.

## Decision

**Phase 1:** GS200 + 2182A as the minimum viable test pair. DMM6500 available as budget readout alternative (replaces 2182A, saves ~$4.8k).

**Phase 2:** Evaluate OCTOPUX and QDAC-II + digitizer once Phase 1 characterization is complete and digital testing requirements are defined. OCTOPUX is the stronger option if available; QDAC-II is a good stimulus box if paired with a separate ADC.

## Consequences

- Phase 1 instruments (GS200, 2182A) are single-channel. Scaling to multi-channel bias requires a Phase 2 investment.
- The clock signal generator line item in the BOM (for GHz AQFP clocking) is separate from the kHz–MHz digital test stimulus discussed here.
- OCTOPUX pricing and lead time need to be confirmed with RedHiTech before Phase 2 planning.
