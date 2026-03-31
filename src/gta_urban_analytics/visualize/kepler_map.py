"""
Generate kepler.gl HTML maps with crime, census, and crime-rate layers.

Produces standalone HTML files that bootstrap kepler.gl via client-side React,
loading kepler.gl and its dependencies from CDN. This avoids the Python
keplergl library's save_to_html bundle and its Mapbox token issues.

Usage:
    uv run kepler              # All years
    uv run kepler --year 2024  # Single year
"""

import argparse
import json
import os
import sys

import geopandas as gpd
import pandas as pd


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


def _df_to_csv_string(df):
    """Convert a DataFrame to a CSV string for embedding in HTML."""
    return df.to_csv(index=False)


def _build_config(crime_data_id):
    """Build kepler config with hexbin, census, and crime-rate layers."""
    return {
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
    }


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{ margin: 0; padding: 0; overflow: hidden; }}
    #app {{ position: absolute; width: 100%; height: 100%; }}
  </style>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/redux@4/dist/redux.min.js"></script>
  <script src="https://unpkg.com/react-redux@8/dist/react-redux.min.js"></script>
  <script src="https://unpkg.com/styled-components@6.1.8/dist/styled-components.min.js"></script>
  <script src="https://unpkg.com/kepler.gl/umd/keplergl.min.js"></script>
</head>
<body>
  <div id="app"></div>
  <script>
    const MAPBOX_TOKEN = '{mapbox_token}';

    // --- Inline CSV datasets ---
    {dataset_declarations}

    // --- Kepler config ---
    const keplerConfig = {config_json};

    // Bootstrap Redux store with kepler reducer, seeding the mapbox token into initial state
    const keplerReducer = KeplerGl.keplerGlReducer.initialState({{
      mapStyle: {{ mapboxApiAccessToken: MAPBOX_TOKEN }},
      uiState: {{
        activeSidePanel: null,
        currentModal: null,
      }}
    }});

    const store = Redux.createStore(
      Redux.combineReducers({{ keplerGl: keplerReducer }}),
      {{}},
      window.__REDUX_DEVTOOLS_EXTENSION__
        ? window.__REDUX_DEVTOOLS_EXTENSION__()
        : f => f
    );

    // Seed the token into the store via the init action so style loading works
    store.dispatch(KeplerGl.keplerGlInit({{ mapboxApiAccessToken: MAPBOX_TOKEN }}));

    // Render the KeplerGl React component
    const app = React.createElement(
      ReactRedux.Provider,
      {{ store: store }},
      React.createElement(KeplerGl.KeplerGl, {{
        id: 'map',
        mapboxApiAccessToken: MAPBOX_TOKEN,
        width: window.innerWidth,
        height: window.innerHeight,
      }})
    );

    ReactDOM.render(app, document.getElementById('app'));

    // Build dataset objects and dispatch addDataToMap
    const datasets = [
      {dataset_objects}
    ];

    store.dispatch(KeplerGl.addDataToMap({{
      datasets: datasets,
      config: keplerConfig,
    }}));

    // Keep map full-screen on resize
    window.addEventListener('resize', () => {{
      store.dispatch({{
        type: '@@kepler.gl/UPDATE_MAP',
        payload: {{ width: window.innerWidth, height: window.innerHeight }},
      }});
    }});
  </script>
</body>
</html>
"""


def _build_html(title, datasets_dict, config):
    """
    Build a standalone HTML string with inline CSV data and client-side kepler.gl.

    datasets_dict: {data_id: (label, DataFrame), ...}
    config: kepler config dict (visState, mapState, mapStyle)
    """
    # Build JS variable declarations for each CSV dataset
    declarations = []
    dataset_objects = []

    for data_id, (label, df) in datasets_dict.items():
        var_name = f"csv_{data_id.replace('-', '_')}"
        csv_str = _df_to_csv_string(df)
        # Escape backticks and backslashes for JS template literal
        csv_escaped = csv_str.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
        declarations.append(f"const {var_name} = `{csv_escaped}`;")
        dataset_objects.append(
            f'{{ info: {{ id: "{data_id}", label: "{label}" }}, '
            f'data: KeplerGl.processCsvData({var_name}) }}'
        )

    return _HTML_TEMPLATE.format(
        title=title,
        mapbox_token=MAPBOX_TOKEN,
        dataset_declarations="\n    ".join(declarations),
        config_json=json.dumps(config, indent=2),
        dataset_objects=",\n      ".join(dataset_objects),
    )


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
    datasets = {
        crime_data_id: (f"Crime Data ({label})", crime_df),
        "census": ("Census Demographics", census_points_df),
        "crime_rate": ("Crime per 1,000 Residents", crime_rate_df),
    }

    title = f"GTA Crime Map - {label}"
    html = _build_html(title, datasets, config)

    # Write output
    output_dir = os.path.join(_project_root, 'data', '03_visualizations')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'crime_map_{label}.html')

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
