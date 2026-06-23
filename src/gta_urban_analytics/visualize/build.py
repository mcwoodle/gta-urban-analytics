import os
import subprocess
import sys
from pathlib import Path

def build_map():
    """Build the Kepler map visualization project."""
    # Find the visualize-kepler-map directory
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    kepler_dir = project_root / "visualize-kepler-map"
    
    if not kepler_dir.exists():
        print(f"Error: Could not find visualize-kepler-map directory at {kepler_dir}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Building Kepler map project in {kepler_dir}...")
    
    # Check if yarn is available
    try:
        subprocess.run(["yarn", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: yarn is not installed or not in PATH.", file=sys.stderr)
        print("Please install yarn (e.g. 'npm install -g yarn') to build the map.", file=sys.stderr)
        sys.exit(1)
        
    # Run yarn install
    print("Running 'yarn install'...")
    try:
        subprocess.run(["yarn", "install"], cwd=str(kepler_dir), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during yarn install: {e}", file=sys.stderr)
        sys.exit(e.returncode)
        
    # Run yarn build:all
    print("Running 'yarn build:all'...")
    try:
        subprocess.run(["yarn", "build:all"], cwd=str(kepler_dir), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during yarn build:all: {e}", file=sys.stderr)
        sys.exit(e.returncode)
        
    print("Map visualization built successfully!")

if __name__ == "__main__":
    build_map()
