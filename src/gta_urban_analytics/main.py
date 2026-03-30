"""
GTA Crime Data Pipeline
=======================
Entry point for the GTA crime data acquisition, transformation, and analysis pipeline.

Usage:
  uv run -m gta_urban_analytics.main download    # Download all regional datasets
  uv run -m gta_urban_analytics.main unify       # Unify downloaded data into a single CSV
  uv run -m gta_urban_analytics.main transform   # Run full transform pipeline (unify → filter → deduplicate)
  uv run -m gta_urban_analytics.main analyze -i <csv_file>  # Run analysis on a dataset
"""

import sys

def full_pipeline():
    download()
    transform()
    # analyze()

def download():
    """Download all regional crime datasets into data/01_raw/."""
    from gta_urban_analytics.extract.all import download
    download()


def unify():
    """Unify all downloaded regional CSVs in memory (does not save to CSV)."""
    from gta_urban_analytics.transform.crime.unify_datasets import unify_datasets
    unify_datasets()


def transform():
    """Run the full transform pipeline: unify → filter invalid → deduplicate."""
    from gta_urban_analytics.transform.pipeline import run
    run()


def analyze():
    """Run per-region statistical analysis on a CSV file."""
    from gta_urban_analytics.analyze.analyze import main as analyze_main
    analyze_main()


def main():
    """Main CLI dispatcher."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]
    # Remove the subcommand so downstream parsers see correct argv
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "download":
        download()
    elif command == "unify":
        unify()
    elif command == "transform":
        transform()
    elif command == "analyze":
        analyze()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
