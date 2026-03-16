#!/usr/bin/env python3
"""
FreeCAD macro to set up the view after opening the assembly.

Run in FreeCAD after opening cryostat-assembly.FCStd:
    1. Open the Python console (View → Panels → Python console)
    2. Paste: exec(open('/path/to/cad/setup-view.py').read())

Or add to FreeCAD macro folder and run from Macro menu.
"""

import FreeCADGui

# Make all objects visible
for obj in FreeCAD.ActiveDocument.Objects:
    if hasattr(obj, 'ViewObject') and obj.ViewObject:
        obj.ViewObject.Visibility = True

# Set isometric view and zoom to fit
view = FreeCADGui.ActiveDocument.ActiveView
view.viewIsometric()
view.fitAll()

# Optional: set a specific camera angle (front-right-top view)
# view.viewFront()
# view.viewRotateRight()

FreeCADGui.updateGui()
print("View configured: isometric, zoomed to fit")
