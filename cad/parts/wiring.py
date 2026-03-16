#!/usr/bin/env python3
"""
FreeCAD script to generate wiring models.

Run in FreeCAD:
    exec(open('wiring.py').read())

Simplified representations of:
- DC wire loom (16× PhBr 36AWG bundled)
- RF coax cables (4× 0.086" SS semi-rigid)

These are representative paths, not exact geometry.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Wiring")

# ============================================================================
# Dimensions
# ============================================================================

# Wire loom (DC wires bundled)
wire_loom_dia = 8.0      # mm - bundle diameter
wire_300k_to_40k = 200.0 # mm - from top plate to 40K heatsink
wire_40k_to_4k = 150.0   # mm - from 40K heatsink to sample

# Coax cables
coax_od = 2.2            # mm - 0.086" semi-rigid
num_coax = 4
coax_spacing = 8.0       # mm - spacing between cables

# Path geometry (simplified as straight sections with bends)
heatsink_z = -100.0      # mm - position of 40K heatsink (relative to top plate)
sample_z = -250.0        # mm - position of sample stage

# ============================================================================
# Helper functions
# ============================================================================

def set_color(obj, color):
    """Set object color (only works in GUI mode)."""
    if hasattr(obj, 'ViewObject') and obj.ViewObject:
        obj.ViewObject.ShapeColor = color

def make_cable_path(diameter, length, start_pos):
    """Create a simplified vertical cable section."""
    cable = Part.makeCylinder(diameter/2, length, start_pos, Vector(0, 0, -1))
    return cable

def make_helix_section(diameter, turns, pitch, radius, start_pos):
    """Create a helix section for heatsinking wrap."""
    # Simplified: just use a small coil at heatsink position
    helix_height = turns * pitch
    points = []
    for i in range(int(turns * 36)):  # 36 points per turn
        angle = i * (2 * math.pi / 36)
        z = start_pos.z - (i / 36.0) * pitch
        x = start_pos.x + radius * math.cos(angle)
        y = start_pos.y + radius * math.sin(angle)
        points.append(Vector(x, y, z))

    if len(points) > 1:
        wire = Part.makePolygon(points)
        pipe = Part.Wire(wire).makePipeShell([Part.makeCircle(diameter/2)], True, True)
        return pipe
    return Part.makeSphere(diameter/2, start_pos)

# ============================================================================
# Create wire loom
# ============================================================================

# Wire loom: top plate to 40K heatsink
loom_top = Part.makeCylinder(wire_loom_dia/2, wire_300k_to_40k,
                             Vector(30, 0, 0), Vector(0, 0, -1))
loom_top_obj = doc.addObject("Part::Feature", "WireLoom_300K_40K")
loom_top_obj.Shape = loom_top
set_color(loom_top_obj, (0.4, 0.3, 0.2))  # Dark bronze (PhBr)

# Wire loom: 40K to 4K
loom_bottom = Part.makeCylinder(wire_loom_dia/2, wire_40k_to_4k,
                                Vector(30, 0, heatsink_z), Vector(0, 0, -1))
loom_bottom_obj = doc.addObject("Part::Feature", "WireLoom_40K_4K")
loom_bottom_obj.Shape = loom_bottom
set_color(loom_bottom_obj, (0.4, 0.3, 0.2))

# ============================================================================
# Create coax cables
# ============================================================================

# Arrange coax in a row
coax_start_x = -((num_coax - 1) * coax_spacing / 2) - 30  # Offset from wire loom

for i in range(num_coax):
    x_pos = coax_start_x + i * coax_spacing

    # Top section: 300K to 40K
    coax_top = Part.makeCylinder(coax_od/2, wire_300k_to_40k,
                                 Vector(x_pos, 20, 0), Vector(0, 0, -1))
    coax_top_obj = doc.addObject("Part::Feature", f"Coax{i+1}_300K_40K")
    coax_top_obj.Shape = coax_top
    set_color(coax_top_obj, (0.7, 0.7, 0.75))  # Stainless

    # Bottom section: 40K to 4K
    coax_bottom = Part.makeCylinder(coax_od/2, wire_40k_to_4k,
                                    Vector(x_pos, 20, heatsink_z), Vector(0, 0, -1))
    coax_bottom_obj = doc.addObject("Part::Feature", f"Coax{i+1}_40K_4K")
    coax_bottom_obj.Shape = coax_bottom
    set_color(coax_bottom_obj, (0.7, 0.7, 0.75))

# ============================================================================
# Create heatsink representation (simple ring)
# ============================================================================

heatsink_outer = Part.makeTorus(25, 5, Vector(0, 0, heatsink_z))
heatsink_obj = doc.addObject("Part::Feature", "Heatsink_40K")
heatsink_obj.Shape = heatsink_outer
set_color(heatsink_obj, (0.83, 0.69, 0.22))  # Copper

# Recompute
doc.recompute()

# Save document
doc.saveAs("wiring.FCStd")

print("Created wiring models")
print(f"  Wire loom diameter: Ø{wire_loom_dia} mm (16× PhBr 36AWG)")
print(f"  Coax cables: {num_coax}× Ø{coax_od} mm (0.086\" SS)")
print(f"  300K→40K length: {wire_300k_to_40k} mm")
print(f"  40K→4K length: {wire_40k_to_4k} mm")
