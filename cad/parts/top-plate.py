#!/usr/bin/env python3
"""
FreeCAD script to generate top plate model.

Run in FreeCAD:
    exec(open('top-plate.py').read())

DN200CF top plate with center bore for cold head (DN63CF)
and feedthrough ports arranged around center.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Top-Plate")

# ============================================================================
# Dimensions
# ============================================================================

# Main plate (DN320CF compatible)
plate_od = 368.0         # mm (14.5" CF flange OD)
plate_thickness = 28.0   # mm (thicker for structural rigidity)

# Bolt pattern (DN320CF)
bolt_pcd = 336.5         # mm
bolt_dia = 11.0          # mm (7/16" bolts)
num_bolts = 20

# Center bore for cold head (DN63CF)
center_bore_dia = 70.0   # mm (CF4.50 / DN63CF mounting bore)

# Zero-length reducer collar (to adapt DN320CF to DN63CF cold head)
reducer_od = 114.0       # mm (DN63CF flange OD)
reducer_id = 70.0        # mm
reducer_height = 15.0    # mm (above main plate)
reducer_bolt_pcd = 92.0  # mm (CF4.50 bolt pattern)
reducer_bolt_dia = 6.5   # mm (1/4" bolts)
num_reducer_bolts = 8

# Feedthrough ports (CF40 / DN40CF for more room)
feedthrough_port_dia = 50.0   # mm (CF40 bore)
feedthrough_pcd = 130.0       # mm (distance from center - more room now)
num_feedthrough_ports = 6     # D-sub × 2 + SMA × 4
feedthrough_angles = [30, 90, 150, 210, 270, 330]  # degrees, avoiding bolt pattern

# ============================================================================
# Create geometry
# ============================================================================

shapes = []

# Main plate disk
main_plate = Part.makeCylinder(plate_od/2, plate_thickness, Vector(0, 0, 0))

# Cut center bore
center_bore = Part.makeCylinder(center_bore_dia/2, plate_thickness, Vector(0, 0, 0))
main_plate = main_plate.cut(center_bore)

# Cut main flange bolt holes (DN200CF)
for i in range(num_bolts):
    angle = i * (2 * math.pi / num_bolts)
    x = (bolt_pcd/2) * math.cos(angle)
    y = (bolt_pcd/2) * math.sin(angle)
    bolt_hole = Part.makeCylinder(bolt_dia/2, plate_thickness, Vector(x, y, 0))
    main_plate = main_plate.cut(bolt_hole)

# Cut feedthrough ports
for angle_deg in feedthrough_angles:
    angle = math.radians(angle_deg)
    x = (feedthrough_pcd) * math.cos(angle)
    y = (feedthrough_pcd) * math.sin(angle)
    port_hole = Part.makeCylinder(feedthrough_port_dia/2, plate_thickness, Vector(x, y, 0))
    main_plate = main_plate.cut(port_hole)

shapes.append(main_plate)

# Reducer collar (raised boss for DN63CF cold head mounting)
reducer_outer = Part.makeCylinder(reducer_od/2, reducer_height,
                                  Vector(0, 0, plate_thickness))
reducer_inner = Part.makeCylinder(reducer_id/2, reducer_height,
                                  Vector(0, 0, plate_thickness))
reducer_collar = reducer_outer.cut(reducer_inner)

# Cut reducer bolt holes
for i in range(num_reducer_bolts):
    angle = i * (2 * math.pi / num_reducer_bolts) + math.radians(22.5)  # Offset
    x = (reducer_bolt_pcd/2) * math.cos(angle)
    y = (reducer_bolt_pcd/2) * math.sin(angle)
    bolt_hole = Part.makeCylinder(reducer_bolt_dia/2, reducer_height + plate_thickness/2,
                                  Vector(x, y, plate_thickness/2))
    reducer_collar = reducer_collar.cut(bolt_hole)
    # Also cut through main plate for bolt access
    through_hole = Part.makeCylinder(reducer_bolt_dia/2, plate_thickness/2,
                                     Vector(x, y, plate_thickness/2))
    main_plate = main_plate.cut(through_hole)

shapes.append(reducer_collar)

# ============================================================================
# Combine and create solid
# ============================================================================

# Fuse all shapes
top_plate = shapes[0]
for shape in shapes[1:]:
    top_plate = top_plate.fuse(shape)

# ============================================================================
# Create Part object
# ============================================================================

top_plate_obj = doc.addObject("Part::Feature", "TopPlate")
top_plate_obj.Shape = top_plate
if hasattr(top_plate_obj, 'ViewObject') and top_plate_obj.ViewObject:
    top_plate_obj.ViewObject.ShapeColor = (0.6, 0.6, 0.65)  # Stainless steel

# Recompute
doc.recompute()

# Save document
doc.saveAs("top-plate.FCStd")

print("Created top plate model")
print(f"  Plate OD: Ø{plate_od} mm (DN320CF)")
print(f"  Plate thickness: {plate_thickness} mm")
print(f"  Center bore: Ø{center_bore_dia} mm (for DN63CF cold head)")
print(f"  Reducer collar: Ø{reducer_od} mm × {reducer_height} mm")
print(f"  Feedthrough ports: {num_feedthrough_ports}× CF40 at R={feedthrough_pcd} mm")
print(f"  Main bolts: {num_bolts}× Ø{bolt_dia} mm on Ø{bolt_pcd} mm PCD")
