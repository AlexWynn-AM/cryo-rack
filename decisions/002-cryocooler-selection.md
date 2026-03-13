# ADR-002: Cryocooler Selection

**Status:** proposed  
**Date:** 2026-03-10  
**Deciders:** Team

See also: [docs/cryocooler-comparison.md](../docs/cryocooler-comparison.md) for full quoted comparison table.

## Context

The cryo rack needs a two-stage cryocooler to reach 4.2 K for AQFP testing. The system must be operational at Vertiv within ~4 weeks, then move to CBA and AM. Key drivers are lead time, cost, 120 V plug-and-play operation, and sufficient cooling for a minimal-wiring first build.

The original BOM placeholder spec'd ">= 1 W at 4.2 K" (RDK-408D2 class), but the actual thermal budget for the first build is ~16 mW at 4 K and ~2 W at 40 K — well within the capacity of a smaller cooler.

Quotes have been received for four options (all in `bom/quotes/`).

## Options Considered

### Option A: Sumitomo RDK-101D + CNA-11RC — $27,230 (Recommended)

- **4 K capacity:** 0.1 W at 4.2 K
- **40 K capacity:** ~6 W at 45 K
- **Compressor:** CNA-11RC, air-cooled, 100–120 V single-phase, 1.0–1.2 kW
- **120 V / 15 A:** Yes — 1.2 kW well within 1,440 W continuous limit
- **Lead time:** 12 weeks ARO
- **Quote:** SHI Quote 5618, 11/7/2025 (expired — re-quote needed)
- **Type:** GM
- **Pros:**
  - 120 V plug-and-play — works at any site without special power
  - Air-cooled — no chilled water needed
  - Well-established platform, extensive support ecosystem
  - Adequate margin for minimal AQFP test (~16% utilization at 4 K)
  - 10,000 hr maintenance interval, field-serviceable
- **Cons:**
  - 12-week lead time
  - Limited headroom for Phase 2 expansion
  - Moderate vibration at cold stage (GM displacer)

### Option B: Bama BMC401 + HC104F — $12,500 (Backup)

- **4 K capacity:** 0.16 W at 4.2 K
- **40 K capacity:** 3 W at 45 K
- **Compressor:** HC104F — voltage/cooling TBD, must confirm with vendor
- **120 V / 15 A:** Unknown — must confirm. Chinese equipment often defaults to 220 V / 50 Hz.
- **Lead time:** 4 weeks
- **Quote:** Bama email, RMB 90,000 EXW (active)
- **Type:** GM
- **Pros:**
  - Lowest cost by far (less than half of SHI)
  - Fastest lead time (4 weeks)
  - Higher 4 K capacity than RDK-101D (0.16 W vs 0.1 W)
  - Reaches < 2.3 K base temperature
- **Cons:**
  - Less established in Western cryo labs — smaller support ecosystem
  - 120 V / cooling method unconfirmed
  - 1st stage only 3 W @ 45 K (vs 6 W for SHI) — tighter margin at 40 K
  - Flex lines/cables may not be included in quote
  - 10,000 hr maintenance (same as SHI)

### Option C: Cryomech PT205 + CP103A — $42,325 (Reference only)

- **4 K capacity:** 0.1–0.3 W at 5–6 K (prototype)
- **Compressor:** CP103A, 208/220 V 1-ph 60 Hz, air-cooled, ~1.5 kW, 19" rack
- **120 V / 15 A:** No — requires 208/220 V dedicated circuit (NEMA 6-15/6-20)
- **Lead time:** 36–40 weeks ARO (prototype)
- **Quote:** Bluefors CTI Quote 0010037, 10/24/2025 (expired)
- **Type:** Pulse tube
- **Pros:**
  - No moving parts at cold end — low vibration, ~20,000+ hr maintenance
  - Rack-mountable compressor
- **Cons:**
  - Prototype — 36–40 week lead time rules it out for near-term build
  - Most expensive option
  - Requires 208 V — not plug-and-play at arbitrary sites
  - Must be operated near-vertical (pulse tube orientation sensitivity)
  - 5–6 K operation, not guaranteed < 4.2 K

### Option D: SHI RDC-02K + CNA-11RC — $37,155

- **4 K capacity:** 0.2 W at 4.2 K
- **40 K capacity:** ~6 W at 45 K
- **Compressor:** CNA-11RC, air-cooled, 100–120 V single-phase, 1.0–1.2 kW
- **120 V / 15 A:** Yes — same compressor as Option A
- **Lead time:** 12 weeks ARO
- **Quote:** SHI Quote 5617 (expired — re-quote needed)
- **Min temp:** < 2 K (guaranteed)
- **Type:** GM
- **Pros:**
  - 2× the 4 K capacity of the RDK-101D (0.2 W vs 0.1 W) — more headroom for Phase 2 wiring
  - Guaranteed < 2 K base — enables future sub-4 K experiments if needed
  - Same compressor, flex lines, and rack integration as Option A
  - 120 V plug-and-play, air-cooled
- **Cons:**
  - $10k premium over Option A for capacity not needed in the first build
  - Slightly heavier cold head (~6 kg vs ~4 kg)
  - 12-week lead time (same as Option A)
  - Quote expired — re-quote needed

### Previously considered (not quoted)

- **RDK-408D2 + CSW-71D:** ~$40–60k, water-cooled, 208 V, overkill for this build.
- **Cryomech PT410:** ~$50–70k, water-cooled, 208 V, overkill.

## Decision

**Select RDK-101D + CNA-11RC as primary (Option A). BMC401 as backup/fast-start (Option B).**

The PT205 pulse tube is not viable for the near-term build due to 36–40 week prototype lead time, 208 V power requirement, and higher cost. It should be reconsidered for a future permanent installation.

## Rationale

1. **Thermal budget fit:** ~16 mW at 4 K and ~2 W at 40 K — both options cover this with margin.
2. **120 V plug-and-play:** The CNA-11RC runs on a standard wall outlet. The Cryomech CP103A does not. This is a hard constraint for a portable demo rack.
3. **GM reliability is sufficient:** 10,000 hr maintenance interval gives > 1 year continuous before service. For a demo/prototype platform this is more than adequate.
4. **Pulse tube advantages don't help here:** Low vibration matters for scanning probe or optical alignment, not for AQFP electrical testing. The 2x maintenance interval doesn't justify 3x cost and 8x lead time.
5. **BMC401 is the fastest path** if we need to move immediately — 4 weeks, $12.5k. Must confirm 120 V compatibility.

## Consequences

- Cryostat design must be compatible with the RDK-101D cold-head flange (outline drawing in `bom/quotes/`).
- If BMC401 compressor is 220 V only, it needs a step-up transformer or dedicated circuit — reduces its plug-and-play advantage.
- Phase 2 may require a cooler upgrade — design cryostat top plate to accept larger cold heads if practical.
- Water chiller line item not needed (both options are air-cooled).

## Open Actions

1. Re-quote SHI RDK-101D (Quote 5618 expired 12/7/2025)
2. Confirm BMC401 compressor specs: input voltage (120 V / 60 Hz available?), air vs water cooling, flex line inclusion
3. Make go/no-go decision on Option A vs B based on voltage confirmation and schedule
