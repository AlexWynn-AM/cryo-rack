#!/usr/bin/env python3
"""
FreeCAD script to generate sample volume model.

Run in FreeCAD:
    exec(open('sample-stage.py').read())

Large cylindrical sample volume envelope.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Sample-Volume")

# ============================================================================
# Dimensions
# ============================================================================

# Main cylinder (large sample envelope)
diameter = 250.0     # mm
thickness = 250.0    # mm (height)

# Thermal strap mounting tabs at top
tab_width = 25.0     # mm
tab_length = 20.0    # mm (radial extension)
tab_thickness = 10.0 # mm
num_tabs = 2         # opposite sides
m4_clearance = 4.5   # mm

# ============================================================================
# Create geometry
# ============================================================================

# Main cylinder
volume = Part.makeCylinder(diameter/2, thickness, Vector(0, 0, 0))

# Add mounting tabs at top for thermal strap connection
for i in range(num_tabs):
    angle = math.radians(90 + i * 180)  # 90 and 270 degrees (match 2nd stage holes)

    # Tab extends radially outward from top of cylinder
    tab = Part.makeBox(tab_length, tab_width, tab_thickness)
    tab.translate(Vector(0, -tab_width/2, thickness - tab_thickness))
    tab.rotate(Vector(0, 0, 0), Vector(0, 0, 1), math.degrees(angle))
    tab.translate(Vector((diameter/2) * math.cos(angle),
                         (diameter/2) * math.sin(angle), 0))
    volume = volume.fuse(tab)

# Cut mounting holes in tabs
for i in range(num_tabs):
    angle = math.radians(90 + i * 180)
    # Hole at center of tab
    hole_r = diameter/2 + tab_length/2
    x = hole_r * math.cos(angle)
    y = hole_r * math.sin(angle)
    z = thickness - tab_thickness/2

    hole = Part.makeCylinder(m4_clearance/2, tab_thickness * 2,
                             Vector(x, y, thickness - tab_thickness - 1),
                             Vector(0, 0, 1))
    volume = volume.cut(hole)

# ============================================================================
# Create Part object
# ============================================================================

sample_volume = doc.addObject("Part::Feature", "SampleVolume")
sample_volume.Shape = volume
if hasattr(sample_volume, 'ViewObject') and sample_volume.ViewObject:
    sample_volume.ViewObject.ShapeColor = (0.83, 0.69, 0.22)  # Gold color (Cu)

# Recompute
doc.recompute()

# Save document
doc.saveAs("sample-stage.FCStd")

print("Created sample volume model")
print(f"  Diameter: Ø{diameter} mm")
print(f"  Height: {thickness} mm")
print(f"  Mounting tabs: {num_tabs}× with M4 holes")
