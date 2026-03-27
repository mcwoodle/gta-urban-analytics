"""
Generate kepler.gl HTML maps from yearly crime data.

Usage:
    uv run kepler --year 2024
"""

import argparse
import os
import sys

import pandas as pd
from keplergl import KeplerGl


MAPBOX_TOKEN = "pk.eyJ1IjoibWN3b29kbGUiLCJhIjoiY21uOWpoNmZzMDh6azJwcHg2NmNsanZ1bSJ9.gmd6iVjMzmzP8nc2wAa7cA"

# GTA center coordinates
GTA_CENTER = {"lat": 43.7, "lng": -79.4}

# Kepler config for hexbin layer
def _build_config(data_id: str) -> dict:
    return {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
                    {
                        "id": "hexbin-layer",
                        "type": "hexbin",
                        "config": {
                            "dataId": data_id,
                            "label": "Crime Hexbin",
                            "color": [255, 153, 31],
                            "columns": {
                                "lat": "lat",
                                "lng": "lon",
                            },
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "worldUnitSize": 1,  # 1 km radius
                                "resolution": 8,
                                "colorRange": {
                                    "name": "Global Warming",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#5A1846",
                                        "#900C3F",
                                        "#C70039",
                                        "#E3611C",
                                        "#F1920E",
                                        "#FFC300",
                                    ],
                                },
                                "coverage": 1,
                                "sizeRange": [0, 500],
                                "percentile": [0, 100],
                                "elevationPercentile": [0, 100],
                                "elevationScale": 100,  # height multiplier
                                "enableElevationZoomFactor": True,
                                "colorAggregation": "count",
                                "sizeAggregation": "count",
                                "enable3d": True,
                            },
                            "hidden": False,
                            "textLabel": [],
                        },
                        "visualChannels": {
                            "colorField": None,
                            "colorScale": "quantile",
                            "sizeField": None,
                            "sizeScale": "linear",
                        },
                    }
                ],
                "interactionConfig": {
                    "tooltip": {
                        "fieldsToShow": {
                            data_id: [
                                {"name": "region", "format": None},
                                {"name": "mapped_crime_category", "format": None},
                                {"name": "original_crime_type", "format": None},
                                {"name": "occurrence_date", "format": None},
                            ]
                        },
                        "compareMode": False,
                        "compareType": "absolute",
                        "enabled": True,
                    },
                    "brush": {"size": 0.5, "enabled": False},
                    "geocoder": {"enabled": False},
                    "coordinate": {"enabled": False},
                },
                "layerBlending": "normal",
                "splitMaps": [],
                "animationConfig": {"currentTime": None, "speed": 1},
            },
            "mapState": {
                "bearing": 24,
                "dragRotate": True,
                "latitude": GTA_CENTER["lat"],
                "longitude": GTA_CENTER["lng"],
                "pitch": 45,
                "zoom": 9,
                "isSplit": False,
            },
            "mapStyle": {
                "styleType": "dark",
                "topLayerGroups": {},
                "visibleLayerGroups": {
                    "label": True,
                    "road": True,
                    "border": False,
                    "building": True,
                    "water": True,
                    "land": True,
                    "3d building": False,
                },
                "threeDBuildingColor": [9.665468314072013, 17.18305478057247, 31.1442867897876],
                "mapStyles": {},
            },
        },
    }


def generate_map(year: int) -> str:
    """Generate a kepler.gl HTML map for the given year. Returns the output path."""
    # Resolve data path
    project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    data_dir = os.path.join(project_root, 'data', '02_transformed')
    csv_path = os.path.join(data_dir, f'unified_crime_data_{year}.csv')

    if not os.path.exists(csv_path):
        print(f"Error: Data file not found: {csv_path}")
        print(f"Run the transform pipeline first to generate yearly partitions.")
        sys.exit(1)

    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)

    # Drop rows without coordinates
    before = len(df)
    df = df.dropna(subset=['lat', 'lon'])
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with missing coordinates ({len(df):,} remaining)")

    data_id = f"crime_{year}"
    config = _build_config(data_id)

    # Create map
    kepler_map = KeplerGl(
        height=800,
        data={data_id: df},
        config=config,
        show_docs=False,
    )

    # Save HTML
    output_dir = os.path.join(project_root, 'data', '03_visualizations')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'crime_map_{year}.html')

    kepler_map.save_to_html(
        file_name=output_path,
        read_only=False,
    )

    # Inject Mapbox token into the HTML
    with open(output_path, 'r') as f:
        html = f.read()
    html = html.replace(
        'PROVIDE_MAPBOX_TOKEN',
        MAPBOX_TOKEN,
    )
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Map saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate kepler.gl crime data visualization"
    )
    parser.add_argument(
        "--year", type=int, required=True,
        help="Year to visualize (e.g. 2024)"
    )
    args = parser.parse_args()
    generate_map(args.year)


if __name__ == "__main__":
    main()
