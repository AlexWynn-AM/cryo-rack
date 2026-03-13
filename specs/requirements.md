# System Requirements

## Functional Requirements

1. Provide a 4.2 K environment with sufficient volume to mount and test AQFP processor die.
2. Cryocooler cooling capacity: >= 100 mW at 4.2 K (second stage), >= 6 W at 45 K (first stage). Thermal budget shows ~16 mW / ~2 W actual load (see `specs/thermal-budget.md`).
3. Ambient magnetic field at the DUT must be < 5 uT (with shielding, target < 100 nT using superconducting Pb shield at 4 K).
4. Support DC bias wiring (16+ conductors, uA precision) from 300 K to 4 K with thermal intercepts at 40 K.
5. Support multi-phase AC clock delivery at GHz frequencies via 4 coax lines from 300 K to 4 K.
6. Support signal readout from 4 K to 300 K with adequate bandwidth.
7. Cool-down time from 300 K to 4 K base temperature should be < 12 hours.
8. System must be self-contained in a standard 19" rack form factor.

## Constraints

- **Timeline:** Procurement and assembly within approximately 4 weeks (target operational by 2026-04-10).
- **Budget:** Estimated ~$75-85k all-in for RDK-101D configuration (see BOM). Use COTS components where possible.
- **Power:** 120 V single-phase preferred for site portability. Total system power ~2-3 kW with RDK-101D air-cooled compressor.
- **Cooling water:** Not required (air-cooled CNA-11C compressor selected per ADR-002).
- **Transportability:** System must be movable between Vertiv, CBA, and AM. Avoid permanent installations. Air-cooled compressor and 120 V operation support this.

## Deployment Sites

1. **Vertiv** — first deployment, primary demo site
2. **CBA** — second deployment, leveraging existing lab infrastructure
3. **AM** — third deployment, shortly after CBA

## Future Requirements (Phase 2)

- Optical I/O path: fiber feedthroughs, VCSEL driver at 300 K, InGaAs photodiode at 4 K.
- Higher channel count for larger AQFP die (may require upgrading to RDK-408D2 class cooler).
- Integration with LPDDR5X memory subsystem at 300 K.
