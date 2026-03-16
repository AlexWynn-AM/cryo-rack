#!/usr/bin/env python3
"""
FreeCAD script to generate CNA-11R rackmount compressor model.

Run in FreeCAD:
    exec(open('cna-11r-compressor.py').read())

Based on SHI Cryogenics CNA-11RB specifications:
- 400 x 484 x 540 mm (H x W x D)
- 65 kg
- 9U rackmount, air-cooled
- Compatible with RDK-101D cold head
"""

import FreeCAD as App
import Part
from FreeCAD import Vector
import math

# Create new document
doc = App.newDocument("CNA-11R-Compressor")

# ============================================================================
# Dimensions (CNA-11RB)
# ============================================================================

# Main enclosure
height = 400.0        # mm (~9U)
width = 484.0         # mm (19" rack width)
depth = 540.0         # mm

# Rack mounting
rack_ear_width = 15.0       # mm (ears extend beyond 19" panel)
rack_ear_height = height    # full height
rack_ear_thickness = 3.0    # mm
panel_width = 482.6         # mm (standard 19" panel)

# Front panel features
front_panel_thickness = 3.0  # mm
vent_area_width = 200.0      # mm
vent_area_height = 300.0     # mm
vent_slot_width = 60.0       # mm
vent_slot_height = 3.0       # mm
vent_slot_spacing = 8.0      # mm

# Rear panel features
rear_panel_thickness = 3.0   # mm
helium_port_dia = 20.0       # mm (supply/return fittings)
helium_port_spacing = 80.0   # mm
power_inlet_width = 50.0     # mm
power_inlet_height = 30.0    # mm

# Handle
handle_width = 120.0         # mm
handle_height = 25.0         # mm
handle_depth = 30.0          # mm
handle_bar_dia = 10.0        # mm

# Feet/standoffs
foot_dia = 30.0              # mm
foot_height = 10.0           # mm
foot_inset = 40.0            # mm from edges

# ============================================================================
# Create geometry
# ============================================================================

shapes = []

# ----------------------------------------------------------------------------
# Main enclosure body
# ----------------------------------------------------------------------------

# Main box (centered on X, front face at Y=0)
body = Part.makeBox(width, depth, height,
                    Vector(-width/2, 0, 0))

# Hollow it out (2mm wall thickness)
wall = 2.0
body_inner = Part.makeBox(width - 2*wall, depth - 2*wall, height - 2*wall,
                          Vector(-width/2 + wall, wall, wall))
body = body.cut(body_inner)
shapes.append(body)

# ----------------------------------------------------------------------------
# Rack mounting ears
# ----------------------------------------------------------------------------

for side in [-1, 1]:
    x_pos = side * (panel_width/2)
    ear = Part.makeBox(rack_ear_width, rack_ear_thickness, rack_ear_height,
                       Vector(x_pos - (rack_ear_width/2 if side < 0 else -rack_ear_width/2),
                              -rack_ear_thickness, 0))

    # Add mounting holes (3 per ear, standard rack spacing)
    hole_positions = [height * 0.15, height * 0.5, height * 0.85]
    for z in hole_positions:
        hole = Part.makeCylinder(3.5, rack_ear_thickness + 10,  # ~M6 clearance
                                 Vector(x_pos, -rack_ear_thickness - 5, z),
                                 Vector(0, 1, 0))
        ear = ear.cut(hole)

    shapes.append(ear)

# ----------------------------------------------------------------------------
# Front panel with vents
# ----------------------------------------------------------------------------

# Front panel overlay (cosmetic)
front_panel = Part.makeBox(panel_width - 20, front_panel_thickness, height - 20,
                           Vector(-(panel_width - 20)/2, -front_panel_thickness, 10))

# Cut ventilation slots
vent_start_x = -vent_area_width/2
vent_start_z = (height - vent_area_height)/2
num_slots = int(vent_area_height / vent_slot_spacing)

for i in range(num_slots):
    z = vent_start_z + i * vent_slot_spacing
    slot = Part.makeBox(vent_slot_width, front_panel_thickness + wall + 5, vent_slot_height,
                        Vector(-vent_slot_width/2, -front_panel_thickness - 2, z))
    front_panel = front_panel.cut(slot)
    body = body.cut(slot)

shapes.append(front_panel)

# ----------------------------------------------------------------------------
# Handles (top front)
# ----------------------------------------------------------------------------

for side in [-1, 1]:
    x_center = side * (panel_width/2 - 60)

    # Handle bracket
    bracket = Part.makeBox(handle_width/4, handle_depth, handle_height,
                           Vector(x_center - handle_width/8, -handle_depth, height - handle_height - 20))
    shapes.append(bracket)

    # Handle bar (simplified as box)
    bar = Part.makeBox(handle_width, handle_bar_dia, handle_bar_dia,
                       Vector(x_center - handle_width/2, -handle_depth + 5, height - 30))
    shapes.append(bar)

# ----------------------------------------------------------------------------
# Rear panel features
# ----------------------------------------------------------------------------

# Helium supply and return ports (rear, centered)
for i, x_offset in enumerate([-helium_port_spacing/2, helium_port_spacing/2]):
    # Port fitting (cylinder protruding from rear)
    port = Part.makeCylinder(helium_port_dia/2, 30,
                             Vector(x_offset, depth, height/2),
                             Vector(0, 1, 0))
    shapes.append(port)

    # Flange
    flange = Part.makeCylinder(helium_port_dia/2 + 5, 5,
                               Vector(x_offset, depth, height/2),
                               Vector(0, 1, 0))
    shapes.append(flange)

# Power inlet (rear, lower right)
power_inlet = Part.makeBox(power_inlet_width, 5, power_inlet_height,
                           Vector(width/2 - power_inlet_width - 30, depth, 50))
shapes.append(power_inlet)

# ----------------------------------------------------------------------------
# Feet/rubber standoffs
# ----------------------------------------------------------------------------

for x_sign in [-1, 1]:
    for y_pos in [foot_inset, depth - foot_inset]:
        x = x_sign * (width/2 - foot_inset)
        foot = Part.makeCylinder(foot_dia/2, foot_height,
                                 Vector(x, y_pos, -foot_height))
        shapes.append(foot)

# ----------------------------------------------------------------------------
# Status LEDs / display area (front panel)
# ----------------------------------------------------------------------------

# LED indicator panel (simplified as a box)
led_panel = Part.makeBox(80, 2, 30,
                         Vector(width/2 - 100, -front_panel_thickness - 2, height - 60))
shapes.append(led_panel)

# ============================================================================
# Combine all shapes
# ============================================================================

# Update body with vent cuts
shapes[0] = body

compressor = shapes[0]
for shape in shapes[1:]:
    compressor = compressor.fuse(shape)

# ============================================================================
# Create Part object
# ============================================================================

comp_obj = doc.addObject("Part::Feature", "CNA11R_Compressor")
comp_obj.Shape = compressor
if hasattr(comp_obj, 'ViewObject') and comp_obj.ViewObject:
    comp_obj.ViewObject.ShapeColor = (0.15, 0.15, 0.18)  # Dark gray/black

# ============================================================================
# Print specifications
# ============================================================================

print("\n" + "="*60)
print("CNA-11R RACKMOUNT COMPRESSOR MODEL")
print("="*60)

print(f"\nDimensions:")
print(f"  Height: {height} mm ({height/25.4:.1f}\")")
print(f"  Width:  {width} mm ({width/25.4:.1f}\" - 19\" rack)")
print(f"  Depth:  {depth} mm ({depth/25.4:.1f}\")")

rack_units = round(height / 44.45)
print(f"\nRack Units: ~{rack_units}U")

print(f"\nFeatures:")
print(f"  - Front ventilation slots")
print(f"  - Rack mounting ears with M6 holes")
print(f"  - Dual helium ports (rear)")
print(f"  - Power inlet (rear)")
print(f"  - Carrying handles")

print(f"\nCompatibility:")
print(f"  - RDK-101D cold head")
print(f"  - Standard 19\" rack")

print("\n" + "="*60)

# Recompute
doc.recompute()

# Save document
doc.saveAs("cna-11r-compressor.FCStd")

print("\nCompressor model saved to cna-11r-compressor.FCStd")
