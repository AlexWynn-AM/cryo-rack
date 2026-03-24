#!/usr/bin/env python3
"""
FreeCAD script to generate complete cryostat assembly with server rack.

Run in FreeCAD:
    exec(open('cryostat-assembly.py').read())

Positions cryostat inside a 42U server rack.
Cryostat top plate mounts at a specified rack unit position.

Assembly reference frame:
- Origin: Floor level at center of rack
- Z+: Up
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Cryostat-Assembly")

# ============================================================================
# Rack dimensions (from server-rack.py)
# ============================================================================

rack_units = 42
rack_width = 600.0           # mm
rack_depth = 1100.0          # mm
u_height = 44.45             # mm
rail_width = 15.875          # mm
rail_spacing = 465.1         # mm
post_size = 50.0
frame_height = 50.0
base_height = 100.0
top_clearance = 50.0
usable_height = rack_units * u_height
total_rack_height = base_height + usable_height + top_clearance + frame_height

# Cryostat mounting position in rack
# Mount top plate at U35 (near top, leaves ~7U for motor + clearance)
mount_u = 35
z_mount = base_height + frame_height + (mount_u - 1) * u_height

# Cryostat Z offset: position top plate bottom face at mount height
cryostat_z_offset = z_mount

# CNA-11R Compressor dimensions
compressor_height = 400.0     # mm (~9U)
compressor_width = 484.0      # mm (19" rack)
compressor_depth = 540.0      # mm
compressor_u = 1              # Mount at U1 (bottom of rack)
compressor_z = base_height + frame_height + (compressor_u - 1) * u_height

# ============================================================================
# Key dimensions for positioning (from individual part scripts)
# ============================================================================

# Top plate
top_plate_thickness = 25.0    # mm

# Cold head
motor_height = 200.0          # mm (above CF flange)
cf_flange_thickness = 20.0    # mm
transition_height = 50.0      # mm
first_stage_height = 30.0     # mm
second_stage_tube_height = 100.0  # mm
second_stage_tip_height = 40.0    # mm

# Calculated positions
first_stage_z = -(transition_height + first_stage_height)
second_stage_tip_z = first_stage_z - first_stage_height - second_stage_tube_height - second_stage_tip_height

# Vessel (DN320CF)
vessel_length = 550.0         # mm (extended for 250mm sample stage)
vessel_flange_thickness = 22.0  # mm

# Radiation shield (12" aluminum tube)
shield_height = 450.0         # mm (extended for 250mm sample stage)
shield_od = 300.0             # mm

# Sample stage (large cylindrical envelope)
sample_stage_thick = 250.0    # mm (height)
alumina_thick = 1.5           # mm

# ============================================================================
# Part dimensions (simplified for assembly positioning)
# ============================================================================

# Motor housing
motor_dia = 130.0
# First stage
first_stage_dia = 108.0
# Second stage
second_stage_tube_od = 52.0
second_stage_tip_dia = 45.0
# Vessel (DN320CF)
vessel_od = 324.0
vessel_id = 320.0
flange_od = 368.0
# Sample stage (large cylindrical envelope)
sample_stage_dia = 250.0
# Alumina
alumina_dia = 28.0

# ============================================================================
# Create simplified geometry for assembly visualization
# ============================================================================

shapes_info = []  # [(name, shape, color, transparency), ...]

# ============================================================================
# Server Rack Frame
# ============================================================================

# Post positions
post_x = (rack_width - post_size) / 2
post_y = (rack_depth - post_size) / 2
post_wall = 3.0
rail_x = rail_spacing / 2

rack_shapes = []

# Four corner posts
for px, py in [(-post_x, -post_y), (+post_x, -post_y),
               (-post_x, +post_y), (+post_x, +post_y)]:
    post_outer = Part.makeBox(post_size, post_size, total_rack_height,
                              Vector(px - post_size/2, py - post_size/2, 0))
    post_inner = Part.makeBox(post_size - 2*post_wall, post_size - 2*post_wall,
                              total_rack_height,
                              Vector(px - post_size/2 + post_wall,
                                     py - post_size/2 + post_wall, 0))
    rack_shapes.append(post_outer.cut(post_inner))

# Top frame bars
z_top = total_rack_height - frame_height
for py in [-post_y, +post_y]:
    bar = Part.makeBox(rack_width - post_size, post_size, frame_height,
                       Vector(-post_x + post_size/2, py - post_size/2, z_top))
    rack_shapes.append(bar)
for px in [-post_x, +post_x]:
    bar = Part.makeBox(post_size, rack_depth - post_size, frame_height,
                       Vector(px - post_size/2, -post_y + post_size/2, z_top))
    rack_shapes.append(bar)

# Bottom frame bars
for py in [-post_y, +post_y]:
    bar = Part.makeBox(rack_width - post_size, post_size, frame_height,
                       Vector(-post_x + post_size/2, py - post_size/2, 0))
    rack_shapes.append(bar)
for px in [-post_x, +post_x]:
    bar = Part.makeBox(post_size, rack_depth - post_size, frame_height,
                       Vector(px - post_size/2, -post_y + post_size/2, 0))
    rack_shapes.append(bar)

# 19" mounting rails (front)
rail_height = usable_height + 20
z_rail = base_height + frame_height - 10
for rx in [-rail_x, +rail_x]:
    ry = -post_y + post_size/2 + 20
    rail = Part.makeBox(rail_width, rail_width, rail_height,
                        Vector(rx - rail_width/2, ry - rail_width/2, z_rail))
    rack_shapes.append(rail)

# Rear rails
for rx in [-rail_x, +rail_x]:
    ry = +post_y - post_size/2 - 20
    rail = Part.makeBox(rail_width, rail_width, rail_height,
                        Vector(rx - rail_width/2, ry - rail_width/2, z_rail))
    rack_shapes.append(rail)

# Casters
for px, py in [(-post_x, -post_y), (+post_x, -post_y),
               (-post_x, +post_y), (+post_x, +post_y)]:
    caster = Part.makeCylinder(37.5, base_height - 10, Vector(px, py, 0))
    rack_shapes.append(caster)

# Combine rack
rack = rack_shapes[0]
for s in rack_shapes[1:]:
    rack = rack.fuse(s)
shapes_info.append(("ServerRack", rack, (0.2, 0.2, 0.25), 0))

# ----------------------------------------------------------------------------
# CNA-11R Compressor (at bottom of rack)
# ----------------------------------------------------------------------------

comp_shapes = []

# Main enclosure body (centered in rack, toward front)
comp_y_offset = -rack_depth/2 + post_size + 50  # Near front of rack
comp_body = Part.makeBox(compressor_width, compressor_depth, compressor_height,
                         Vector(-compressor_width/2, comp_y_offset, compressor_z))
# Hollow it out
comp_wall = 2.0
comp_inner = Part.makeBox(compressor_width - 2*comp_wall,
                          compressor_depth - 2*comp_wall,
                          compressor_height - 2*comp_wall,
                          Vector(-compressor_width/2 + comp_wall,
                                 comp_y_offset + comp_wall,
                                 compressor_z + comp_wall))
comp_body = comp_body.cut(comp_inner)
comp_shapes.append(comp_body)

# Rack mounting ears
panel_width = 482.6
ear_width = 15.0
ear_thick = 3.0
for side in [-1, 1]:
    x_pos = side * (panel_width/2)
    ear = Part.makeBox(ear_width, ear_thick, compressor_height,
                       Vector(x_pos - (ear_width if side > 0 else 0),
                              comp_y_offset - ear_thick,
                              compressor_z))
    comp_shapes.append(ear)

# Helium ports (rear)
port_y = comp_y_offset + compressor_depth
for x_off in [-40, 40]:
    port = Part.makeCylinder(10, 30,
                             Vector(x_off, port_y, compressor_z + compressor_height/2),
                             Vector(0, 1, 0))
    comp_shapes.append(port)

# Combine compressor
compressor = comp_shapes[0]
for s in comp_shapes[1:]:
    compressor = compressor.fuse(s)
shapes_info.append(("CNA11R_Compressor", compressor, (0.15, 0.15, 0.18), 0))

# ----------------------------------------------------------------------------
# Cold Head (motor outside vacuum, cold stages inside)
# All cryostat parts offset by cryostat_z_offset
# ----------------------------------------------------------------------------

# Motor housing (above top plate, outside vacuum)
motor = Part.makeCylinder(motor_dia/2, motor_height,
                          Vector(0, 0, cryostat_z_offset + top_plate_thickness + cf_flange_thickness))
shapes_info.append(("ColdHead_Motor", motor, (0.3, 0.3, 0.35), 0))

# CF flange
cf_flange = Part.makeCylinder(114/2, cf_flange_thickness,
                              Vector(0, 0, cryostat_z_offset + top_plate_thickness))
shapes_info.append(("ColdHead_CFFlange", cf_flange, (0.5, 0.5, 0.55), 0))

# Transition tube (inside vacuum, from top plate down to 1st stage)
transition = Part.makeCylinder(70/2, transition_height,
                               Vector(0, 0, cryostat_z_offset - transition_height))
shapes_info.append(("ColdHead_Transition", transition, (0.5, 0.5, 0.55), 0))

# First stage (45K)
z_1st = -transition_height - first_stage_height
first_stage = Part.makeCylinder(first_stage_dia/2, first_stage_height,
                                Vector(0, 0, cryostat_z_offset + z_1st))
shapes_info.append(("ColdHead_1stStage", first_stage, (0.4, 0.5, 0.6), 0))

# Second stage tube
z_2nd_tube = z_1st - second_stage_tube_height
tube_2nd = Part.makeCylinder(second_stage_tube_od/2, second_stage_tube_height,
                             Vector(0, 0, cryostat_z_offset + z_2nd_tube))
shapes_info.append(("ColdHead_2ndTube", tube_2nd, (0.5, 0.5, 0.55), 0))

# Second stage tip (4K)
z_2nd_tip = z_2nd_tube - second_stage_tip_height
tip_2nd = Part.makeCylinder(second_stage_tip_dia/2, second_stage_tip_height,
                            Vector(0, 0, cryostat_z_offset + z_2nd_tip))
shapes_info.append(("ColdHead_2ndTip", tip_2nd, (0.3, 0.4, 0.5), 0))

# ----------------------------------------------------------------------------
# Alumina disk (on 2nd stage tip)
# ----------------------------------------------------------------------------

z_alumina = z_2nd_tip - alumina_thick
alumina = Part.makeCylinder(alumina_dia/2, alumina_thick,
                            Vector(0, 0, cryostat_z_offset + z_alumina))
shapes_info.append(("AluminaDisk", alumina, (0.95, 0.95, 0.9), 0))

# ----------------------------------------------------------------------------
# Sample stage (below alumina disk)
# ----------------------------------------------------------------------------

z_sample = z_alumina - sample_stage_thick
sample_stage = Part.makeCylinder(sample_stage_dia/2, sample_stage_thick,
                                 Vector(0, 0, cryostat_z_offset + z_sample))
shapes_info.append(("SampleVolume", sample_stage, (0.83, 0.69, 0.22), 0))

# ----------------------------------------------------------------------------
# Radiation shield (surrounds 2nd stage and sample)
# ----------------------------------------------------------------------------

# Position: shield top near 1st stage, surrounds 2nd stage
z_shield_top = z_1st - 10  # 10mm below 1st stage
z_shield_bottom = z_shield_top - shield_height

shield_outer = Part.makeCylinder(shield_od/2, shield_height,
                                 Vector(0, 0, cryostat_z_offset + z_shield_bottom))
shield_inner = Part.makeCylinder(shield_od/2 - 2, shield_height - 3,
                                 Vector(0, 0, cryostat_z_offset + z_shield_bottom + 3))
shield = shield_outer.cut(shield_inner)
shapes_info.append(("RadiationShield", shield, (0.75, 0.75, 0.8), 60))

# ----------------------------------------------------------------------------
# Vacuum vessel
# ----------------------------------------------------------------------------

# Position vessel so top flange mates with top plate
z_vessel_top = 0
z_vessel_bottom = -vessel_length

# Vessel body
vessel_outer = Part.makeCylinder(vessel_od/2, vessel_length,
                                 Vector(0, 0, cryostat_z_offset + z_vessel_bottom))
vessel_inner = Part.makeCylinder(vessel_id/2, vessel_length,
                                 Vector(0, 0, cryostat_z_offset + z_vessel_bottom))
vessel_body = vessel_outer.cut(vessel_inner)
shapes_info.append(("VacuumVessel_Body", vessel_body, (0.6, 0.6, 0.65), 50))

# Bottom flange
z_bottom_flange = z_vessel_bottom - vessel_flange_thickness
bottom_flange = Part.makeCylinder(flange_od/2, vessel_flange_thickness,
                                  Vector(0, 0, cryostat_z_offset + z_bottom_flange))
bottom_bore = Part.makeCylinder(vessel_id/2, vessel_flange_thickness,
                                Vector(0, 0, cryostat_z_offset + z_bottom_flange))
bottom_flange = bottom_flange.cut(bottom_bore)
shapes_info.append(("VacuumVessel_BottomFlange", bottom_flange, (0.6, 0.6, 0.65), 0))

# ----------------------------------------------------------------------------
# Top plate (at mount position)
# ----------------------------------------------------------------------------

top_plate_outer = Part.makeCylinder(flange_od/2, top_plate_thickness,
                                    Vector(0, 0, cryostat_z_offset))
top_plate_bore = Part.makeCylinder(70/2, top_plate_thickness,
                                   Vector(0, 0, cryostat_z_offset))
top_plate = top_plate_outer.cut(top_plate_bore)
shapes_info.append(("TopPlate", top_plate, (0.6, 0.6, 0.65), 0))

# ----------------------------------------------------------------------------
# Sheet metal mounting frame (solid plate with cutout + bent tabs)
# ----------------------------------------------------------------------------

# Rail positions (must match rack geometry)
front_rail_y = -post_y + post_size/2 + 20  # where front rails are
rear_rail_y = +post_y - post_size/2 - 20   # where rear rails are

# Frame dimensions - simple solid plate
plate_thick = 6.0             # mm - 6mm steel plate (1/4")
plate_width = rail_spacing + 100  # mm - extends past rails for mounting tabs
plate_depth = rear_rail_y - front_rail_y + 80  # mm - spans between rails
plate_y_start = front_rail_y - 40
frame_z = cryostat_z_offset - plate_thick  # sits just below top plate

# Main plate
plate = Part.makeBox(plate_width, plate_depth, plate_thick,
                     Vector(-plate_width/2, plate_y_start, frame_z))

# Cut center hole for vessel (slightly smaller than flange so flange rests on lip)
vessel_hole_dia = flange_od - 40  # 40mm lip to support flange
vessel_hole = Part.makeCylinder(vessel_hole_dia/2, plate_thick + 10,
                                Vector(0, 0, frame_z - 5))
plate = plate.cut(vessel_hole)

# Cut corner relief holes (reduces stress, easier to bend)
corner_hole_dia = 20.0
corner_positions = [
    (-plate_width/2 + 60, plate_y_start + 60),
    (+plate_width/2 - 60, plate_y_start + 60),
    (-plate_width/2 + 60, plate_y_start + plate_depth - 60),
    (+plate_width/2 - 60, plate_y_start + plate_depth - 60),
]
for cx, cy in corner_positions:
    corner_hole = Part.makeCylinder(corner_hole_dia/2, plate_thick + 10,
                                    Vector(cx, cy, frame_z - 5))
    plate = plate.cut(corner_hole)

# Bent mounting tabs (4 tabs, one at each rail position)
tab_height = 4 * u_height  # 4U tall
tab_width = 44.0           # mm - fits between rack holes
tab_thick = plate_thick    # same thickness (bent from plate)

# Front tabs (bent down toward front)
for side in [-1, 1]:
    x_pos = side * (rail_spacing/2)

    # Vertical tab (bent 90 degrees down)
    tab = Part.makeBox(tab_width, tab_thick, tab_height,
                       Vector(x_pos - tab_width/2,
                              front_rail_y - rail_width/2 - tab_thick,
                              frame_z - tab_height))

    # M6 mounting holes (4 per tab at standard rack spacing)
    for i in range(4):
        hole_z = frame_z - u_height/2 - i * u_height
        hole = Part.makeCylinder(3.2, tab_thick + 10,
                                 Vector(x_pos, front_rail_y - rail_width/2 - tab_thick - 5, hole_z),
                                 Vector(0, 1, 0))
        tab = tab.cut(hole)

    plate = plate.fuse(tab)

# Rear tabs (bent down toward rear)
for side in [-1, 1]:
    x_pos = side * (rail_spacing/2)

    tab = Part.makeBox(tab_width, tab_thick, tab_height,
                       Vector(x_pos - tab_width/2,
                              rear_rail_y + rail_width/2,
                              frame_z - tab_height))

    for i in range(4):
        hole_z = frame_z - u_height/2 - i * u_height
        hole = Part.makeCylinder(3.2, tab_thick + 10,
                                 Vector(x_pos, rear_rail_y + rail_width/2 + tab_thick + 5, hole_z),
                                 Vector(0, -1, 0))
        tab = tab.cut(hole)

    plate = plate.fuse(tab)

# Add gussets for tab reinforcement (triangular braces)
gusset_size = 50.0
gusset_thick = plate_thick

for side in [-1, 1]:
    x_pos = side * (rail_spacing/2)

    # Front gussets (left and right of each tab)
    for tab_side in [-1, 1]:
        gusset_x = x_pos + tab_side * (tab_width/2)
        # Create triangular gusset using points
        gusset_pts = [
            Vector(gusset_x, front_rail_y - rail_width/2 - tab_thick, frame_z),
            Vector(gusset_x, front_rail_y - rail_width/2 - tab_thick, frame_z - gusset_size),
            Vector(gusset_x, front_rail_y - rail_width/2 - tab_thick + gusset_size, frame_z),
        ]
        gusset_wire = Part.makePolygon(gusset_pts + [gusset_pts[0]])
        gusset_face = Part.Face(gusset_wire)
        gusset = gusset_face.extrude(Vector(tab_side * gusset_thick, 0, 0))
        plate = plate.fuse(gusset)

    # Rear gussets
    for tab_side in [-1, 1]:
        gusset_x = x_pos + tab_side * (tab_width/2)
        gusset_pts = [
            Vector(gusset_x, rear_rail_y + rail_width/2 + tab_thick, frame_z),
            Vector(gusset_x, rear_rail_y + rail_width/2 + tab_thick, frame_z - gusset_size),
            Vector(gusset_x, rear_rail_y + rail_width/2 + tab_thick - gusset_size, frame_z),
        ]
        gusset_wire = Part.makePolygon(gusset_pts + [gusset_pts[0]])
        gusset_face = Part.Face(gusset_wire)
        gusset = gusset_face.extrude(Vector(tab_side * gusset_thick, 0, 0))
        plate = plate.fuse(gusset)

shapes_info.append(("MountingFrame", plate, (0.45, 0.5, 0.55), 0))

# Note: Thermal straps (Cu braid) are purchased items, not modeled.
# Mounting holes for straps are on: 1st stage, radiation shield tabs,
# 2nd stage, and sample volume tabs.

# ============================================================================
# Create Part objects
# ============================================================================

for name, shape, color, transparency in shapes_info:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if hasattr(obj, 'ViewObject') and obj.ViewObject:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
        obj.ViewObject.Visibility = True

# ============================================================================
# Set up view (if GUI is available)
# ============================================================================

try:
    import FreeCADGui
    if FreeCADGui.ActiveDocument:
        FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        FreeCADGui.updateGui()
except:
    pass  # Running in console mode, no GUI available

# ============================================================================
# Add annotation with key dimensions
# ============================================================================

# Calculate and print key measurements
print("\n" + "="*60)
print("CRYOSTAT ASSEMBLY WITH RACK - KEY MEASUREMENTS")
print("="*60)

print(f"\nServer Rack (42U):")
print(f"  Dimensions: {rack_width} × {rack_depth} × {total_rack_height:.1f} mm")
print(f"  Rail spacing: {rail_spacing} mm (19\" standard)")
print(f"  Usable height: {usable_height:.1f} mm ({rack_units}U)")

compressor_top_z = compressor_z + compressor_height
compressor_u_count = round(compressor_height / u_height)
print(f"\nCNA-11R Compressor:")
print(f"  Position: U{compressor_u} - U{compressor_u + compressor_u_count} ({compressor_u_count}U)")
print(f"  Dimensions: {compressor_height} × {compressor_width} × {compressor_depth} mm")
print(f"  Z range: {compressor_z:.1f} - {compressor_top_z:.1f} mm")

print(f"\nCryostat Mounting:")
print(f"  Top plate at: U{mount_u} (z = {z_mount:.1f} mm from floor)")
print(f"  Motor top: z = {cryostat_z_offset + top_plate_thickness + cf_flange_thickness + motor_height:.1f} mm")
print(f"  Vessel bottom: z = {cryostat_z_offset + z_bottom_flange:.1f} mm")

total_cold_head_length = motor_height + cf_flange_thickness + transition_height + \
                         first_stage_height + second_stage_tube_height + second_stage_tip_height
print(f"\nCold Head:")
print(f"  Total length: {total_cold_head_length} mm")
print(f"  1st stage (45K): z = {cryostat_z_offset + z_1st:.1f} mm (global)")
print(f"  2nd stage tip (4K): z = {cryostat_z_offset + z_2nd_tip:.1f} mm (global)")

print(f"\nSample Volume:")
print(f"  Top: z = {cryostat_z_offset + z_alumina:.1f} mm")
print(f"  Bottom: z = {cryostat_z_offset + z_sample:.1f} mm")

# Clearance checks
shield_to_vessel_gap = (vessel_id - shield_od) / 2
sample_clearance = z_sample - z_shield_bottom
cold_head_clearance = z_bottom_flange - z_sample

print(f"\nClearances:")
print(f"  Shield to vessel wall: {shield_to_vessel_gap} mm (radial)")
print(f"  Sample to shield bottom: {sample_clearance} mm")
print(f"  Cryostat to floor: {cryostat_z_offset + z_bottom_flange:.1f} mm")

# Rack fit check
print(f"\nRack Fit Check:")
print(f"  Vessel flange OD: Ø{flange_od} mm")
print(f"  Rail clearance: {rail_spacing - rail_width:.1f} mm available")
print(f"  Flange clearance: {(rail_spacing - rail_width - flange_od)/2:.1f} mm each side")
if flange_od < rail_spacing - rail_width:
    print("  ✓ Cryostat fits between rails")
else:
    print("  ✗ WARNING: Cryostat may not fit between rails")

# Height check
motor_top_z = cryostat_z_offset + top_plate_thickness + cf_flange_thickness + motor_height
if motor_top_z < total_rack_height - frame_height:
    print(f"  ✓ Motor clears top of rack ({total_rack_height - frame_height - motor_top_z:.1f} mm margin)")
else:
    print(f"  ✗ WARNING: Motor extends above rack!")

vessel_bottom_z = cryostat_z_offset + z_bottom_flange
if vessel_bottom_z > base_height:
    print(f"  ✓ Vessel clears floor ({vessel_bottom_z - base_height:.1f} mm margin)")
else:
    print(f"  ✗ WARNING: Vessel extends below rack base!")

print("\n" + "="*60)

# Recompute
doc.recompute()

# Save document
doc.saveAs("cryostat-assembly.FCStd")

print("\nAssembly saved to cryostat-assembly.FCStd")

# ============================================================================
# Export STEP file
# ============================================================================

import os
import Import

script_dir = os.path.dirname(os.path.abspath(__file__))
export_dir = os.path.join(script_dir, "..", "exports")
os.makedirs(export_dir, exist_ok=True)
step_path = os.path.join(export_dir, "cryostat-assembly.step")

objs = [obj for obj in doc.Objects if hasattr(obj, "Shape")]
Import.export(objs, step_path)
print(f"STEP exported to {step_path}")
