#!/usr/bin/env python3
"""
FreeCAD script to generate radiation shield model.

Run in FreeCAD:
    exec(open('radiation-shield.py').read())

6061-T6 Al cylinder with bottom cap, open top for cold head access.
Parametric - can be linked to dimensions.fods spreadsheet.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector

# Create new document
doc = App.newDocument("Radiation-Shield")

# ============================================================================
# Dimensions (parametric - default values)
# These can be linked to spreadsheet in FreeCAD
# ============================================================================

# Using 12" nominal aluminum tube (COTS)
shield_od = 300.0           # mm - outer diameter (~12" tube)
shield_height = 450.0       # mm - total height (extended for 250mm sample stage)
shield_wall = 3.0           # mm - wall thickness (0.125" standard wall)
shield_bottom_thick = 5.0   # mm - bottom cap thickness

# Calculated values
shield_id = shield_od - 2 * shield_wall

# Mounting tab dimensions (for thermal strap attachment)
tab_width = 25.0    # mm
tab_height = 20.0   # mm
tab_thickness = 5.0 # mm
num_tabs = 2        # opposite sides

# Access hole for 2nd stage cold finger
access_hole_dia = 70.0  # mm (must clear 2nd stage tube Ø52 + straps)

# ============================================================================
# Create geometry
# ============================================================================

shapes = []

# Main cylinder (hollow)
outer_cyl = Part.makeCylinder(shield_od/2, shield_height, Vector(0, 0, 0))
inner_cyl = Part.makeCylinder(shield_id/2, shield_height - shield_bottom_thick,
                              Vector(0, 0, shield_bottom_thick))
shield_body = outer_cyl.cut(inner_cyl)
shapes.append(shield_body)

# Top opening for cold head access (cut a hole in top if it was solid)
# The cylinder is already open at top, but we add an access hole at top

# Access hole through top portion (for 2nd stage to pass through)
access_hole = Part.makeCylinder(access_hole_dia/2, shield_wall + 10,
                                Vector(0, 0, shield_height - shield_wall - 5))
# Note: This is for visualization - the top is already open

# Mounting tabs at top (for thermal strap connection to 1st stage)
import math

# M4 clearance hole for strap mounting
m4_clearance = 4.5  # mm

for i in range(num_tabs):
    angle = i * math.pi  # 0 and 180 degrees
    x = (shield_od/2 + tab_thickness/2) * math.cos(angle)
    y = (shield_od/2 + tab_thickness/2) * math.sin(angle)

    # Create tab as a box, then position
    tab = Part.makeBox(tab_width, tab_thickness, tab_height)
    tab.translate(Vector(-tab_width/2, -tab_thickness/2, 0))
    tab.rotate(Vector(0, 0, 0), Vector(0, 0, 1), math.degrees(angle))
    tab.translate(Vector(x, y, shield_height - tab_height))
    shapes.append(tab)

# ============================================================================
# Combine and create solid
# ============================================================================

# Fuse all shapes
shield = shapes[0]
for shape in shapes[1:]:
    shield = shield.fuse(shape)

# Cut mounting holes in tabs
for i in range(num_tabs):
    angle = i * math.pi
    # Hole position: center of tab
    tab_center_r = shield_od/2 + tab_thickness/2
    x = tab_center_r * math.cos(angle)
    y = tab_center_r * math.sin(angle)
    z = shield_height - tab_height/2

    # Hole goes through tab thickness (radial direction)
    hole_dir = Vector(math.cos(angle), math.sin(angle), 0)
    hole = Part.makeCylinder(m4_clearance/2, tab_thickness * 2,
                             Vector(x - hole_dir.x * tab_thickness,
                                    y - hole_dir.y * tab_thickness, z),
                             hole_dir)
    shield = shield.cut(hole)

# ============================================================================
# Create Part object
# ============================================================================

rad_shield = doc.addObject("Part::Feature", "RadiationShield")
rad_shield.Shape = shield
if hasattr(rad_shield, 'ViewObject') and rad_shield.ViewObject:
    rad_shield.ViewObject.ShapeColor = (0.75, 0.75, 0.8)  # Aluminum color
    rad_shield.ViewObject.Transparency = 50  # Semi-transparent for visibility

# Recompute
doc.recompute()

# Save document
doc.saveAs("radiation-shield.FCStd")

print("Created radiation shield model")
print(f"  Outer diameter: Ø{shield_od} mm")
print(f"  Inner diameter: Ø{shield_id} mm")
print(f"  Height: {shield_height} mm")
print(f"  Wall thickness: {shield_wall} mm")
print(f"  Bottom thickness: {shield_bottom_thick} mm")
print(f"  Mounting tabs: {num_tabs}×")
