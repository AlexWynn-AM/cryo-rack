#!/usr/bin/env python3
"""
Master build script to generate all FreeCAD models.

Run in FreeCAD:
    exec(open('build-all.py').read())

Or from command line (generates all .FCStd files):
    freecad -c build-all.py

This script:
1. Changes to the appropriate directory
2. Executes each part script in order
3. Then creates the assembly
"""

import os
import sys

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()

# List of part scripts to execute (in order)
part_scripts = [
    'parts/rdk-101d-cold-head.py',
    'parts/sample-stage.py',
    'parts/alumina-disk.py',
    'parts/radiation-shield.py',
    'parts/vacuum-vessel.py',
    'parts/top-plate.py',
    'parts/thermal-straps.py',
    'parts/wiring.py',
]

# Assembly script
assembly_script = 'assembly/cryostat-assembly.py'

print("="*60)
print("BUILDING CRYOSTAT CAD MODELS")
print("="*60)

# Build parts
print("\n--- Building Parts ---\n")
for script in part_scripts:
    script_path = os.path.join(script_dir, script)
    output_dir = os.path.dirname(script_path)

    print(f"Building: {script}")

    # Change to the script's directory so save paths work
    original_dir = os.getcwd()
    os.chdir(output_dir)

    try:
        exec(open(os.path.basename(script_path)).read())
        print(f"  ✓ Success\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
    finally:
        os.chdir(original_dir)

# Build assembly
print("\n--- Building Assembly ---\n")
script_path = os.path.join(script_dir, assembly_script)
output_dir = os.path.dirname(script_path)

print(f"Building: {assembly_script}")

original_dir = os.getcwd()
os.chdir(output_dir)

try:
    exec(open(os.path.basename(script_path)).read())
    print(f"  ✓ Success\n")
except Exception as e:
    print(f"  ✗ Error: {e}\n")
finally:
    os.chdir(original_dir)

print("="*60)
print("BUILD COMPLETE")
print("="*60)
print(f"\nOutput files in: {script_dir}")
print("\nTo view: Open cad/assembly/cryostat-assembly.FCStd in FreeCAD")
