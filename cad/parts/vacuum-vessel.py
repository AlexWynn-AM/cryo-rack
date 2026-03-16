#!/usr/bin/env python3
"""
FreeCAD script to generate vacuum vessel model.

Run in FreeCAD:
    exec(open('vacuum-vessel.py').read())

DN200CF vacuum vessel - SS tube with CF flanges at both ends.
KF-25 side ports for pump, gauge, and relief valve.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Vacuum-Vessel")

# ============================================================================
# Dimensions
# ============================================================================

# Vessel body (12" Sch 10 pipe with DN320CF flanges)
vessel_od = 324.0        # mm - 12" pipe OD (323.85mm nominal)
vessel_id = 320.0        # mm - approximately
vessel_wall = 4.0        # mm - Sch 10
vessel_length = 550.0    # mm - extended for 250mm sample stage

# DN320CF flanges (12.75" / 324mm class)
flange_od = 368.0        # mm (14.5")
flange_thickness = 22.0  # mm
flange_bolt_pcd = 336.5  # mm
flange_bolt_dia = 11.0   # mm (7/16" bolts)
num_flange_bolts = 20

# KF-25 side ports (welded on vessel body)
kf25_od = 33.0           # mm - KF25 fitting OD
kf25_id = 25.0           # mm - KF25 bore
kf25_length = 40.0       # mm - stub length
num_kf_ports = 3         # pump, gauge, relief valve

# Port positions (angle from front, height from bottom)
port_angles = [0, 120, 240]  # degrees
port_height = vessel_length / 3  # lower third of vessel

# ============================================================================
# Create geometry
# ============================================================================

shapes = []

# Main tube (hollow cylinder)
outer_tube = Part.makeCylinder(vessel_od/2, vessel_length, Vector(0, 0, 0))
inner_tube = Part.makeCylinder(vessel_id/2, vessel_length, Vector(0, 0, 0))
vessel_tube = outer_tube.cut(inner_tube)
shapes.append(vessel_tube)

# Bottom flange (DN200CF)
bottom_flange = Part.makeCylinder(flange_od/2, flange_thickness,
                                  Vector(0, 0, -flange_thickness))
# Cut center bore
bottom_bore = Part.makeCylinder(vessel_id/2, flange_thickness,
                                Vector(0, 0, -flange_thickness))
bottom_flange = bottom_flange.cut(bottom_bore)

# Cut bolt holes
for i in range(num_flange_bolts):
    angle = i * (2 * math.pi / num_flange_bolts)
    x = (flange_bolt_pcd/2) * math.cos(angle)
    y = (flange_bolt_pcd/2) * math.sin(angle)
    bolt_hole = Part.makeCylinder(flange_bolt_dia/2, flange_thickness,
                                  Vector(x, y, -flange_thickness))
    bottom_flange = bottom_flange.cut(bolt_hole)
shapes.append(bottom_flange)

# Top flange (DN200CF) - but this will be separate top plate
top_flange = Part.makeCylinder(flange_od/2, flange_thickness,
                               Vector(0, 0, vessel_length))
top_bore = Part.makeCylinder(vessel_id/2, flange_thickness,
                             Vector(0, 0, vessel_length))
top_flange = top_flange.cut(top_bore)

# Cut bolt holes
for i in range(num_flange_bolts):
    angle = i * (2 * math.pi / num_flange_bolts)
    x = (flange_bolt_pcd/2) * math.cos(angle)
    y = (flange_bolt_pcd/2) * math.sin(angle)
    bolt_hole = Part.makeCylinder(flange_bolt_dia/2, flange_thickness,
                                  Vector(x, y, vessel_length))
    top_flange = top_flange.cut(bolt_hole)
shapes.append(top_flange)

# KF-25 side ports
for i, angle_deg in enumerate(port_angles):
    angle = math.radians(angle_deg)
    # Port stub extending outward from vessel wall
    port_x = (vessel_od/2) * math.cos(angle)
    port_y = (vessel_od/2) * math.sin(angle)

    # Create port stub
    port = Part.makeCylinder(kf25_od/2, kf25_length)
    port_bore = Part.makeCylinder(kf25_id/2, kf25_length + vessel_wall + 5)

    # Position: rotate to point outward, translate to vessel surface
    port.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90)  # Point along X
    port.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle_deg)  # Rotate around Z
    port.translate(Vector(port_x, port_y, port_height))

    # Position bore similarly (will cut through vessel wall)
    port_bore.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90)
    port_bore.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle_deg)
    port_bore.translate(Vector(0, 0, port_height))

    shapes.append(port)
    # We'll cut the bore from the combined shape later

# ============================================================================
# Combine and create solid
# ============================================================================

# Fuse all shapes
vessel = shapes[0]
for shape in shapes[1:]:
    vessel = vessel.fuse(shape)

# Cut port bores through vessel wall
for i, angle_deg in enumerate(port_angles):
    angle = math.radians(angle_deg)
    port_bore = Part.makeCylinder(kf25_id/2, vessel_od)
    port_bore.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 90)
    port_bore.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle_deg)
    port_bore.translate(Vector(0, 0, port_height))
    vessel = vessel.cut(port_bore)

# ============================================================================
# Create Part object
# ============================================================================

vacuum_vessel = doc.addObject("Part::Feature", "VacuumVessel")
vacuum_vessel.Shape = vessel
if hasattr(vacuum_vessel, 'ViewObject') and vacuum_vessel.ViewObject:
    vacuum_vessel.ViewObject.ShapeColor = (0.6, 0.6, 0.65)  # Stainless steel color
    vacuum_vessel.ViewObject.Transparency = 30  # Slightly transparent

# Recompute
doc.recompute()

# Save document
doc.saveAs("vacuum-vessel.FCStd")

print("Created vacuum vessel model")
print(f"  Vessel OD: Ø{vessel_od} mm")
print(f"  Vessel ID: Ø{vessel_id} mm")
print(f"  Length: {vessel_length} mm")
print(f"  Flange: DN200CF (Ø{flange_od} mm)")
print(f"  KF-25 ports: {num_kf_ports}× at z={port_height} mm")
