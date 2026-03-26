"""
GTA Crime Data Pipeline
=======================
Entry point for the GTA crime data acquisition, transformation, and analysis pipeline.

Usage:
  uv run -m gta_crime_data.main download   # Download all regional datasets
  uv run -m gta_crime_data.main unify      # Unify downloaded data into a single CSV
  uv run -m gta_crime_data.main analyze -i <csv_file>  # Run analysis on a dataset
"""

import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]
    # Remove the subcommand so downstream parsers see correct argv
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "download":
        from gta_crime_data.extract.download_durham import download_durham_data
        from gta_crime_data.extract.download_halton import download_halton_crime_data
        from gta_crime_data.extract.download_peel import download_peel_crime_data
        from gta_crime_data.extract.download_toronto import download_toronto_data
        from gta_crime_data.extract.download_york import download_york_data

        download_toronto_data()
        download_york_data()
        download_peel_crime_data()
        download_halton_crime_data()
        download_durham_data()

    elif command == "unify":
        from gta_crime_data.transform.unify_datasets import run
        run()

    elif command == "analyze":
        from gta_crime_data.analyze.analyze import main as analyze_main
        analyze_main()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
