# System Architecture

## Overview

The cryo rack is a self-contained cryogenic deployment platform for AQFP superconducting processors. It houses a GM cryocooler, vacuum system, magnetic shielding, and instrumentation in a standard 19" rack, with all signal and power connections accessible from the front or rear panel.

## Block Diagram

```
┌─────────────────────────────────────────────────┐
│  19" Rack                                        │
│                                                   │
│  ┌──────────────┐    ┌────────────────────────┐  │
│  │ Instruments  │    │ Cryostat               │  │
│  │              │    │                        │  │
│  │ Temp Monitor │    │  300K ──── Feedthroughs│  │
│  │ Bias Sources │    │    │                   │  │
│  │ Clock Gen    │    │  40K ──── FINEMET      │  │
│  │ DAQ/Scope    │    │    │      shield       │  │
│  │              │    │   4K ──── Pb shield    │  │
│  │              │    │    │      DUT mount    │  │
│  └──────────────┘    │    └── AQFP die       │  │
│                      └────────────────────────┘  │
│  ┌──────────────┐    ┌────────────────────────┐  │
│  │ He Compressor│◄──►│ Flex lines to cold head│  │
│  │ (+ chiller)  │    └────────────────────────┘  │
│  └──────────────┘                                 │
│  ┌──────────────┐                                 │
│  │ Turbo + Scroll│   Vacuum pumping              │
│  │ Pump Stack    │                                │
│  └──────────────┘                                 │
└─────────────────────────────────────────────────┘
```

## Thermal Stages

The system has three thermal stages. The 300K (room temperature) stage holds the vacuum vessel walls, feedthroughs, and all room-temperature electronics. The first stage at approximately 40K provides radiation shielding and a thermal intercept for wiring; the FINEMET nanocrystalline magnetic shield is wrapped on the 40K radiation shield. The second stage at 4.2K is where the AQFP die is mounted, surrounded by a superconducting lead foil shield for residual field attenuation.

## Signal Path

DC bias currents are delivered via phosphor bronze or manganin twisted pairs, heat-sunk at 40K and 4K. AC clock signals at GHz frequencies travel on semi-rigid or flexible stainless-steel coaxial cables, also thermally intercepted at both stages. Signal readout follows the reverse path. All connections terminate at room-temperature feedthroughs on the cryostat top plate.

## Vacuum

The cryostat is evacuated by a turbomolecular pump backed by an oil-free scroll pump. Once cold, cryopumping on the 4K surfaces maintains vacuum without continuous pumping, though the turbo may remain connected for safety.
