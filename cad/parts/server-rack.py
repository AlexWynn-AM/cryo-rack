#!/usr/bin/env python3
"""
FreeCAD script to generate parametric 19" server rack model.

Run in FreeCAD:
    exec(open('server-rack.py').read())

Based on Vertiv VR3100 dimensions (42U, 600mm x 1100mm).
Open frame style for visibility of internal components.
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("Server-Rack")

# ============================================================================
# Parametric Dimensions
# ============================================================================

# Rack size (Vertiv VR3100 style)
rack_units = 42              # U (1U = 44.45mm = 1.75")
rack_width = 600.0           # mm (external width)
rack_depth = 1100.0          # mm (external depth)

# 19" EIA standard
u_height = 44.45             # mm (1.75")
rail_width = 15.875          # mm (5/8" - standard rail width)
panel_width = 482.6          # mm (19")
rail_spacing = 465.1         # mm (between rail hole centers)
hole_spacing = 15.875        # mm (5/8" between holes in a U)

# Frame construction
post_size = 50.0             # mm (square posts)
post_wall = 3.0              # mm (wall thickness if hollow)
frame_height = 50.0          # mm (top/bottom horizontal frame)
base_height = 100.0          # mm (height of base from floor)
top_clearance = 50.0         # mm (clearance above top U)

# Calculated dimensions
usable_height = rack_units * u_height  # 42U = 1866.9mm
total_height = base_height + usable_height + top_clearance + frame_height

# Post positions (corners)
post_x = (rack_width - post_size) / 2
post_y = (rack_depth - post_size) / 2

# Rail positions (19" spacing)
rail_x = rail_spacing / 2

# ============================================================================
# Create geometry
# ============================================================================

shapes = []

# ----------------------------------------------------------------------------
# Four corner posts (vertical)
# ----------------------------------------------------------------------------

post_positions = [
    (-post_x, -post_y),  # front-left
    (+post_x, -post_y),  # front-right
    (-post_x, +post_y),  # rear-left
    (+post_x, +post_y),  # rear-right
]

for px, py in post_positions:
    # Outer post
    post_outer = Part.makeBox(post_size, post_size, total_height,
                              Vector(px - post_size/2, py - post_size/2, 0))
    # Hollow it out
    post_inner = Part.makeBox(post_size - 2*post_wall, post_size - 2*post_wall,
                              total_height,
                              Vector(px - post_size/2 + post_wall,
                                     py - post_size/2 + post_wall, 0))
    post = post_outer.cut(post_inner)
    shapes.append(post)

# ----------------------------------------------------------------------------
# Top frame (horizontal bars connecting posts)
# ----------------------------------------------------------------------------

z_top = total_height - frame_height

# Front and rear bars
for py in [-post_y, +post_y]:
    bar = Part.makeBox(rack_width - post_size, post_size, frame_height,
                       Vector(-post_x + post_size/2, py - post_size/2, z_top))
    shapes.append(bar)

# Side bars
for px in [-post_x, +post_x]:
    bar = Part.makeBox(post_size, rack_depth - post_size, frame_height,
                       Vector(px - post_size/2, -post_y + post_size/2, z_top))
    shapes.append(bar)

# ----------------------------------------------------------------------------
# Bottom frame (at base height)
# ----------------------------------------------------------------------------

z_bottom = 0

# Front and rear bars
for py in [-post_y, +post_y]:
    bar = Part.makeBox(rack_width - post_size, post_size, frame_height,
                       Vector(-post_x + post_size/2, py - post_size/2, z_bottom))
    shapes.append(bar)

# Side bars
for px in [-post_x, +post_x]:
    bar = Part.makeBox(post_size, rack_depth - post_size, frame_height,
                       Vector(px - post_size/2, -post_y + post_size/2, z_bottom))
    shapes.append(bar)

# ----------------------------------------------------------------------------
# 19" mounting rails (front pair)
# ----------------------------------------------------------------------------

rail_height = usable_height + 20  # Slightly taller than usable space
z_rail_bottom = base_height + frame_height - 10

# Front rails (where equipment mounts)
for rx in [-rail_x, +rail_x]:
    # Rail is at front of rack
    ry = -post_y + post_size/2 + 20  # 20mm from front posts

    rail = Part.makeBox(rail_width, rail_width, rail_height,
                        Vector(rx - rail_width/2, ry - rail_width/2, z_rail_bottom))

    # Add mounting holes (simplified - just visual indicators)
    for u in range(rack_units):
        z_hole = z_rail_bottom + 10 + u * u_height + u_height/2
        # Three holes per U (top, middle, bottom)
        for offset in [-hole_spacing/2, 0, hole_spacing/2]:
            hole = Part.makeCylinder(2.5, rail_width + 10,  # M5 clearance
                                     Vector(rx, ry - rail_width, z_hole + offset),
                                     Vector(0, 1, 0))
            rail = rail.cut(hole)

    shapes.append(rail)

# Rear rails
for rx in [-rail_x, +rail_x]:
    ry = +post_y - post_size/2 - 20  # 20mm from rear posts

    rail = Part.makeBox(rail_width, rail_width, rail_height,
                        Vector(rx - rail_width/2, ry - rail_width/2, z_rail_bottom))

    # Mounting holes
    for u in range(rack_units):
        z_hole = z_rail_bottom + 10 + u * u_height + u_height/2
        for offset in [-hole_spacing/2, 0, hole_spacing/2]:
            hole = Part.makeCylinder(2.5, rail_width + 10,
                                     Vector(rx, ry + rail_width, z_hole + offset),
                                     Vector(0, -1, 0))
            rail = rail.cut(hole)

    shapes.append(rail)

# ----------------------------------------------------------------------------
# Casters/feet (simplified as cylinders)
# ----------------------------------------------------------------------------

caster_dia = 75.0
caster_height = base_height - 10

for px, py in post_positions:
    caster = Part.makeCylinder(caster_dia/2, caster_height,
                               Vector(px, py, 0))
    shapes.append(caster)

# ============================================================================
# Combine all shapes
# ============================================================================

rack = shapes[0]
for shape in shapes[1:]:
    rack = rack.fuse(shape)

# Refine shape
rack = rack.removeSplitter()

# ============================================================================
# Create Part object
# ============================================================================

rack_obj = doc.addObject("Part::Feature", "ServerRack")
rack_obj.Shape = rack
if hasattr(rack_obj, 'ViewObject') and rack_obj.ViewObject:
    rack_obj.ViewObject.ShapeColor = (0.2, 0.2, 0.25)  # Dark gray
    rack_obj.ViewObject.Transparency = 0

# ============================================================================
# Add reference planes for equipment mounting
# ============================================================================

# Create a datum plane at U1 (bottom of usable space) for reference
z_u1 = base_height + frame_height

# ============================================================================
# Print dimensions
# ============================================================================

print("\n" + "="*60)
print("SERVER RACK - PARAMETRIC MODEL")
print("="*60)

print(f"\nOverall Dimensions:")
print(f"  Width:  {rack_width} mm ({rack_width/25.4:.1f}\")")
print(f"  Depth:  {rack_depth} mm ({rack_depth/25.4:.1f}\")")
print(f"  Height: {total_height:.1f} mm ({total_height/25.4:.1f}\")")

print(f"\nRack Units:")
print(f"  Total: {rack_units}U")
print(f"  Usable height: {usable_height:.1f} mm")
print(f"  U1 position (z): {z_u1:.1f} mm from floor")
print(f"  U{rack_units} top (z): {z_u1 + usable_height:.1f} mm from floor")

print(f"\n19\" Rail Mounting:")
print(f"  Rail spacing: {rail_spacing} mm (center-to-center)")
print(f"  Panel width: {panel_width} mm (19\")")
print(f"  Max equipment width: ~{rail_spacing - 10:.0f} mm between rails")

print(f"\nEquipment Clearance:")
print(f"  Between front rails: {rail_spacing - rail_width:.1f} mm")
print(f"  Depth (rail to rail): {rack_depth - 2*post_size - 80:.1f} mm")

# Check if our cryostat fits
cryostat_flange_od = 368.0  # DN320CF
print(f"\nCryostat Fit Check:")
print(f"  Cryostat flange OD: {cryostat_flange_od} mm")
print(f"  Available width: {rail_spacing - rail_width:.1f} mm")
if cryostat_flange_od < rail_spacing - rail_width:
    print(f"  ✓ Cryostat fits between rails")
else:
    print(f"  ✗ WARNING: Cryostat may not fit between rails")

print("\n" + "="*60)

# Recompute
doc.recompute()

# Save document
doc.saveAs("server-rack.FCStd")

print("\nRack model saved to server-rack.FCStd")
