#!/usr/bin/env python3
"""
FreeCAD script to generate complete cryostat assembly.

Run in FreeCAD:
    exec(open('cryostat-assembly.py').read())

Positions all parts relative to the top plate (origin at top plate bottom face).
Cold head hangs down into the vacuum vessel.

Assembly reference frame:
- Origin: Center of top plate, bottom face (vacuum side)
- Z+: Up (toward motor, outside vacuum)
- Z-: Down (into vacuum, toward 2nd stage)
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Cryostat-Assembly")

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

# ----------------------------------------------------------------------------
# Cold Head (motor outside vacuum, cold stages inside)
# ----------------------------------------------------------------------------

# Motor housing (above top plate, outside vacuum)
motor = Part.makeCylinder(motor_dia/2, motor_height,
                          Vector(0, 0, top_plate_thickness + cf_flange_thickness))
shapes_info.append(("ColdHead_Motor", motor, (0.3, 0.3, 0.35), 0))

# CF flange
cf_flange = Part.makeCylinder(114/2, cf_flange_thickness,
                              Vector(0, 0, top_plate_thickness))
shapes_info.append(("ColdHead_CFFlange", cf_flange, (0.5, 0.5, 0.55), 0))

# Transition tube (inside vacuum, from top plate down to 1st stage)
transition = Part.makeCylinder(70/2, transition_height,
                               Vector(0, 0, -transition_height))
shapes_info.append(("ColdHead_Transition", transition, (0.5, 0.5, 0.55), 0))

# First stage (45K)
z_1st = -transition_height - first_stage_height
first_stage = Part.makeCylinder(first_stage_dia/2, first_stage_height,
                                Vector(0, 0, z_1st))
shapes_info.append(("ColdHead_1stStage", first_stage, (0.4, 0.5, 0.6), 0))

# Second stage tube
z_2nd_tube = z_1st - second_stage_tube_height
tube_2nd = Part.makeCylinder(second_stage_tube_od/2, second_stage_tube_height,
                             Vector(0, 0, z_2nd_tube))
shapes_info.append(("ColdHead_2ndTube", tube_2nd, (0.5, 0.5, 0.55), 0))

# Second stage tip (4K)
z_2nd_tip = z_2nd_tube - second_stage_tip_height
tip_2nd = Part.makeCylinder(second_stage_tip_dia/2, second_stage_tip_height,
                            Vector(0, 0, z_2nd_tip))
shapes_info.append(("ColdHead_2ndTip", tip_2nd, (0.3, 0.4, 0.5), 0))

# ----------------------------------------------------------------------------
# Alumina disk (on 2nd stage tip)
# ----------------------------------------------------------------------------

z_alumina = z_2nd_tip - alumina_thick
alumina = Part.makeCylinder(alumina_dia/2, alumina_thick,
                            Vector(0, 0, z_alumina))
shapes_info.append(("AluminaDisk", alumina, (0.95, 0.95, 0.9), 0))

# ----------------------------------------------------------------------------
# Sample stage (below alumina disk)
# ----------------------------------------------------------------------------

z_sample = z_alumina - sample_stage_thick
sample_stage = Part.makeCylinder(sample_stage_dia/2, sample_stage_thick,
                                 Vector(0, 0, z_sample))
shapes_info.append(("SampleVolume", sample_stage, (0.83, 0.69, 0.22), 0))

# ----------------------------------------------------------------------------
# Radiation shield (surrounds 2nd stage and sample)
# ----------------------------------------------------------------------------

# Position: shield top near 1st stage, surrounds 2nd stage
z_shield_top = z_1st - 10  # 10mm below 1st stage
z_shield_bottom = z_shield_top - shield_height

shield_outer = Part.makeCylinder(shield_od/2, shield_height,
                                 Vector(0, 0, z_shield_bottom))
shield_inner = Part.makeCylinder(shield_od/2 - 2, shield_height - 3,
                                 Vector(0, 0, z_shield_bottom + 3))
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
                                 Vector(0, 0, z_vessel_bottom))
vessel_inner = Part.makeCylinder(vessel_id/2, vessel_length,
                                 Vector(0, 0, z_vessel_bottom))
vessel_body = vessel_outer.cut(vessel_inner)
shapes_info.append(("VacuumVessel_Body", vessel_body, (0.6, 0.6, 0.65), 50))

# Bottom flange
z_bottom_flange = z_vessel_bottom - vessel_flange_thickness
bottom_flange = Part.makeCylinder(flange_od/2, vessel_flange_thickness,
                                  Vector(0, 0, z_bottom_flange))
bottom_bore = Part.makeCylinder(vessel_id/2, vessel_flange_thickness,
                                Vector(0, 0, z_bottom_flange))
bottom_flange = bottom_flange.cut(bottom_bore)
shapes_info.append(("VacuumVessel_BottomFlange", bottom_flange, (0.6, 0.6, 0.65), 0))

# ----------------------------------------------------------------------------
# Top plate (at origin)
# ----------------------------------------------------------------------------

top_plate_outer = Part.makeCylinder(flange_od/2, top_plate_thickness,
                                    Vector(0, 0, 0))
top_plate_bore = Part.makeCylinder(70/2, top_plate_thickness,
                                   Vector(0, 0, 0))
top_plate = top_plate_outer.cut(top_plate_bore)
shapes_info.append(("TopPlate", top_plate, (0.6, 0.6, 0.65), 0))

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
print("CRYOSTAT ASSEMBLY - KEY MEASUREMENTS")
print("="*60)

total_cold_head_length = motor_height + cf_flange_thickness + transition_height + \
                         first_stage_height + second_stage_tube_height + second_stage_tip_height
print(f"\nCold Head:")
print(f"  Total length: {total_cold_head_length} mm")
print(f"  Motor top: z = +{top_plate_thickness + cf_flange_thickness + motor_height} mm")
print(f"  CF flange: z = +{top_plate_thickness} to +{top_plate_thickness + cf_flange_thickness} mm")
print(f"  1st stage (45K): z = {z_1st} to {z_1st + first_stage_height} mm")
print(f"  2nd stage tip (4K): z = {z_2nd_tip} to {z_2nd_tip + second_stage_tip_height} mm")

print(f"\nSample Stage:")
print(f"  Alumina disk: z = {z_alumina} mm")
print(f"  Sample stage: z = {z_sample} to {z_sample + sample_stage_thick} mm")
print(f"  Sample stage bottom: z = {z_sample} mm")

print(f"\nRadiation Shield:")
print(f"  Top: z = {z_shield_top} mm")
print(f"  Bottom: z = {z_shield_bottom} mm")
print(f"  OD: Ø{shield_od} mm")

print(f"\nVacuum Vessel:")
print(f"  Top flange: z = 0 mm")
print(f"  Bottom flange: z = {z_bottom_flange} mm")
print(f"  ID: Ø{vessel_id} mm")

# Clearance checks
shield_to_vessel_gap = (vessel_id - shield_od) / 2
sample_clearance = z_sample - z_shield_bottom
cold_head_clearance = z_bottom_flange - z_sample

print(f"\nClearances:")
print(f"  Shield to vessel wall: {shield_to_vessel_gap} mm (radial)")
print(f"  Sample to shield bottom: {sample_clearance} mm")
print(f"  Cold head reach vs vessel: {cold_head_clearance} mm (margin)")

# Recommended vessel length
min_vessel_length = abs(z_sample) + 50  # 50mm margin below sample
print(f"\nRecommended vessel length: {min_vessel_length} mm (current: {vessel_length} mm)")

if vessel_length >= min_vessel_length:
    print("  ✓ Vessel length is adequate")
else:
    print(f"  ✗ WARNING: Vessel too short! Need {min_vessel_length - vessel_length} mm more")

# Rack fit check
print(f"\nRack Fit (19\" = 482mm panel, ~450mm between rails):")
print(f"  Vessel flange OD: Ø{flange_od} mm")
print(f"  Clearance to rack rails: {(450 - flange_od)/2} mm each side")
if flange_od < 450:
    print("  ✓ Fits in 19\" rack")
else:
    print("  ✗ WARNING: May not fit in standard 19\" rack")

print("\n" + "="*60)

# Recompute
doc.recompute()

# Save document
doc.saveAs("cryostat-assembly.FCStd")

print("\nAssembly saved to cryostat-assembly.FCStd")
