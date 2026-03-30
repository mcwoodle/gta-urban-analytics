"""
Generate kepler.gl HTML maps with crime, census, and crime-rate layers.

Usage:
    uv run kepler              # All years
    uv run kepler --year 2024  # Single year
"""

import argparse
import os
import sys

import geopandas as gpd
import pandas as pd
from keplergl import KeplerGl


MAPBOX_TOKEN = "pk.eyJ1IjoibWN3b29kbGUiLCJhIjoiY21uOWpoNmZzMDh6azJwcHg2NmNsanZ1bSJ9.gmd6iVjMzmzP8nc2wAa7cA"

# GTA center coordinates
GTA_CENTER = {"lat": 43.7, "lng": -79.4}

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def _load_crime_data(year=None):
    """Load unified crime data, optionally filtered to a year."""
    csv_path = os.path.join(_project_root, 'data', '02_transformed', 'unified_data.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run the transform pipeline first.")
        sys.exit(1)

    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)

    if year:
        df['_year'] = pd.to_datetime(df['occurrence_date'], errors='coerce').dt.year
        df = df[df['_year'] == year].drop(columns=['_year'])
        print(f"  Filtered to year {year}: {len(df):,} rows")

    before = len(df)
    df = df.dropna(subset=['lat', 'lon'])
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with missing coordinates ({len(df):,} remaining)")

    return df


def _load_census_data():
    """Load GTA census DA GeoJSON. Returns (GeoDataFrame, points DataFrame)."""
    geojson_path = os.path.join(_project_root, 'data', '02_transformed', 'gta_census_da.geojson')
    if not os.path.exists(geojson_path):
        print(f"Error: {geojson_path} not found. Run the census notebook first.")
        sys.exit(1)

    print(f"Loading {geojson_path}...")
    gdf = gpd.read_file(geojson_path)

    # Point dataframe for the census kepler layer
    points_df = pd.DataFrame({
        'DAUID': gdf['DAUID'],
        'Population': gdf['Population'],
        'Median_Income': gdf['Median_Income'],
        'lat': gdf['centroid_lat'],
        'lon': gdf['centroid_lon'],
    })
    print(f"  Loaded {len(gdf):,} Dissemination Areas")
    return gdf, points_df


def _compute_crime_rate(crime_df, census_gdf, census_points_df):
    """Spatial join crimes to DAs and compute crime per 1,000 residents."""
    print("Computing crime rates per Dissemination Area...")
    crime_gdf = gpd.GeoDataFrame(
        crime_df,
        geometry=gpd.points_from_xy(crime_df['lon'], crime_df['lat']),
        crs='EPSG:4326',
    )

    joined = gpd.sjoin(crime_gdf, census_gdf[['DAUID', 'geometry']], how='inner', predicate='within')
    crime_counts = joined.groupby('DAUID').size().reset_index(name='crime_count')

    rate_df = crime_counts.merge(
        census_points_df[['DAUID', 'Population', 'lat', 'lon']],
        on='DAUID',
    )
    rate_df['crime_per_1000'] = (rate_df['crime_count'] / rate_df['Population']) * 1000
    rate_df = rate_df[rate_df['Population'] > 0].dropna(subset=['crime_per_1000'])

    print(f"  Computed rates for {len(rate_df):,} DAs")
    return rate_df


def _build_config(crime_data_id):
    """Build kepler config with hexbin, census, and crime-rate layers."""
    return {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
                    # Layer 1: Crime hexbin (visible by default)
                    {
                        "id": "hexbin-layer",
                        "type": "hexbin",
                        "config": {
                            "dataId": crime_data_id,
                            "label": "Crime Hexbin",
                            "color": [255, 153, 31],
                            "columns": {"lat": "lat", "lng": "lon"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "worldUnitSize": 1,
                                "resolution": 8,
                                "colorRange": {
                                    "name": "Global Warming",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#5A1846", "#900C3F", "#C70039",
                                        "#E3611C", "#F1920E", "#FFC300",
                                    ],
                                },
                                "coverage": 1,
                                "sizeRange": [0, 500],
                                "percentile": [0, 100],
                                "elevationPercentile": [0, 100],
                                "elevationScale": 100,
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
                    },
                    # Layer 2: Census demographics (hidden by default)
                    {
                        "id": "census-layer",
                        "type": "point",
                        "config": {
                            "dataId": "census",
                            "label": "Census Demographics",
                            "color": [30, 150, 190],
                            "columns": {"lat": "lat", "lng": "lon"},
                            "isVisible": False,
                            "visConfig": {
                                "radius": 5,
                                "opacity": 0.7,
                                "filled": True,
                                "colorRange": {
                                    "name": "Uber Viz Sequential",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#E6FAFA", "#AAD7DA", "#68B4BB",
                                        "#00939C", "#006D75", "#004B4E",
                                    ],
                                },
                            },
                            "hidden": False,
                            "textLabel": [],
                        },
                        "visualChannels": {
                            "colorField": {"name": "Population", "type": "real"},
                            "colorScale": "quantile",
                            "sizeField": None,
                            "sizeScale": "linear",
                        },
                    },
                    # Layer 3: Crime rate per 1,000 residents (hidden by default)
                    {
                        "id": "crime-rate-layer",
                        "type": "point",
                        "config": {
                            "dataId": "crime_rate",
                            "label": "Crime per 1,000 Residents",
                            "color": [255, 80, 80],
                            "columns": {"lat": "lat", "lng": "lon"},
                            "isVisible": False,
                            "visConfig": {
                                "radius": 8,
                                "opacity": 0.8,
                                "filled": True,
                                "colorRange": {
                                    "name": "Sunrise",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#355C7D", "#6C5B7B", "#C06C84",
                                        "#F67280", "#F8B195", "#F5E0B7",
                                    ],
                                },
                            },
                            "hidden": False,
                            "textLabel": [],
                        },
                        "visualChannels": {
                            "colorField": {"name": "crime_per_1000", "type": "real"},
                            "colorScale": "quantile",
                            "sizeField": {"name": "crime_per_1000", "type": "real"},
                            "sizeScale": "sqrt",
                        },
                    },
                ],
                "interactionConfig": {
                    "tooltip": {
                        "fieldsToShow": {
                            crime_data_id: [
                                {"name": "region", "format": None},
                                {"name": "mapped_crime_category", "format": None},
                                {"name": "original_crime_type", "format": None},
                                {"name": "occurrence_date", "format": None},
                            ],
                            "census": [
                                {"name": "DAUID", "format": None},
                                {"name": "Population", "format": None},
                                {"name": "Median_Income", "format": None},
                            ],
                            "crime_rate": [
                                {"name": "DAUID", "format": None},
                                {"name": "crime_count", "format": None},
                                {"name": "Population", "format": None},
                                {"name": "crime_per_1000", "format": None},
                            ],
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


def generate_map(year=None):
    """Generate a kepler.gl HTML map with crime, census, and crime-rate layers."""
    # Load all data
    crime_df = _load_crime_data(year)
    census_gdf, census_points_df = _load_census_data()
    crime_rate_df = _compute_crime_rate(crime_df, census_gdf, census_points_df)

    label = str(year) if year else "all"
    crime_data_id = f"crime_{label}"
    config = _build_config(crime_data_id)

    print("Building kepler.gl map...")
    kepler_map = KeplerGl(
        height=800,
        data={
            crime_data_id: crime_df,
            "census": census_points_df,
            "crime_rate": crime_rate_df,
        },
        config=config,
        show_docs=False,
    )

    # Save HTML
    output_dir = os.path.join(_project_root, 'data', '03_visualizations')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'crime_map_{label}.html')

    kepler_map.save_to_html(file_name=output_path, read_only=False)

    # Inject Mapbox token into the HTML
    with open(output_path, 'r') as f:
        html = f.read()
    html = html.replace('PROVIDE_MAPBOX_TOKEN', MAPBOX_TOKEN)

    # Inject a window resize event to make the map fill the browser window
    parts = html.rsplit('</body>', 1)
    if len(parts) == 2:
        html = parts[0] + """
    <script>
      window.addEventListener('load', () => {
        window.dispatchEvent(new Event('resize'));
      });
    </script>
</body>""" + parts[1]

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Map saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate kepler.gl crime data visualization"
    )
    parser.add_argument(
        "--year", type=int, default=None,
        help="Year to filter (omit for all years)"
    )
    args = parser.parse_args()
    generate_map(args.year)


if __name__ == "__main__":
    main()
