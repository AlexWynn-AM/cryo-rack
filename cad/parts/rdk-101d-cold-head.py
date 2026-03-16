#!/usr/bin/env python3
"""
FreeCAD script to generate RDK-101D cold head model.

Run in FreeCAD:
    exec(open('rdk-101d-cold-head.py').read())

Or from command line:
    freecad -c rdk-101d-cold-head.py

Dimensions from SHI RDK-101D outline drawing.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("RDK-101D-Cold-Head")

# ============================================================================
# Dimensions (from SHI RDK-101D outline drawing)
# ============================================================================

# Motor housing (outside vacuum)
motor_dia = 130.0        # mm
motor_height = 200.0     # mm (approximate, above CF flange)

# CF flange (DN63CF / CF4.50)
cf_flange_od = 114.0     # mm
cf_flange_id = 70.0      # mm (bore)
cf_flange_thickness = 20.0  # mm

# 1st stage (45K)
first_stage_dia = 108.0   # mm
first_stage_height = 30.0 # mm

# Transition tube between flange and 1st stage
transition_tube_od = 70.0  # mm
transition_tube_id = 60.0  # mm
transition_height = 50.0   # mm (approx)

# 2nd stage cylinder (between 1st and 2nd stage)
second_stage_tube_od = 52.0  # mm
second_stage_tube_height = 100.0  # mm (approx)

# 2nd stage cold tip (4K)
second_stage_tip_dia = 45.0  # mm
second_stage_tip_height = 40.0  # mm

# Total cold head height: 442 mm
# Breakdown: motor(200) + flange(20) + transition(50) + 1st_stage(30) +
#            tube(100) + tip(40) = 440 mm (close to 442)

# ============================================================================
# Create geometry
# ============================================================================

shapes = []

# Origin at center of CF flange bottom face (vacuum side)

# Motor housing (cylinder above flange, outside vacuum)
motor = Part.makeCylinder(motor_dia/2, motor_height,
                          Vector(0, 0, cf_flange_thickness))
shapes.append(motor)

# CF flange
cf_flange = Part.makeCylinder(cf_flange_od/2, cf_flange_thickness,
                              Vector(0, 0, 0))
# Hollow out the bore
cf_bore = Part.makeCylinder(cf_flange_id/2, cf_flange_thickness,
                            Vector(0, 0, 0))
cf_flange = cf_flange.cut(cf_bore)
shapes.append(cf_flange)

# Transition tube (from flange down to 1st stage, inside vacuum)
trans_outer = Part.makeCylinder(transition_tube_od/2, transition_height,
                                Vector(0, 0, -transition_height))
trans_inner = Part.makeCylinder(transition_tube_id/2, transition_height,
                                Vector(0, 0, -transition_height))
transition = trans_outer.cut(trans_inner)
shapes.append(transition)

# 1st stage flange (45K)
first_stage_z = -transition_height - first_stage_height
first_stage = Part.makeCylinder(first_stage_dia/2, first_stage_height,
                                Vector(0, 0, first_stage_z))
shapes.append(first_stage)

# 2nd stage tube (between 1st stage and cold tip)
tube_z = first_stage_z - second_stage_tube_height
tube = Part.makeCylinder(second_stage_tube_od/2, second_stage_tube_height,
                         Vector(0, 0, tube_z))
shapes.append(tube)

# 2nd stage cold tip (4K) - slightly smaller diameter
tip_z = tube_z - second_stage_tip_height
tip = Part.makeCylinder(second_stage_tip_dia/2, second_stage_tip_height,
                        Vector(0, 0, tip_z))
shapes.append(tip)

# ============================================================================
# Combine and create solid
# ============================================================================

# Fuse all shapes
cold_head = shapes[0]
for shape in shapes[1:]:
    cold_head = cold_head.fuse(shape)

# ============================================================================
# Mounting holes for thermal straps
# ============================================================================

# 1st stage mounting holes (M4 tapped, 2x on opposite sides)
m4_hole_dia = 3.3  # mm - tap drill for M4
m4_hole_depth = 10.0  # mm
first_stage_hole_radius = first_stage_dia/2 - 8  # 8mm from edge

for angle_deg in [0, 180]:
    angle = math.radians(angle_deg)
    x = first_stage_hole_radius * math.cos(angle)
    y = first_stage_hole_radius * math.sin(angle)
    # Holes go into top of 1st stage
    hole = Part.makeCylinder(m4_hole_dia/2, m4_hole_depth,
                             Vector(x, y, first_stage_z + first_stage_height),
                             Vector(0, 0, -1))
    cold_head = cold_head.cut(hole)

# 2nd stage mounting holes (M4 tapped, 2x on opposite sides)
second_stage_hole_radius = second_stage_tip_dia/2 - 6  # 6mm from edge

for angle_deg in [90, 270]:  # Different orientation from 1st stage
    angle = math.radians(angle_deg)
    x = second_stage_hole_radius * math.cos(angle)
    y = second_stage_hole_radius * math.sin(angle)
    # Holes go into bottom of 2nd stage tip
    hole = Part.makeCylinder(m4_hole_dia/2, m4_hole_depth,
                             Vector(x, y, tip_z + m4_hole_depth),
                             Vector(0, 0, -1))
    cold_head = cold_head.cut(hole)

# Create Part object
cold_head_obj = doc.addObject("Part::Feature", "RDK-101D")
cold_head_obj.Shape = cold_head
if hasattr(cold_head_obj, 'ViewObject') and cold_head_obj.ViewObject:
    cold_head_obj.ViewObject.ShapeColor = (0.7, 0.7, 0.75)  # Steel gray

# ============================================================================
# Add reference planes and labels
# ============================================================================

# Recompute
doc.recompute()

# Save document
doc.saveAs("rdk-101d-cold-head.FCStd")

print("Created RDK-101D cold head model")
print(f"  Total height: {motor_height + cf_flange_thickness + transition_height + first_stage_height + second_stage_tube_height + second_stage_tip_height} mm")
print(f"  Motor housing: Ø{motor_dia} mm")
print(f"  1st stage: Ø{first_stage_dia} mm at z = {first_stage_z} mm")
print(f"  2nd stage tip: Ø{second_stage_tip_dia} mm at z = {tip_z} mm")
