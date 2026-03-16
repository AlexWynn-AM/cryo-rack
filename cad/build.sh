#!/bin/bash
#
# Build all FreeCAD models from Python scripts.
#
# Usage:
#   ./build.sh          # Build all parts and assembly
#   ./build.sh clean    # Remove generated .FCStd files
#   ./build.sh export   # Export assembly to STEP format
#
# Requires: FreeCAD (freecad or freecadcmd in PATH)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Find FreeCAD command
if command -v freecadcmd &> /dev/null; then
    FREECAD="freecadcmd"
elif command -v FreeCADCmd &> /dev/null; then
    FREECAD="FreeCADCmd"
elif command -v freecad &> /dev/null; then
    FREECAD="freecad -c"
elif [ -x "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd" ]; then
    FREECAD="/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
elif [ -x "/Applications/FreeCAD.app/Contents/Resources/bin/freecad" ]; then
    FREECAD="/Applications/FreeCAD.app/Contents/Resources/bin/freecad -c"
else
    echo "Error: FreeCAD not found in PATH"
    echo "Install FreeCAD or add it to your PATH"
    exit 1
fi

case "${1:-build}" in
    gui)
        echo "Building in GUI mode (saves view state)..."
        # Use FreeCAD GUI with the assembly script
        SCRIPT_PATH="$(pwd)/assembly/cryostat-assembly.py"
        /Applications/FreeCAD.app/Contents/Resources/bin/freecad "$SCRIPT_PATH" 2>/dev/null &
        echo "FreeCAD opened. After it loads:"
        echo "  1. View → Standard views → Isometric"
        echo "  2. View → Fit All (or press V, F)"
        echo "  3. File → Save"
        echo "This will save the view state for future opens."
        exit 0
        ;;

    build)
        echo "Building FreeCAD models..."
        echo ""

        # Build parts
        echo "=== Building Parts ==="
        for script in parts/*.py; do
            echo "  Building $(basename "$script" .py)..."
            (cd parts && $FREECAD "$(basename "$script")")
        done

        # Build assembly
        echo ""
        echo "=== Building Assembly ==="
        (cd assembly && $FREECAD cryostat-assembly.py)

        # Inject GuiDocument.xml for view settings
        echo ""
        echo "=== Injecting view settings ==="
        if [ -f assembly/GuiDocument.xml ] && [ -f assembly/cryostat-assembly.FCStd ]; then
            (cd assembly && zip -u cryostat-assembly.FCStd GuiDocument.xml)
            echo "View settings added (isometric, zoomed to fit)"
        fi

        echo ""
        echo "Build complete!"
        echo "Open assembly/cryostat-assembly.FCStd in FreeCAD to view"
        ;;

    clean)
        echo "Cleaning generated files..."
        rm -f parts/*.FCStd
        rm -f assembly/*.FCStd
        rm -f exports/*.step exports/*.stp
        echo "Done"
        ;;

    export)
        echo "Exporting to STEP format..."
        mkdir -p exports

        if [ ! -f assembly/cryostat-assembly.FCStd ]; then
            echo "Error: assembly/cryostat-assembly.FCStd not found"
            echo "Run './build.sh' first to generate the assembly"
            exit 1
        fi

        # Create export script with absolute paths embedded
        ASSEMBLY_PATH="$(cd assembly && pwd)/cryostat-assembly.FCStd"
        EXPORT_PATH="$(pwd)/exports/cryostat-assembly.step"

        cat > /tmp/export_step.py << EXPORT_SCRIPT
import FreeCAD
import Part

input_file = "${ASSEMBLY_PATH}"
output_file = "${EXPORT_PATH}"

print(f"Opening: {input_file}")
doc = FreeCAD.openDocument(input_file)

# Get all Part::Feature objects
shapes = []
for obj in doc.Objects:
    if hasattr(obj, 'Shape') and obj.Shape:
        shapes.append(obj.Shape)

if shapes:
    print(f"Found {len(shapes)} shapes")
    compound = Part.makeCompound(shapes)
    compound.exportStep(output_file)
    print(f"Exported to: {output_file}")
else:
    print("No shapes found to export")

FreeCAD.closeDocument(doc.Name)
EXPORT_SCRIPT

        $FREECAD /tmp/export_step.py

        if [ -f "$EXPORT_PATH" ]; then
            echo "Success: exports/cryostat-assembly.step"
            ls -la exports/cryostat-assembly.step
        else
            echo "Export may have failed - check above for errors"
        fi
        ;;

    *)
        echo "Usage: $0 [build|gui|clean|export]"
        echo ""
        echo "Commands:"
        echo "  build   - Build all parts and assembly (default, console mode)"
        echo "  gui     - Build assembly in GUI mode (saves view state)"
        echo "  clean   - Remove generated .FCStd files"
        echo "  export  - Export assembly to STEP format"
        exit 1
        ;;
esac
