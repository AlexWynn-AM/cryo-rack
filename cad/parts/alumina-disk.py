#!/usr/bin/env python3
"""
FreeCAD script to generate alumina isolation disk model.

Run in FreeCAD:
    exec(open('alumina-disk.py').read())

Polycrystalline Al2O3 disk for electrical isolation at 4K.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector

# Create new document
doc = App.newDocument("Alumina-Disk")

# ============================================================================
# Dimensions
# ============================================================================

diameter = 28.0      # mm
thickness = 1.5      # mm

# ============================================================================
# Create geometry
# ============================================================================

# Simple cylinder
disk = Part.makeCylinder(diameter/2, thickness, Vector(0, 0, 0))

# ============================================================================
# Create Part object
# ============================================================================

alumina = doc.addObject("Part::Feature", "AluminaDisk")
alumina.Shape = disk
if hasattr(alumina, 'ViewObject') and alumina.ViewObject:
    alumina.ViewObject.ShapeColor = (0.95, 0.95, 0.9)  # Off-white (ceramic)

# Recompute
doc.recompute()

# Save document
doc.saveAs("alumina-disk.FCStd")

print("Created alumina disk model")
print(f"  Diameter: Ø{diameter} mm")
print(f"  Thickness: {thickness} mm")
print(f"  Material: Polycrystalline Al₂O₃")
