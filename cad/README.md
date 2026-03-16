# Cryostat CAD Model

FreeCAD 3D model of the cryo-rack cryostat system for AQFP testing.

## Folder Structure

```
cad/
├── README.md                    # This file
├── dimensions.fods              # FreeCAD-linked spreadsheet (Flat ODS)
├── build.sh                     # Build script (generates .FCStd files)
├── build-all.py                 # FreeCAD build script
├── parts/
│   ├── rdk-101d-cold-head.py    # → rdk-101d-cold-head.FCStd
│   ├── sample-stage.py          # → sample-stage.FCStd
│   ├── alumina-disk.py          # → alumina-disk.FCStd
│   ├── radiation-shield.py      # → radiation-shield.FCStd
│   ├── vacuum-vessel.py         # → vacuum-vessel.FCStd
│   ├── top-plate.py             # → top-plate.FCStd
│   ├── thermal-straps.py        # → thermal-straps.FCStd
│   └── wiring.py                # → wiring.FCStd
├── assembly/
│   └── cryostat-assembly.py     # → cryostat-assembly.FCStd
├── exports/                     # STEP files for external sharing
│   └── (generated on demand)
└── reference/
    └── BMC401_cryocooler.stp    # Vendor STEP model (SHI BMC401 cryo cooler)
```

## Building the Models

The `.FCStd` files are generated from Python scripts. To build:

### Option 1: Shell script (recommended)
```bash
cd cad
./build.sh           # Build all parts and assembly
./build.sh clean     # Remove generated files
./build.sh export    # Export to STEP format
```

### Option 2: From FreeCAD GUI
1. Open FreeCAD 0.21 or later
2. Open the Python console (View → Panels → Python console)
3. Run: `exec(open('/path/to/cad/build-all.py').read())`

### Option 3: Individual parts
```bash
cd cad/parts
freecadcmd rdk-101d-cold-head.py  # Generates .FCStd file
```

## Opening the Model

1. Build the models first (see above)
2. Open FreeCAD 0.21 or later
3. Open `assembly/cryostat-assembly.FCStd`
4. All parts are included in the assembly file

## Dimension Sources

### RDK-101D Cold Head (SHI Cryogenics)
- **Source:** SHI RDK-101D outline drawing (request from distributor)
- **Total height:** 442 mm (motor housing to 2nd stage tip)
- **Motor housing:** Ø130 mm
- **1st stage flange:** Ø108 mm at 45K
- **2nd stage cold finger:** Ø52 mm → Ø45 mm at 4K
- **CF flange:** DN63CF (CF4.50)

### Vacuum Vessel
- **Source:** Kurt J. Lesker standard CF components
- **Size:** DN200CF (10" CF flanges, ~200 mm ID)
- **Wall:** 304L stainless steel
- **Length:** Calculated from cold head reach + clearances

### Radiation Shield
- **Source:** Custom fabrication (6061-T6 Al)
- **Default size:** Ø180 mm OD × 250 mm height × 2 mm wall
- **Linked to:** `dimensions.ods` for easy updates

### Sample Stage
- **Source:** Custom fabrication (OFHC Cu, gold-plated)
- **Size:** Ø50 mm × 20 mm thick
- **Mounting:** M3 holes for thermal straps and DUT carrier

### Alumina Disk
- **Source:** CoorsTek / Kyocera polycrystalline Al₂O₃
- **Size:** Ø28 mm × 1.5 mm thick
- **Purpose:** Electrical isolation between cold head and sample stage

## Parametric Variables

All envelope dimensions are linked to `dimensions.ods`. Edit the spreadsheet
to update all linked parts automatically.

| Variable | Default | Unit | Description |
|----------|---------|------|-------------|
| `vessel_cf_size` | 200 | mm | DN200CF nominal |
| `vessel_id` | 200 | mm | Inner diameter |
| `vessel_length` | 400 | mm | Calculated from cold head |
| `shield_od` | 180 | mm | Radiation shield OD |
| `shield_height` | 250 | mm | Radiation shield height |
| `shield_wall` | 2 | mm | Shield wall thickness |
| `sample_stage_dia` | 50 | mm | Sample stage diameter |
| `sample_stage_thick` | 20 | mm | Sample stage thickness |
| `strap_width` | 15 | mm | Thermal strap width |
| `coax_od` | 2.2 | mm | 0.086" semi-rigid coax |

## Assembly Notes

- Cold head hangs from top plate (motor outside vacuum)
- Radiation shield thermally connected to 1st stage via Cu straps
- Sample stage thermally connected to 2nd stage via Cu straps
- Alumina disk provides electrical isolation at 4K
- All wiring routes: top plate → 40K heatsink → 4K

## Export Instructions

To generate STEP files for external sharing:

### Using build script (recommended)
```bash
./build.sh export
```
Creates `exports/cryostat-assembly.step`

### Manual export
1. Open `assembly/cryostat-assembly.FCStd` in FreeCAD
2. Select all parts in the model tree (Ctrl+A)
3. File → Export → Select STEP format
4. Save to `exports/cryostat-assembly.step`

Individual parts can be exported similarly from their respective files.

## Verification Checklist

- [ ] Cold head dimensions match RDK-101D outline drawing
- [ ] Radiation shield clears 2nd stage + sample stage + wiring
- [ ] Vessel length accommodates full cold head reach
- [ ] Assembly fits within 19" rack width (~450 mm)
- [ ] STEP exports open correctly in other CAD tools

## Calculated Vessel Length

Based on the RDK-101D cold head dimensions and required clearances:

| Component | Z Position | Notes |
|-----------|------------|-------|
| Motor top | +245 mm | Outside vacuum |
| CF flange | +25 mm | Mounts to top plate |
| Top plate | 0 mm | **Origin** |
| 1st stage (45K) | -80 mm | Thermal strap attachment |
| 2nd stage tip (4K) | -220 mm | |
| Alumina disk | -222 mm | Electrical isolation |
| Sample stage bottom | -242 mm | Lowest point |

**Recommended vessel length: 300 mm minimum**
- Current design: 400 mm (provides margin for wiring and future changes)
- 50 mm clearance below sample stage

## Related Documents

- `docs/cryostat-assembly.md` — Exploded view diagram and assembly layers
- `docs/thermal-budget.md` — Heat load calculations and shield sizing
- `specs/requirements.md` — System requirements and constraints

## Status

- [x] Folder structure created
- [x] Part scripts written (Python)
- [x] Assembly script written
- [x] Dimension spreadsheet created
- [ ] Generate .FCStd files (run `./build.sh`)
- [ ] Verify dimensions against RDK-101D datasheet
- [ ] Export STEP for Vertiv review
