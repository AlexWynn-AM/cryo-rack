# Thermal Budget — RDK-101D + CNA-11RC

Last updated: 2026-03-11 (BOM rev 0.6)

## Cryocooler Capacity

RDK-101D with CNA-11RC compressor at 60 Hz (US power):

| Stage | Temperature | Capacity |
|---|---|---|
| 1st stage | 45–60 K | 3–5 W |
| 2nd stage | 4.2 K | **0.1 W (100 mW)** |

Note: headline spec (0.2 W) is with larger F-20L/FA-20L compressors.
CNA-11 footnote on SHI datasheet: 0.1 W @ 4.2 K. Use this for budgeting.

## Chamber Geometry (from BOM rev 0.6)

- Vacuum vessel: 6" OD SS tube (~140 mm ID)
- Radiation shield: ~Ø100 mm OD × 150–200 mm tall, 6061 Al
- Sample stage: ~Ø50 mm × 20 mm, OFHC Cu
- MLI: 10-layer aluminized mylar on radiation shield exterior

## 2nd Stage (4 K) Heat Budget

| Source | Parameters | Load (mW) |
|---|---|---|
| Radiation (40K → 4K) | ε≈0.1, A≈0.02 m², σ·(40⁴−4⁴) | 0.3 |
| DC wire conduction (40K → 4K) | 16× PhBr 36AWG, L=0.3m, k≈4 W/mK | 0.1 |
| RF coax conduction (40K → 4K) | 4× SS 0.086", L=0.3m, A_metal≈1.7e-6 m² | 2.0 |
| DUT dissipation | AQFP: nW–μW | ~0 |
| **Total** | | **~2.4** |
| **Available** | | **100** |
| **Utilization** | | **2.4%** |

Dominant load: RF coax conduction. Large margin.

## 1st Stage (40 K) Heat Budget

| Source | Parameters | Load (mW) |
|---|---|---|
| Radiation (300K → 40K) w/ 10-layer MLI | ~1.5 W/m², A≈0.08 m² | 120 |
| Radiation (300K → 40K) without MLI | ε≈0.05 bare, A≈0.08 m² | 1,800 |
| DC wire conduction (300K → 40K) | 16× PhBr 36AWG, L=0.5m, k≈25 W/mK | 3 |
| RF coax conduction (300K → 40K) | 4× SS 0.086", L=0.5m, k≈10 W/mK | 35 |
| **Total (with MLI)** | | **~160** |
| **Total (without MLI)** | | **~1,840** |
| **Available** | | **~3,000** |
| **Utilization (with MLI)** | | **5%** |
| **Utilization (without MLI)** | | **61%** |

MLI is not strictly required but reduces 1st stage load by >10×.
Without MLI the system still works but with reduced margin.

## Assumptions

- Wire lengths: ~0.5 m from 300K to 40K heat sink, ~0.3 m from 40K to 4K
- Phosphor bronze thermal conductivity: ~25 W/mK avg (300K–40K), ~4 W/mK avg (40K–4K)
- SS304 thermal conductivity: ~10 W/mK avg (300K–40K), ~2.5 W/mK avg (40K–4K)
- Emissivities: 0.05 (polished metal), 0.1 (unpolished/mixed surfaces at 4K)
- MLI performance: ~1.5 W/m² (typical for 10-layer at 300K–40K)
- 0.086" SS coax metal cross-section: ~1.7e-6 m² (outer + inner conductor)
- 36 AWG wire cross-section: 1.27e-8 m² per conductor
- AQFP DUT dissipation: negligible (nW–μW)

## Risk Items

1. **More RF cables**: each additional 0.086" SS coax adds ~0.5 mW at 4K
   and ~9 mW at 40K. Could add up to 10 cables before 4K budget reaches
   10% utilization.
2. **Larger DUT package**: if future DUT needs more wiring (e.g., 64-pin
   instead of 16), DC wire conduction roughly scales linearly.
   64 wires × 6 μW = 0.4 mW — still negligible.
3. **Wiring heat-sinking quality**: if 40K heat sink is poor (wires not
   well anchored), some 300K heat leaks directly to 4K. GE varnish and
   proper bobbin wrapping are essential.
4. **MLI installation quality**: crumpled or poorly layered MLI degrades
   performance significantly. If MLI is bad, radiation load approaches
   the "without MLI" case — still within budget but reduced margin.

## Conclusion

The RDK-101D + CNA-11RC is well-matched to this chamber. Both stages
have >90% margin with MLI. The small radiation shield area is the main
reason the budget works so comfortably. There is ample room to add more
wiring or a larger DUT in the future without upgrading the cryocooler.

---

## Appendix A: Radiation Shield Sizing — How Big Can We Go?

### Which stage constrains shield size?

**4K (2nd stage): not constrained by shield size.** For a small object
(sample stage) inside a larger enclosure (radiation shield), heat load
depends on the *object* area, not the enclosure area:
Q = ε_object × σ × A_object × (T_enclosure⁴ − T_object⁴).
Making the shield bigger does not increase the 4K heat load. The 2nd
stage budget is wire-conduction limited (~2 mW for 4 coax + 16 DC wires),
independent of shield geometry.

**40K (1st stage): this is the constraint.** Radiation from the 300K
vacuum vessel wall to the 40K shield scales directly with shield surface
area. Available budget: ~3 W (CNA-11RC, 60 Hz). Using 70% utilization
policy → 2.1 W, minus ~40 mW wires → ~2.06 W for radiation.

### Shield size vs. 1st stage heat load

| Shield (Ø × H) | Area (m²) | Vacuum vessel | With MLI | No MLI (ε=0.05) | No MLI (ε=0.15) |
|---|---|---|---|---|---|
| Ø100 × 150 mm | 0.063 | 6" CF nipple | 95 mW **(3%)** | 1.4 W (48%) | 4.3 W (OVER) |
| Ø150 × 200 mm | 0.129 | 8" CF nipple | 194 mW **(6%)** | 3.0 W (100%) | 8.9 W (OVER) |
| Ø200 × 300 mm | 0.251 | 10" CF nipple | 376 mW **(13%)** | 5.8 W (OVER) | 17 W (OVER) |
| Ø300 × 400 mm | 0.518 | 12–14" CF nipple | 777 mW **(26%)** | 12 W (OVER) | 36 W (OVER) |
| Ø400 × 500 mm | 0.942 | 16" CF nipple | 1.4 W **(47%)** | 22 W (OVER) | 65 W (OVER) |
| Max @ 70% util | ~1.4 m² | ~Ø350 × 1000 mm | 2.1 W **(70%)** | — | — |

### Rack fit check

19" rack: 482 mm panel width, ~450 mm between rails.

| Shield Ø | Vessel OD (approx) | Fits in rack? |
|---|---|---|
| 200 mm | ~250 mm (10") | **Yes** — 200 mm clearance |
| 300 mm | ~350 mm (14") | **Yes** — 130 mm clearance |
| 400 mm | ~450 mm (18") | Tight — needs careful layout |

### Takeaway

With MLI, shield size is **thermally unconstrained** for any rack-mount
design. A Ø200–300 mm shield (generous working space for multiple DUTs,
complex wiring, and magnetic shielding layers) uses only 13–26% of the
1st stage budget and fits comfortably in a 19" rack.

**Without MLI, shield size is tightly constrained.** Even a Ø150 × 200 mm
shield hits 100% utilization with polished surfaces. MLI is effectively
mandatory for any shield larger than the minimum baseline design.

The practical constraints on chamber size are:
1. Vacuum vessel cost and weight (bigger CF = heavier, pricier)
2. Cold head reach (2nd stage cold finger has a fixed length)
3. Rack depth and cryostat mounting logistics
