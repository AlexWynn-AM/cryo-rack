# Cryocooler Options — Quoted Comparison

Last updated: 2026-03-11 (BOM rev 0.7)

## Quoted Options

| Parameter | **Bama BMC401** | **SHI RDK-101D** | **SHI RDC-02K** | **Cryomech PT205** |
|---|---|---|---|---|
| **Type** | GM | GM | GM | Pulse tube |
| **Quoted price** | $13,000 (USD direct) | $27,230 | $37,155 | $42,325 |
| **Lead time** | 4 weeks | 12 weeks | 12 weeks | 36–40 weeks |
| **2nd stage (4.2 K)** | 0.16 W | 0.1 W | 0.2 W | 0.1–0.3 W (prototype) |
| **1st stage** | 3 W @ 45 K | ~6 W @ 45 K | ~6 W @ 45 K | TBD ("not as important") |
| **Min temp** | < 2.3 K | ~3.5 K | < 2 K (guaranteed) | 5–6 K |
| **120 V / 15 A compatible** | **Marginal** — HC104F is 220V/1.5kW; with step-up xfmr draws 12.5A @ 120V (tight on 15A, OK on 20A). 60Hz confirmed. | **Yes** (CNA-11RC, 1.0–1.2 kW) | **Yes** (same CNA-11RC) | **Likely yes** — quote said 208/220V but ~1.5 kW = 12.5A @ 120V; confirm 120V option |
| **Cooling** | TBD — confirm | Air-cooled | Air-cooled | Air-cooled |
| **Rack-mountable compressor** | TBD | Yes (CNA-11 series) | Yes (CNA-11 series) | Yes (CP103A, 19" rack) |
| **Compressor input power** | 1.5 kW (confirmed) | ~1.0–1.2 kW | ~1.0–1.2 kW | ~1.5 kW |
| **Cold head mass** | 8 kg | ~4 kg | ~6 kg | TBD (prototype) |
| **Maintenance interval** | 10,000 hr | 10,000 hr | 10,000 hr | ~20,000+ hr (est.) |
| **Vibration at cold stage** | Moderate (GM) | Moderate (GM) | Moderate (GM) | Low (pulse tube) |
| **Quote status** | Active | Expired — re-quote | Expired — re-quote | Expired — re-quote |
| **Quote ref** | Bama email Oct 2025, $7k+$6k USD | SHI Quote 5618 | SHI Quote 5617 | Quote 0010037, Ticket 72680 |
| **Vendor** | Bama Superconductor (Suzhou) | SHI Cryogenics of America | SHI Cryogenics of America | Bluefors CTI (Cryomech) |

### Alternative Compressor: attocube IGLU

The [IGLU compressor](https://www.attocube.com/en/products/cryostats/compact-mobile-cryogenics/iglu-compressor) is a standalone rack-mountable helium compressor (~$40k est.) confirmed compatible with the RDK-101D cold head. 19" rack form factor, ~1 kW input, air-cooled, orientation-free, oil-free. Natively 230V but at ~1 kW a 120V step-up transformer is trivial (~8.3A). Decouples the compressor from the cold head vendor. However, the CNA-11RC bundled in the SHI quote is $13k and does 120V natively — so the IGLU is 3x the cost for the same function. Mainly interesting for future modularity or if rack density is critical.

### 120 V / 15 A Notes

A standard US NEMA 5-15 outlet supplies 120 V at 15 A (1,800 W max, 1,440 W continuous per NEC 80% rule).

- **SHI CNA-11RC**: 1.0–1.2 kW input. Runs on 100–120 V single-phase. Well within 15 A / 1,440 W continuous. **Plug and play.**
- **Cryomech CP103A**: Quote specified 208/220 V, 1-ph, 60 Hz, ~1.5 kW. However, at 1.5 kW a 120 V version would draw only ~12.5 A — well within 15 A. Cryomech (US manufacturer, Syracuse NY) routinely makes compressors in multiple voltage variants. **Likely available in 120 V — confirm when re-quoting.** If so, this is also plug-and-play.
- **Bama HC104F**: 220 V, **1.5 kW confirmed** (10A Chinese outlet). **60 Hz confirmed OK** — Bama can set before shipping. With a ~$40 step-up transformer (120V→220V, 1.5 kW), draws **~12.5 A @ 120 V**. Exceeds the NEC 80% continuous limit (12 A) on a 15 A breaker, but **fine on a 20 A circuit (NEMA 5-20)**. Much better than the 3 kW / 25 A originally estimated. BMC401 cold head is **NOT compatible** with SHI CNA-11 compressor (different motor drive).

## Pulse Tube vs GM — Reliability & Tradeoffs

### GM (Gifford-McMahon) — BMC401, RDK-101D, RDC-02K

- **Moving parts at cold end**: mechanical displacer with seal, driven by motor.
- **Maintenance interval**: ~10,000 hours (~14 months continuous). Displacer seal and regenerator service.
- **Failure modes**: well-characterized. Seal wear is gradual — performance degrades before failure. Field-serviceable with standard tool kits (SHI includes one in quote).
- **Vibration**: moderate displacement at cold stage (~10–25 μm) due to displacer motion. For AQFP testing this is generally acceptable — AQFP chips are not mechanically sensitive in the way optical cavities or STM tips are.
- **Orientation**: can operate in any orientation (some models have restrictions, but SHI RDK-101D is flexible).
- **Cooldown**: relatively fast. BMC401 < 150 min, RDK-101D typically ~60–90 min.

### Pulse Tube — PT205

- **No moving parts at cold end**: the oscillating gas column replaces the mechanical displacer. All moving parts are in the remote compressor.
- **Maintenance interval**: ~20,000–30,000 hours (~2–3 years continuous). Compressor valve maintenance only.
- **Failure modes**: less wear overall, but when issues occur they tend to be in the rotary valve or compressor — still field-serviceable. Less community experience with the PT205 specifically (it's a prototype).
- **Vibration**: significantly lower at cold stage (no displacer motion). Relevant for vibration-sensitive measurements (scanning probe, optical interferometry), but **not a major differentiator for AQFP electrical testing**.
- **Orientation**: pulse tubes are more sensitive to tilt. Most must operate within ~5° of vertical. This matters for shipping/setup but not for steady-state rack operation.
- **Cooldown**: can be slower than GM for the same capacity due to lower specific cooling at high temperatures.

### Recommendation for This Project

For a demo rack that needs to be stood up fast and moved between sites:

1. **GM is the practical choice.** Shorter lead time, lower cost, simpler logistics (120 V, any orientation).
2. **10,000 hr maintenance is fine** — this is a prototype/demo platform, not a 24/7 production system. Even at 10,000 hr you get > 1 year before first service.
3. **Pulse tube advantages (vibration, maintenance interval) don't materially help AQFP electrical testing.** If we were doing scanning probe microscopy or optical alignment, pulse tube would be worth the premium.
4. **The PT205 being a prototype with 36–40 week lead time eliminates it** from contention for the near-term build regardless.

Pulse tube should be reconsidered for a future permanent installation where unattended multi-year operation and low vibration are priorities.
