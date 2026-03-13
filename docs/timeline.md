# Project Timeline

**Target:** Operational cryo rack within 4 weeks of project start (by ~April 10, 2026).

## Week 1: Design Finalization & Procurement Start

- Finalize cryocooler selection (ADR required).
- Finalize cryostat approach: COTS vs custom, vendor selection.
- Send RFQs for all long-lead items.
- Complete thermal budget estimates for both stages.
- Order any items with known > 2 week lead times immediately.

## Week 2: Procurement & Fabrication

- Place orders for all major components.
- Design and order custom parts (DUT mount, adapter plates, wiring looms).
- Order magnetic shielding materials.
- Begin rack layout planning (physical arrangement, cable routing).

## Week 3: Assembly & Integration

- Receive and inspect major components.
- Assemble cryostat: cold head mounting, radiation shields, wiring.
- Install magnetic shielding.
- Wire feedthroughs and test at room temperature.
- Assemble rack: mount instruments, route cables, install PDU.

## Week 4: Cooldown & Commissioning

- Leak check vacuum system.
- Pump down and begin cooldown.
- Verify base temperature at both stages.
- Measure residual magnetic field at DUT location.
- Basic functional test with AQFP die (if available).
- Document as-built configuration.

## Critical Path Items

These are the items most likely to gate the schedule:

1. Cryostat / vacuum vessel (longest lead if custom; COTS may ship faster)
2. GM cryocooler cold head (typically 2-6 week lead)
3. Custom magnetic shielding (if non-stock dimensions)
4. Electrical feedthroughs (if high pin count or custom)

## Risk Mitigations

- Identify backup vendors for critical-path items.
- Consider used/refurbished cryocooler equipment to shorten lead time.
- Decouple phases: rack assembly and instrumentation setup can proceed in parallel with cryostat procurement.
