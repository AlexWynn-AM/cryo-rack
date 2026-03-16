#!/usr/bin/env python3
"""
FreeCAD script to generate thermal strap models.

Run in FreeCAD:
    exec(open('thermal-straps.py').read())

Simplified OFHC Cu braid straps:
- 2× from 1st stage to radiation shield
- 2× from 2nd stage to sample stage
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Thermal-Straps")

# ============================================================================
# Dimensions
# ============================================================================

# Strap cross-section
strap_width = 15.0    # mm
strap_thick = 3.0     # mm

# Strap lengths (simplified - actual geometry is flexible braid)
strap_1st_length = 60.0   # mm - 1st stage to shield
strap_2nd_length = 40.0   # mm - 2nd stage to sample

# Mounting lug dimensions
lug_width = 20.0      # mm
lug_length = 15.0     # mm
lug_hole_dia = 4.2    # mm (M4 clearance)

# ============================================================================
# Helper function to create a strap
# ============================================================================

def make_strap(length, with_bend=False, bend_radius=15.0):
    """Create a simplified strap with optional bend."""

    shapes = []

    # Main braid section (simplified as rectangular box)
    braid = Part.makeBox(strap_width, length, strap_thick)
    braid.translate(Vector(-strap_width/2, 0, 0))
    shapes.append(braid)

    # Bottom lug
    bottom_lug = Part.makeBox(lug_width, lug_length, strap_thick)
    bottom_lug.translate(Vector(-lug_width/2, -lug_length, 0))
    # Lug hole
    bottom_hole = Part.makeCylinder(lug_hole_dia/2, strap_thick,
                                    Vector(0, -lug_length/2, 0))
    bottom_lug = bottom_lug.cut(bottom_hole)
    shapes.append(bottom_lug)

    # Top lug
    top_lug = Part.makeBox(lug_width, lug_length, strap_thick)
    top_lug.translate(Vector(-lug_width/2, length, 0))
    # Lug hole
    top_hole = Part.makeCylinder(lug_hole_dia/2, strap_thick,
                                 Vector(0, length + lug_length/2, 0))
    top_lug = top_lug.cut(top_hole)
    shapes.append(top_lug)

    # Combine
    strap = shapes[0]
    for s in shapes[1:]:
        strap = strap.fuse(s)

    return strap

# ============================================================================
# Helper to set view properties (only works in GUI mode)
# ============================================================================

def set_color(obj, color):
    if hasattr(obj, 'ViewObject') and obj.ViewObject:
        obj.ViewObject.ShapeColor = color

# ============================================================================
# Create straps
# ============================================================================

COPPER_COLOR = (0.83, 0.69, 0.22)

# 1st stage straps (to radiation shield) - 2×
strap1a = make_strap(strap_1st_length)
strap1a_obj = doc.addObject("Part::Feature", "Strap_1st_A")
strap1a_obj.Shape = strap1a
set_color(strap1a_obj, COPPER_COLOR)

strap1b = make_strap(strap_1st_length)
strap1b.rotate(Vector(0, 0, 0), Vector(0, 0, 1), 180)  # Opposite side
strap1b_obj = doc.addObject("Part::Feature", "Strap_1st_B")
strap1b_obj.Shape = strap1b
set_color(strap1b_obj, COPPER_COLOR)

# 2nd stage straps (to sample stage) - 2×
strap2a = make_strap(strap_2nd_length)
strap2a.translate(Vector(100, 0, 0))  # Offset for visibility
strap2a_obj = doc.addObject("Part::Feature", "Strap_2nd_A")
strap2a_obj.Shape = strap2a
set_color(strap2a_obj, COPPER_COLOR)

strap2b = make_strap(strap_2nd_length)
strap2b.rotate(Vector(0, 0, 0), Vector(0, 0, 1), 180)
strap2b.translate(Vector(100, 0, 0))  # Offset for visibility
strap2b_obj = doc.addObject("Part::Feature", "Strap_2nd_B")
strap2b_obj.Shape = strap2b
set_color(strap2b_obj, COPPER_COLOR)

# Recompute
doc.recompute()

# Save document
doc.saveAs("thermal-straps.FCStd")

print("Created thermal strap models")
print(f"  1st stage straps: 2× length {strap_1st_length} mm")
print(f"  2nd stage straps: 2× length {strap_2nd_length} mm")
print(f"  Cross-section: {strap_width} × {strap_thick} mm")
print(f"  Material: OFHC Cu braid")
