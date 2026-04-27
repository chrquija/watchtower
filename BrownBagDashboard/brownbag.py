import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import io
# (no local file access or mock generation needed)
from MapMap import render_map
from apples import render_apples_tab
from adt import ADT_REGISTRY, render_adt_tab, get_adt_export_data, get_segment_adt_dataframe, SEGMENT_REGISTRY
# (no local file access or mock generation needed)

# Set page configuration
st.set_page_config(
    page_title="Intersection Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
DIRECTION_MAP = {
    "N": "Northbound", "S": "Southbound", "E": "Eastbound", "W": "Westbound",
    "NB": "Northbound", "SB": "Southbound", "EB": "Eastbound", "WB": "Westbound",
    "NE": "Northeast", "NW": "Northwest", "SE": "Southeast", "SW": "Southwest"
}

# Standardized color scheme for directions/approaches
DIRECTION_COLORS = {
    "Northbound": "#3b82f6", # Blue
    "Southbound": "#f97316", # Orange
    "Eastbound": "#10b981",  # Emerald
    "Westbound": "#ef4444",  # Red
    "Northeast": "#8b5cf6",  # Violet
    "Northwest": "#f59e0b",  # Amber
    "Southeast": "#ec4899",  # Pink
    "Southwest": "#06b6d4",  # Cyan
}

# Registry of available intersections
INTERSECTION_REGISTRY = [
    {
        "label": "N PALM CANYON DR & W SAN RAFAEL RD & TRAMWAY RD",
        "lat": 33.85832,
        "lon": -116.55739,
        "city": "City of Palm Springs, California",
        "corridor": "North Palm Canyon Drive",
        "datasets": [
            {
                "date_label": "Default",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/W_SAN_RAFAEL_RD_and_TRAMWAY_RD.xlsx"
            }
        ]
    },
    {
        "label": "Fred Waring Drive and Warner Trail",
        "lat": 33.72898,
        "lon": -116.31262,
        "city": "City of Indian Wells, California",
        "corridor": "Fred Waring Drive",
        "datasets": [
            {
                "date_label": "Default",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/1_Fredwaringdrive_and_WarnerTrail.xlsx"
            }
        ]
    },
    {
        "label": "Fred Waring Drive and Entrada Las Brisas",
        "lat": 33.72898,
        "lon": -116.30824,
        "city": "City of Indian Wells, California",
        "corridor": "Fred Waring Drive",
        "datasets": [
            {
                "date_label": "Default",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/2-Fredwaringdrive_and_EntradaLasBrisas.xlsx"
            }
        ]
    },
    {
        "label": "Washington Street and Fred Waring Drive",
        "lat": 33.72899,
        "lon": -116.303895,
        "city": "City of Indian Wells, California",
        "corridor": "Washington Street",
        "datasets": [
            {
                "date_label": "March 7 – March 9, 2025",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/3_WashingtonSt_and_FredWaringDrive.xlsx"
            },
            {
                "date_label": "March 14, 2025",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/115_TMC_WashingtonSt_and_FredWaringDr_Mar142025.xlsx"
            },
            {
                "date_label": "March 9 – March 16, 2025",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/115_TMC_WashingtonSt_and_FredWaringDr_Mar9toMar162025.xlsx"
            },
            {
                "date_label": "March 8 – March 15, 2026",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/115_TMC_WashingtonSt_and_FredWaringDr_Mar8toMar152026.xlsx"
            }
        ]
    },
    {
        "label": "Washington Street and Via Servilla",
        "lat": 33.72486,
        "lon": -116.3015,
        "city": "City of Indian Wells, California",
        "corridor": "Washington Street",
        "datasets": [
            {
                "date_label": "Default",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/4_WashingtonSt_ViaServilla.xlsx"
            }
        ]
    },
    {
        "label": "Washington Street and Miles Avenue",
        "lat": 33.72177,
        "lon": -116.29775,
        "city": "City of Indian Wells, California",
        "corridor": "Washington Street",
        "datasets": [
            {
                "date_label": "Default",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/5_WashingtonSt_and_MilesAvenue.xlsx"
            }
        ]
    },
    {
        "label": "Miles Avenue and Warner Trail",
        "lat": 33.72258,
        "lon": -116.312625,
        "city": "City of Indian Wells, California",
        "corridor": "Miles Avenue",
        "datasets": [
            {
                "date_label": "Default",
                "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/6_MilesAvenue_and_WarnerTrail.xlsx"
            }
        ]
    }
]

# Default intersection name
DEFAULT_INTERSECTION_NAME = "N PALM CANYON DR & W SAN RAFAEL RD & TRAMWAY RD"


# --- Data Loading Functions ---


@st.cache_data
def load_data(source: str):
    """Load data from a local path or URL. Returns tuple of DataFrames or None on failure.

    Expected sheets:
      - Metadata
      - Intersection
      - By Approach
      - By Movement
    """
    def _read_all(src: str):
        xls = pd.ExcelFile(src)
        available = set([s.strip() for s in xls.sheet_names])

        required = {
            "Metadata": None,
            "Intersection": None,
            "By Approach": None,
            "By Movement": None,
        }

        missing = [name for name in required.keys() if name not in available]
        if missing:
            st.error(
                "Missing required sheet(s) in workbook: "
                + ", ".join(missing)
                + f". Found: {', '.join(available)}"
            )
            return None

        df_meta = pd.read_excel(xls, sheet_name="Metadata")
        df_int = pd.read_excel(xls, sheet_name="Intersection")
        df_app = pd.read_excel(xls, sheet_name="By Approach")
        df_mov = pd.read_excel(xls, sheet_name="By Movement")
        return df_meta, df_int, df_app, df_mov

    try:
        # Primary attempt
        data = _read_all(source)
        if data is not None:
            return data
        return None
    except Exception as e:
        # If user provided a GitHub raw URL with refs/heads, try the simplified branch form
        if isinstance(source, str) and "refs/heads/" in source:
            alt = source.replace("refs/heads/", "")
            try:
                data = _read_all(alt)
                if data is not None:
                    st.info("Loaded data from alternate URL format of the provided GitHub raw link.")
                    return data
            except Exception:
                pass
        st.error(f"Error reading Excel file: {e}")
        return None


def get_meta_value(df_meta, key, fallback="N/A"):
    """Helper to look up values from the two-column Metadata sheet by key name."""
    try:
        col_keys = df_meta.columns[0]
        col_vals = df_meta.columns[1]
        match = df_meta[df_meta[col_keys].astype(str).str.strip() == key]
        if not match.empty:
            return str(match.iloc[0][col_vals]).strip()
    except Exception:
        pass
    return fallback


@st.cache_data
def load_all_intersections_data(registry):
    """Load "By Approach" data from all intersections in the registry and combine into one DataFrame."""
    all_app_dfs = []

    # Use a placeholder for warnings to avoid showing them multiple times in a loop
    # or if we are in a non-UI thread (though st.warning is usually fine).
    for entry in registry:
        try:
            # Use the first dataset URL for each intersection in corridor analysis
            url = entry["datasets"][0]["url"]
            data = load_data(url)
            if data is None:
                continue
            _, _, df_app, _ = data
            
            # Copy to avoid modifying the cached data
            df_app = df_app.copy()
            df_app["Intersection"] = entry["label"]
            
            # Map approach names using the global DIRECTION_MAP
            df_app["Approach"] = df_app["Approach"].astype(str).str.strip()
            df_app["Approach Full"] = df_app["Approach"].map(DIRECTION_MAP).fillna(df_app["Approach"])
            
            # Normalize percentage columns if they are on 0-100 scale
            for col in ["Arrivals On Green Range 1", "Split Failures Range 1"]:
                if col in df_app.columns:
                    if df_app[col].max() > 1:
                        df_app[col] = df_app[col] / 100.0
            
            all_app_dfs.append(df_app)
        except Exception as e:
            st.warning(f"Warning: Failed to load data for {entry['label']}. {e}")
            
    if not all_app_dfs:
        return pd.DataFrame()
        
    df_all = pd.concat(all_app_dfs, ignore_index=True)
    return df_all


# --- Main Application ---

def main():
    # Global Plotly configuration for all tooltips
    pio.templates.default = "plotly"
    pio.templates[pio.templates.default].layout.hoverlabel.font.size = 18
    
    # Global CSS for Streamlit and Folium tooltips
    st.markdown("""
        <style>
        /* Streamlit tooltip font size */
        div[data-baseweb="tooltip"] {
            font-size: 18px !important;
        }
        /* Folium tooltip font size (for those in the main DOM) */
        .leaflet-tooltip {
            font-size: 18px !important;
        }
        /* Extra Streamlit tooltip target */
        .stTooltip {
            font-size: 18px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 0. Sidebar: Analysis Mode selector
    st.sidebar.markdown("## Analysis Mode")
    analysis_mode = st.sidebar.radio(
        "Select Mode",
        options=["Intersection Analysis", "ADT Analysis"],
        index=0
    )
    st.sidebar.markdown("---")

    # 1.5. Sidebar: Map Settings section
    st.sidebar.markdown("## Map Settings")
    use_satellite = st.sidebar.checkbox("Satellite View", value=False)
    st.sidebar.markdown("---")

    # 1. Sidebar: Settings section
    if analysis_mode == "Intersection Analysis":
        st.sidebar.markdown("## Settings")
        selected_name = st.sidebar.selectbox(
            "Intersection",
            options=[i["label"] for i in INTERSECTION_REGISTRY],
            index=[i["label"] for i in INTERSECTION_REGISTRY].index(DEFAULT_INTERSECTION_NAME)
        )

        # Get details for the selected intersection
        selected = next(i for i in INTERSECTION_REGISTRY if i["label"] == selected_name)

        # If this intersection has multiple datasets, show a date range selector
        if len(selected["datasets"]) > 1:
            date_labels = [d["date_label"] for d in selected["datasets"]]
            chosen_date_label = st.sidebar.selectbox(
                "SELECT DATE RANGE",
                options=date_labels,
                index=0
            )
            chosen_dataset = next(d for d in selected["datasets"] if d["date_label"] == chosen_date_label)
        else:
            chosen_dataset = selected["datasets"][0]

        DATA_URL = chosen_dataset["url"]
    else:
        # ADT Analysis Mode
        st.sidebar.markdown("## ADT Settings")
        all_corridors = sorted(list(set([c for entry in ADT_REGISTRY for c in entry["corridors"]])))
        selected_corridor = st.sidebar.selectbox("Select Corridor", options=all_corridors)
        adt_sort_order = st.sidebar.selectbox("Sort Segments By", options=["Registry Order", "ADT (High to Low)", "ADT (Low to High)"])
        adt_show_raw = st.sidebar.checkbox("Show Raw Data Table", value=False)
        
        # We still need a 'selected' intersection for the rest of the app scaffolding
        corridor_intersections = [entry for entry in ADT_REGISTRY if selected_corridor in entry["corridors"]]
        if corridor_intersections:
            selected_name = corridor_intersections[0]["label"]
        else:
            selected_name = DEFAULT_INTERSECTION_NAME
            
        selected = next((i for i in INTERSECTION_REGISTRY if i["label"] == selected_name), INTERSECTION_REGISTRY[0])
        DATA_URL = selected["datasets"][0]["url"]

    # --- Export Helper ---
    def generate_excel_bytes(df_dict):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in df_dict.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        return output.getvalue()

    # Load data early to use metadata for labels
    data = load_data(DATA_URL)
    if data is None:
        st.stop()
    df_meta, df_int, df_app, df_mov = data

    # 2. Extract metadata dynamically
    primary_street = get_meta_value(df_meta, "Primary Street")
    secondary_street = get_meta_value(df_meta, "Secondary Street")
    tertiary_street = get_meta_value(df_meta, "Tertiary Street", "N/A")
    
    city = selected.get("city", "N/A")
    if city == "N/A":
        # try "City" first, then fallback to Intersection
        city = get_meta_value(df_meta, "City", "N/A")
        if city == "N/A":
            city = get_meta_value(df_meta, "Intersection", "N/A")
    
    # User requested to replace any variant of "City of Indio, California" 
    # with "City of Indian Wells, California"
    if city.lower().strip() in ["city of indio, california", "city of indio", "city of indio california"]:
        city = "City of Indian Wells, California"

    start_date = get_meta_value(df_meta, "Start Date")
    end_date = get_meta_value(df_meta, "End Date")
    date_range = f"{start_date} to {end_date}"

    intersection = selected["label"]
    coordinates = f"{selected['lat']}, {selected['lon']}"
    Data_Source = get_meta_value(df_meta, "Data Source", "ITERIS CLEARGUIDE")

    corridor = selected["corridor"]
    if corridor == "N/A":
        corridor = selected["label"]

    if analysis_mode == "Intersection Analysis":
        st.sidebar.markdown("## Location Info")
        st.sidebar.markdown(
            f"""
- **Data Source:** {Data_Source}
- **Date Range:** {date_range}
- **City:** {city}
- **Intersection:** {intersection}
- **Corridor:** {corridor}
- **Primary:** {primary_street}
- **Secondary:** {secondary_street}
- **Tertiary:** {tertiary_street}
- **Coordinates:** {coordinates}
            """
        )

    # Optional toggles for showing details in the main area
    show_details_in_header = st.sidebar.checkbox("Show metadata in banner", value=False)

    # 3. Sidebar: Export Data Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Export Data")
    
    if analysis_mode == "Intersection Analysis":
        export_df_dict = {
            "Metadata": df_meta,
            "Intersection": df_int,
            "By Approach": df_app,
            "By Movement": df_mov
        }
        export_filename = f"Intersection_{intersection.replace(' ', '_').replace('&', 'and')}.xlsx"
        
        excel_data = generate_excel_bytes(export_df_dict)
        st.sidebar.download_button(
            label="Download Intersection Data (Excel)",
            data=excel_data,
            file_name=export_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # ADT Analysis Mode
        export_filename = f"Corridor_{selected_corridor.replace(' ', '_').replace('→', 'to')}.xlsx"
        # We fetch the data for the whole corridor
        with st.sidebar:
            if st.button("Prepare Corridor Export"):
                with st.spinner("Gathering data..."):
                    adt_export_data = get_adt_export_data(
                        selected_corridor, ADT_REGISTRY, load_data, get_meta_value, DIRECTION_MAP
                    )
                    if adt_export_data:
                        excel_data = generate_excel_bytes(adt_export_data)
                        st.download_button(
                            label="Click to Download ADT Data",
                            data=excel_data,
                            file_name=export_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("Failed to gather corridor data.")

    # Compact header (title + key subtitle only)
    header_html = f"""<style>
.bbg-header {{
    background: #1f4582;
    color: #ffffff;
    padding: 16px 24px;
    border-radius: 14px;
    margin-bottom: 14px;
}}
.bbg-header .company {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    opacity: 0.75;
    margin: 0 0 4px 0;
}}
.bbg-header h1 {{
    margin: 0 0 4px 0;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}
.bbg-header .subtitle {{
    display: inline-block;
    margin: 6px 12px 0 0;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.4px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 20px;
    padding: 4px 14px;
    opacity: 1;
}}
.bbg-header .datasource {{
    display: inline-block;
    margin: 6px 0 0 0;
    font-size: 13px;
    font-weight: 400;
    opacity: 0.85;
}}
.bbg-header .datasource a {{
    color: #ffffff;
    text-decoration: underline;
    text-underline-offset: 2px;
}}
.bbg-header .datasource a:hover {{
    opacity: 1;
    color: #ffffff;
}}
.bbg-meta {{
    display: grid;
    grid-template-columns: repeat(2, minmax(200px, 1fr));
    gap: 4px 16px;
    font-size: 13px;
    margin-top: 10px;
}}
.bbg-meta div span {{ opacity: 0.9; }}
@media (max-width: 800px) {{ .bbg-meta {{ grid-template-columns: 1fr; }} }}
</style>
<div class="bbg-header">
<p class="company">Advantec Consulting Engineers</p>
<h1>INTERSECTION PERFORMANCE DASHBOARD</h1>
<p class="subtitle">📍 {intersection}</p>
<p class="datasource">Data Source: <a href="{DATA_URL}" target="_blank">{Data_Source}</a></p>
{f'<div class="bbg-meta">\n<div><strong>Corridor:</strong> <span>{corridor}</span></div>\n<div><strong>City:</strong> <span>{city}</span></div>\n<div><strong>Date Range:</strong> <span>{date_range}</span></div>\n<div><strong>Coordinates:</strong> <span>{coordinates}</span></div>\n</div>' if show_details_in_header else ''}
</div>"""

    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown("---")

    # Right rail layout: create persistent two-column canvas
    
    # Make the right rail sticky and a bit thinner via CSS
    st.markdown(
        """<style>
/* Sticky right rail: target the 2nd column's inner block */
div[data-testid="column"]:nth-child(2) > div {
    position: sticky;
    top: 96px; /* leave space for header */
}
/* Disable stickiness on small screens to avoid layout issues */
@media (max-width: 1100px) {
    div[data-testid="column"]:nth-child(2) > div { position: static; }
}
</style>""",
        unsafe_allow_html=True,
    )

    # Make the map column thinner: 8/4 split
    left_col, right_col = st.columns([8, 4], gap="large")

    # Prepare combined registry for the map context
    map_registry = []
    for entry in INTERSECTION_REGISTRY:
        map_registry.append({"label": entry["label"], "lat": entry["lat"], "lon": entry["lon"]})
    for entry in ADT_REGISTRY:
        if not any(e["label"] == entry["label"] for e in map_registry):
            map_registry.append({"label": entry["label"], "lat": entry["lat"], "lon": entry["lon"]})

    # Map stays pinned in the right rail
    with right_col:
        if analysis_mode == "Intersection Analysis":
            # Gather all intersections in this corridor for the map sidebar
            target_corridor = corridor
            relevant_intersections = [
                i for i in INTERSECTION_REGISTRY 
                if i.get("corridor") == target_corridor or (i.get("corridor", "N/A") == "N/A" and i.get("label") == target_corridor)
            ]
            
            intersections_data = []
            seen_urls = set()
            for item in relevant_intersections:
                for ds in item.get("datasets", []):
                    if ds["url"] not in seen_urls:
                        lbl = item["label"]
                        if ds["date_label"] != "Default":
                            lbl = f"{lbl} ({ds['date_label']})"
                        intersections_data.append({"name": lbl, "url": ds["url"]})
                        seen_urls.add(ds["url"])

            corridor_labels = [i["label"] for i in INTERSECTION_REGISTRY if i["corridor"] == selected["corridor"]]
            
            # Calculate days for Intersection Analysis
            try:
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)
                num_days = (ed - sd).days + 1
                study_period_str = f"{date_range} ({num_days} days)"
            except:
                study_period_str = date_range

            render_map(
                latitude=selected["lat"],
                longitude=selected["lon"],
                height=900,  # longer map
                zoom=None,
                label=intersection,
                registry=map_registry,
                use_satellite=use_satellite,
                highlight_labels=corridor_labels,
                study_period=study_period_str,
                intersections=intersections_data
            )
        else:
            # ADT Analysis Mode: Dynamic corridor view
            corridor_entries = [entry for entry in ADT_REGISTRY if selected_corridor in entry["corridors"]]
            
            intersections_data = []
            seen_urls = set()
            for item in corridor_entries:
                if item["url"] not in seen_urls:
                    intersections_data.append({"name": item["label"], "url": item["url"]})
                    seen_urls.add(item["url"])

            # Determine corridor-wide Study Period
            corridor_date_range = "N/A"
            start = None
            end = None
            for entry in corridor_entries:
                # Use load_data logic (already in current file)
                data = load_data(entry["url"])
                if data:
                    df_meta = data[0]
                    curr_start = get_meta_value(df_meta, "Start Date")
                    curr_end = get_meta_value(df_meta, "End Date")
                    file_range = f"{curr_start} to {curr_end}"
                    if corridor_date_range == "N/A":
                        corridor_date_range = file_range
                        start = curr_start
                        end = curr_end
                    elif corridor_date_range != file_range:
                        corridor_date_range = "Mixed"
                        break

            if corridor_date_range != "N/A" and corridor_date_range != "Mixed":
                try:
                    sd = pd.to_datetime(start)
                    ed = pd.to_datetime(end)
                    num_days = (ed - sd).days + 1
                    corridor_study_period_str = f"{corridor_date_range} ({num_days} days)"
                except:
                    corridor_study_period_str = corridor_date_range
            else:
                corridor_study_period_str = corridor_date_range

            # Fetch Segment ADT Data for the map
            df_segments = get_segment_adt_dataframe(
                selected_corridor=selected_corridor,
                segment_registry=SEGMENT_REGISTRY,
                adt_registry=ADT_REGISTRY,
                load_data_func=load_data,
                get_meta_value_func=get_meta_value,
                direction_map=DIRECTION_MAP
            )

            corridor_labels = [entry["label"] for entry in corridor_entries]
            render_map(
                height=900,
                label=selected_corridor,
                registry=map_registry,
                use_satellite=use_satellite,
                highlight_labels=corridor_labels,
                study_period=corridor_study_period_str,
                intersections=intersections_data,
                segments=df_segments
            )

            # --- ADT Data Tables in Right Rail ---
            st.divider()
            st.markdown("### Corridor Data Tables")
            table_choice = st.selectbox(
                "Flip through chart data:",
                options=[
                    "MidPoint ADT By Subsegment",
                    "Directional ADT Comparison",
                    "Turning Movement Share"
                ]
            )

            if table_choice == "MidPoint ADT By Subsegment":
                if not df_segments.empty:
                    st.dataframe(
                        df_segments[["Subsegment", "Direction Label", "Directional ADT", "Two-Way Segment ADT", "DateRange"]]
                        .style.format({
                            "Directional ADT": "{:,.0f}",
                            "Two-Way Segment ADT": "{:,.0f}"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No subsegment data available.")

            elif table_choice == "Directional ADT Comparison":
                # Need to load/compute directional ADT for all intersections
                all_approach_adt = []
                for entry in corridor_entries:
                    data = load_data(entry["url"])
                    if data:
                        df_app_local = data[2]
                        df_meta_local = data[0]
                        # Helper from adt.py is not easily accessible here without import
                        # but we have DIRECTION_MAP and get_meta_value
                        from adt import compute_approach_adt
                        app_adt = compute_approach_adt(df_app_local, df_meta_local, DIRECTION_MAP, get_meta_value)
                        app_adt["Intersection"] = entry["label"]
                        all_approach_adt.append(app_adt)
                
                if all_approach_adt:
                    df_dir_all = pd.concat(all_approach_adt, ignore_index=True)
                    valid_dirs = ["N", "S", "E", "W", "NB", "SB", "EB", "WB", "NE", "NW", "SE", "SW"]
                    df_dir_all = df_dir_all[df_dir_all["Approach"].isin(valid_dirs)]
                    st.dataframe(
                        df_dir_all[["Intersection", "Approach Full", "ADT", "DateRange"]]
                        .style.format({"ADT": "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No directional ADT data available.")

            elif table_choice == "Turning Movement Share":
                all_mov_shares = []
                for entry in corridor_entries:
                    data = load_data(entry["url"])
                    if data:
                        df_mov_local = data[3]
                        df_meta_local = data[0]
                        start_l = get_meta_value(df_meta_local, "Start Date")
                        end_l = get_meta_value(df_meta_local, "End Date")
                        from adt import compute_movement_share
                        mov_share = compute_movement_share(df_mov_local)
                        mov_share["Intersection"] = entry["label"]
                        mov_share["DateRange"] = f"{start_l} to {end_l}"
                        all_mov_shares.append(mov_share)
                
                if all_mov_shares:
                    df_mov_all = pd.concat(all_mov_shares, ignore_index=True)
                    st.dataframe(
                        df_mov_all[["Intersection", "Movement", "Share", "DateRange"]]
                        .style.format({"Share": "{:.1%}"}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No movement share data available.")

    # All analytics content lives inside the left column
    with left_col:
        # Create tabs for different analysis sections
        tabs = ["Average Daily Traffic (ADT)", "Intersection Analysis", "Corridor-Wide Regression", "Apples-to-Apples"]
        tab_adt, tab1, tab2, tab3 = st.tabs(tabs)

        # Helper to format percentages safely (handles 0.78 vs 78)
        def format_percent(val):
            if pd.isna(val):
                return "N/A"
            # Changed > to >= so that a value of exactly 1 is treated as 1%, not 100%
            if val >= 1:
                return f"{val:.1f}%"  # Assumes 0-100 scale
            return f"{val:.1%}"       # Assumes 0-1 scale

        with tab_adt:
            if analysis_mode == "ADT Analysis":
                render_adt_tab(
                    selected_corridor=selected_corridor,
                    adt_registry=ADT_REGISTRY,
                    load_data_func=load_data,
                    get_meta_value_func=get_meta_value,
                    direction_map=DIRECTION_MAP,
                    direction_colors=DIRECTION_COLORS,
                    sort_by=adt_sort_order,
                    show_raw=adt_show_raw
                )
            else:
                st.info("Switch to **ADT Analysis** mode in the sidebar to view corridor-wide traffic volumes.")

        with tab1:
            # 1. High-level KPIs (Intersection Sheet)
            st.subheader("High-Level KPIs")

            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

            with kpi_col1:
                val = df_int["Delay Range 1"].iloc[0]
                st.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 15px 5px; border-radius: 12px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 120px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.8rem; color: #1f4582; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 8px; line-height: 1.2;">Average Delay (s)</div>
    <div style="font-size: 1.8rem; font-weight: 900; color: var(--text-color); line-height: 1;">{val:.1f}</div>
    <div style="font-size: 0.85rem; font-weight: 600; opacity: 0.7; margin-top: 4px;">seconds</div>
</div>
""", unsafe_allow_html=True)

            with kpi_col2:
                val = df_int["Arrivals On Green Range 1"].iloc[0]
                st.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 15px 5px; border-radius: 12px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 120px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.8rem; color: #1f4582; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 8px; line-height: 1.2;">Arrivals On Green</div>
    <div style="font-size: 1.8rem; font-weight: 900; color: var(--text-color); line-height: 1;">{format_percent(val)}</div>
</div>
""", unsafe_allow_html=True)

            with kpi_col3:
                val = df_int["Split Failures Range 1"].iloc[0]
                st.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 15px 5px; border-radius: 12px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 120px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.8rem; color: #1f4582; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 8px; line-height: 1.2;">Split Failures</div>
    <div style="font-size: 1.8rem; font-weight: 900; color: var(--text-color); line-height: 1;">{format_percent(val)}</div>
</div>
""", unsafe_allow_html=True)

            with kpi_col4:
                val = df_int["Vehicle Samples 1"].iloc[0]
                st.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 15px 5px; border-radius: 12px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 120px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.8rem; color: #1f4582; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 8px; line-height: 1.2;">Total Vehicles</div>
    <div style="font-size: 1.8rem; font-weight: 900; color: var(--text-color); line-height: 1;">{int(val):,}</div>
    <div style="font-size: 0.85rem; font-weight: 600; opacity: 0.7; margin-top: 4px;">vehicles</div>
</div>
""", unsafe_allow_html=True)

            # 2. Approach Analysis (By Approach Sheet)
            st.markdown("---")
            st.subheader("Performance by Approach Visualizations")

            # Create cleaned and mapped approach names for df_app
            df_app_plot = df_app.copy()
            df_app_plot["Approach"] = df_app_plot["Approach"].astype(str).str.strip()
            df_app_plot["Approach Full"] = df_app_plot["Approach"].map(DIRECTION_MAP).fillna(df_app_plot["Approach"])

            col_chart_1, col_chart_2 = st.columns(2)

            with col_chart_1:
                fig_delay = px.bar(
                    df_app_plot,
                    x="Approach Full",
                    y="Delay Range 1",
                    title=f"<b>{intersection}</b><br><sup>Average Delay by Approach | {date_range}</sup>",
                    text_auto='.1f',
                    color="Delay Range 1",
                    color_continuous_scale="RdYlGn_r",  # High delay = Red
                    labels={"Delay Range 1": "Average Delay (s)", "Approach Full": "Approach"},
                    hover_data={"Approach Full": True, "Delay Range 1": ":.1f"}
                )
                fig_delay.update_layout(
                    showlegend=False,
                    title_font_size=26,
                    yaxis_title="Control Delay (seconds)",
                    xaxis=dict(
                        title=dict(text="<b>Approach</b>", font=dict(size=22)),
                        tickfont=dict(size=18)
                    ),
                    yaxis=dict(
                        title=dict(text="<b>Control Delay (seconds)</b>", font=dict(size=22)),
                        tickfont=dict(size=18)
                    ),
                    uniformtext_minsize=10,
                    uniformtext_mode='show'
                )
                # Improve Tooltips + Increase text size inside bars
                fig_delay.update_traces(
                    textfont_size=20,
                    textposition="auto",
                    cliponaxis=False,
                    hovertemplate="<b>Approach:</b> %{x}<br><b>Average Delay:</b> %{y:.1f} seconds<extra></extra>"
                )

                st.plotly_chart(fig_delay, use_container_width=True)

            with col_chart_2:
                # Comparison of Volume vs Split Failures
                fig_combo = go.Figure()

                # Bar for Volume (Use Vehicle Samples 1)
                # Check if column exists, otherwise fallback
                vol_col = "Vehicle Samples 1" if "Vehicle Samples 1" in df_app_plot.columns else "Turning Movement Range 1"

                fig_combo.add_trace(go.Bar(
                    x=df_app_plot["Approach Full"],
                    y=df_app_plot[vol_col],
                    text=df_app_plot[vol_col],
                    texttemplate='%{text:,.0f}',
                    textposition='auto',
                    name="Vehicles",
                    marker_color='rgb(55, 83, 109)',
                    textfont=dict(size=18),
                    hovertemplate="<b>Approach:</b> %{x}<br><b>Vehicles:</b> %{y:,}<extra></extra>"
                ))

                # Line for Split Failures
                # DIVIDE BY 100 to convert integer 4 to 0.04 (4%)
                split_fail_values = df_app_plot["Split Failures Range 1"] / 100.0

                fig_combo.add_trace(go.Scatter(
                    x=df_app_plot["Approach Full"],
                    y=split_fail_values,
                    name="Split Failure %",
                    yaxis="y2",
                    mode="lines+markers+text",
                    text=split_fail_values,
                    texttemplate='%{text:.1%}',
                    textposition="top center",
                    textfont=dict(size=16),
                    line=dict(color='rgb(219, 64, 82)', width=3),
                    hovertemplate="<b>Approach:</b> %{x}<br><b>Split Failure:</b> %{y:.1%}<extra></extra>"
                ))

                fig_combo.update_layout(
                    title=f"<b>{intersection}</b><br><sup>Vehicles vs. Split Failures | {date_range}</sup>",
                    title_font_size=26,
                    uniformtext_minsize=10,
                    uniformtext_mode='show',
                    margin=dict(t=120, b=100),
                    xaxis=dict(
                        title=dict(text="<b>Approach</b>", font=dict(size=22)),
                        tickfont=dict(size=18)
                    ),
                    yaxis=dict(
                        title=dict(text="<b>Vehicles</b>", font=dict(size=22)),
                        tickfont=dict(size=18)
                    ),
                    yaxis2=dict(
                        title=dict(text="<b>Split Failures %</b>", font=dict(size=22)),
                        overlaying="y",
                        side="right",
                        tickformat=".1%",
                        tickfont=dict(size=18)
                    ),
                    legend=dict(
                        orientation="h", 
                        yanchor="top", 
                        y=-0.15, 
                        xanchor="center", 
                        x=0.5,
                        font=dict(size=20),
                        itemsizing='constant'
                    )
                )
                st.plotly_chart(fig_combo, use_container_width=True)

            # 3. Detailed Movement Analysis (By Movement Sheet)
            st.markdown("---")
            st.subheader("Movement Details")

            # Map for human-readable metrics
            metric_map = {
                "Avg Control Delay (seconds)": "Delay Range 1",
                "Arrivals On Green %": "Arrivals On Green Range 1",
                "Split Failure %": "Split Failures Range 1",
                "Vehicles": "Vehicle Samples 1"  # Assuming we want sample count here too
            }

            # Check if 'Vehicle Samples 1' exists in df_mov, if not use Turning Movement
            if "Vehicle Samples 1" not in df_mov.columns:
                metric_map["Vehicles"] = "Turning Movement Range 1"

            # Filter controls
            col_filter, col_display = st.columns([1, 3])

            with col_filter:
                st.write("**Filter Data**")

                # Clean and map all approaches for filtering and display
                df_mov_plot = df_mov.copy()
                df_mov_plot["Approach"] = df_mov_plot["Approach"].astype(str).str.strip()
                df_mov_plot["Approach Full"] = df_mov_plot["Approach"].map(DIRECTION_MAP).fillna(df_mov_plot["Approach"])

                # Get unique mapped approach names for the filter
                app_labels = sorted(list(df_mov_plot["Approach Full"].unique()))

                selected_labels = st.multiselect(
                    "Select Approach",
                    options=app_labels,
                    default=app_labels
                )

                selected_metric_label = st.selectbox(
                    "Select Metric to Visualize",
                    list(metric_map.keys())
                )
                selected_metric_col = metric_map[selected_metric_label]

            with col_display:
                # Filter by the mapped labels directly
                filtered_df = df_mov_plot[df_mov_plot["Approach Full"].isin(selected_labels)].copy()

                # Handle Percentages (Divide by 100 if needed)
                # Apply to BOTH Split Failure AND Arrivals On Green
                if "Split Failure" in selected_metric_label or "Arrivals On Green" in selected_metric_label:
                    # Check if values are integers > 1 (like 32 for 32%)
                    if filtered_df[selected_metric_col].max() > 1:
                        filtered_df[selected_metric_col] = filtered_df[selected_metric_col] / 100.0

                # Determine text format
                if "Delay" in selected_metric_label:
                    text_fmt = '.1f'
                elif "Volume" in selected_metric_label or "Vehicles" in selected_metric_label:
                    text_fmt = '.0f'
                else:
                    text_fmt = '.1%'

                # Determine hover format
                if "Delay" in selected_metric_label:
                    hover_fmt = ":.1f"
                    metric_unit = " seconds"
                elif "Volume" in selected_metric_label or "Vehicles" in selected_metric_label:
                    hover_fmt = ":,"
                    metric_unit = " vehicles"
                else:
                    hover_fmt = ":.1%"
                    metric_unit = ""

                fig_mov = px.bar(
                    filtered_df,
                    x="Approach Full",
                    y=selected_metric_col,
                    color="Movement",
                    barmode="group",
                    # Title includes intersection name and date range
                    title=f"<b>{intersection}</b><br><sup>{selected_metric_label} by Movement | {date_range}</sup>",
                    text_auto=text_fmt,
                    hover_name="Movement",
                    labels={
                        selected_metric_col: selected_metric_label,
                        "Approach Full": "Approach"
                    },
                    hover_data={
                        "Approach Full": True,
                        "Movement": False,
                        selected_metric_col: hover_fmt
                    }
                )

                # Improve Tooltips + Increase text size inside bars
                fig_mov.update_traces(
                    textfont_size=20,
                    textposition="auto",
                    cliponaxis=False,
                    hovertemplate="<b>Approach:</b> %{x}<br><b>Movement:</b> %{hovertext}<br><b>" + selected_metric_label + ":</b> %{y" + hover_fmt + "}" + metric_unit + "<extra></extra>"
                )

                fig_mov.update_layout(
                    title_font_size=26,
                    uniformtext_minsize=10,
                    uniformtext_mode='show',
                    margin=dict(t=120, b=100),
                    legend=dict(
                        orientation="h", 
                        yanchor="top", 
                        y=-0.15, 
                        xanchor="center", 
                        x=0.5,
                        font=dict(size=20),
                        itemsizing='constant'
                    ),
                    xaxis=dict(
                        title=dict(text="<b>Approach</b>", font=dict(size=22)),
                        tickfont=dict(size=18)
                    ),
                    yaxis=dict(
                        title=dict(text=f"<b>{selected_metric_label}</b>", font=dict(size=22)),
                        tickfont=dict(size=18)
                    )
                )

                st.plotly_chart(fig_mov, use_container_width=True)

            # Raw Data Expander
            with st.expander("View Raw Data"):
                st.write("Intersection Data", df_int)
                st.write("Approach Data", df_app)
                st.write("Movement Data", df_mov)

        # Tab 2: Corridor-Wide Regression Analysis
        with tab2:
            st.subheader("Corridor-Wide Regression Analysis (CONCEPT)")

            df_all = load_all_intersections_data(INTERSECTION_REGISTRY)

            if not df_all.empty:
                # Data Coverage Logic
                n_points = len(df_all)
                n_intersections = df_all["Intersection"].nunique()

                missing_items = []
                standard_directions = ["Northbound", "Southbound", "Eastbound", "Westbound"]
                diagonal_directions = ["Northeast", "Southeast", "Southwest", "Northwest"]

                for entry in INTERSECTION_REGISTRY:
                    intersection_data = df_all[df_all["Intersection"] == entry["label"]]
                    found_directions = intersection_data["Approach Full"].tolist()

                    # Determine which set they use
                    if any(d in found_directions for d in diagonal_directions):
                        expected = diagonal_directions
                    else:
                        expected = standard_directions

                    missing = [d for d in expected if d not in found_directions]
                    for m in missing:
                        missing_items.append(f"{entry['label']} — {m}")

                missing_help = ""
                if missing_items:
                    missing_help = f"\n\n**Missing/Excluded:** {', '.join(missing_items)}"

                st.markdown(
                    f"**Data Coverage:** {n_points} approaches across {n_intersections} intersections",
                    help=f"An 'approach' = intersection + direction (e.g., 'Washington & Miles — Eastbound'). "
                         f"With 7 intersections, up to 28 approaches are possible (7×4). "
                         f"Data may be missing due to detector issues or filtered out for quality.{missing_help}"
                )

                reg_col1, reg_col2 = st.columns(2)

                with reg_col1:
                    x_options = {
                        "Volume (vehicles)": "Vehicle Samples 1",
                        "Arrivals on Green (%)": "Arrivals On Green Range 1",
                        "Split Failures (%)": "Split Failures Range 1"
                    }
                    x_label = st.selectbox(
                        "Independent Variable (X) — the input/cause",
                        options=list(x_options.keys()),
                        help="The independent variable is what we believe drives or influences the outcome. For traffic engineers: Volume measures demand pressure on the signal."
                    )
                    x_col = x_options[x_label]

                with reg_col2:
                    y_options = {
                        "Average Delay (seconds)": "Delay Range 1",
                        "Split Failures (%)": "Split Failures Range 1",
                        "Arrivals on Green (%)": "Arrivals On Green Range 1"
                    }
                    y_label = st.selectbox(
                        "Dependent Variable (Y) — the outcome/effect",
                        options=list(y_options.keys()),
                        help="The dependent variable is the performance outcome we are trying to explain or predict. For traffic engineers: Delay is the key measure of how well the signal is serving demand."
                    )
                    y_col = y_options[y_label]

                if x_col == y_col:
                    st.warning("Please select different variables for X and Y axes.")
                else:
                    # --- 1. Statistical Calculations (Pre-Visualization) ---
                    # Prepare chart (and calculate regression internally)
                    try:
                        fig_reg = px.scatter(
                            df_all,
                            x=x_col,
                            y=y_col,
                            color="Intersection",
                            symbol="Approach Full",
                            trendline="ols",
                            trendline_scope="overall",
                            title=f"<b>{x_label} vs. {y_label}</b><br><sup>Corridor Regression Analysis</sup>",
                            hover_name="Intersection",
                            labels={
                                x_col: f"← Independent Variable: {x_label}",
                                y_col: f"Dependent Variable: {y_label} →"
                            },
                            hover_data=["Intersection", "Approach Full"]
                        )
                        fig_reg.update_layout(
                            title_font_size=20,
                            xaxis=dict(
                                title=dict(font=dict(size=16)),
                                tickfont=dict(size=12)
                            ),
                            yaxis=dict(
                                title=dict(font=dict(size=16)),
                                tickfont=dict(size=12)
                            ),
                            legend=dict(
                                title=dict(text="<b>Intersection</b>", font=dict(size=14)),
                                font=dict(size=12),
                                itemsizing='constant'
                            )
                        )
                        has_trendline = True

                        # Extract regression results for KPIs
                        results = px.get_trendline_results(fig_reg)
                        if not results.empty:
                            model = results.iloc[0]["px_fit_results"]
                            r_squared = model.rsquared
                            slope = model.params[1]
                            intercept = model.params[0]
                        else:
                            r_squared, slope, intercept = 0, 0, 0
                    except (ImportError, ModuleNotFoundError):
                        st.warning("Regression analysis requires 'statsmodels' library. Please install it using 'pip install statsmodels' to enable trendlines.")
                        fig_reg = px.scatter(
                            df_all,
                            x=x_col,
                            y=y_col,
                            color="Intersection",
                            symbol="Approach Full",
                            title=f"<b>{x_label} vs. {y_label}</b><br><sup>Corridor Data (Trendline Unavailable)</sup>",
                            labels={
                                x_col: f"← Independent Variable: {x_label}",
                                y_col: f"Dependent Variable: {y_label} →"
                            },
                            hover_data=["Intersection", "Approach Full"]
                        )
                        fig_reg.update_layout(
                            title_font_size=20,
                            xaxis=dict(title=dict(font=dict(size=16))),
                            yaxis=dict(title=dict(font=dict(size=16)))
                        )
                        has_trendline = False
                        r_squared, slope, intercept = 0, 0, 0
                    except Exception as e:
                        st.error(f"Error calculating regression: {e}")
                        fig_reg = px.scatter(
                            df_all,
                            x=x_col,
                            y=y_col,
                            color="Intersection",
                            symbol="Approach Full",
                            title=f"<b>{x_label} vs. {y_label}</b><br><sup>Corridor Data</sup>",
                            labels={
                                x_col: f"← Independent Variable: {x_label}",
                                y_col: f"Dependent Variable: {y_label} →"
                            },
                            hover_data=["Intersection", "Approach Full"]
                        )
                        fig_reg.update_layout(
                            title_font_size=20,
                            xaxis=dict(title=dict(font=dict(size=16))),
                            yaxis=dict(title=dict(font=dict(size=16)))
                        )
                        has_trendline = False
                        r_squared, slope, intercept = 0, 0, 0


                    # --- 3. Visualization ---
                    fig_reg.update_traces(marker=dict(size=12, opacity=0.9, line=dict(width=1, color='DarkSlateGrey')), selector=dict(mode="markers"))

                    # Regression line color: "#E63946" (red), width 3, dash="dash"
                    if has_trendline:
                        fig_reg.update_traces(
                            line=dict(color="#E63946", width=3, dash="dash"),
                            selector=dict(mode="lines"),
                            name="Trendline"
                        )

                    # Tooltip formatting
                    def get_fmt(label):
                        if "Delay" in label: return ":.1f"
                        if "Volume" in label: return ":,.0f"
                        return ":.1%"

                    def get_suffix(label):
                        if "Delay" in label: return " sec"
                        if "Volume" in label: return " vehicles"
                        return ""

                    x_fmt = get_fmt(x_label)
                    x_suffix = get_suffix(x_label)
                    y_fmt = get_fmt(y_label)
                    y_suffix = get_suffix(y_label)

                    fig_reg.update_traces(
                        hovertemplate=(
                            "<b>Intersection:</b> %{customdata[0]}<br>"
                            "<b>Approach:</b> %{customdata[1]}<br>"
                            f"<b>{x_label}:</b> %{{x{x_fmt}}}{x_suffix}<br>"
                            f"<b>{y_label}:</b> %{{y{y_fmt}}}{y_suffix}"
                            "<extra></extra>"
                        ),
                        selector=dict(mode="markers")
                    )

                    # Add n annotation
                    n_points = len(df_all)
                    n_intersections = df_all["Intersection"].nunique()
                    fig_reg.add_annotation(
                        text=f"<b>n = {n_points} approaches across {n_intersections} intersections</b>",
                        xref="paper", yref="paper",
                        x=0.02, y=0.98, showarrow=False,
                        font=dict(size=13),
                        align="left"
                    )

                    # Update layout for better legend and fonts
                    fig_reg.update_layout(
                        margin=dict(l=60, r=20, t=60, b=60),
                        title_font_size=20,
                        legend=dict(
                            title=dict(text="<b>Intersection</b>", font=dict(size=14)),
                            font=dict(size=12),
                            itemsizing='constant'
                        ),
                        font=dict(family="Arial, sans-serif"),
                        xaxis=dict(
                            title=dict(font=dict(size=16)),
                            tickfont=dict(size=12)
                        ),
                        yaxis=dict(
                            title=dict(font=dict(size=16)),
                            tickfont=dict(size=12),
                            title_standoff=15
                        )
                    )

                    st.plotly_chart(fig_reg, use_container_width=True)

                    # Statistical Results
                    if has_trendline:
                        st.markdown("---")
                        st.subheader("Statistical Results & Interpretation")

                        r_percent = r_squared * 100
                        stat_col1, stat_col2 = st.columns([1, 2])

                        with stat_col1:
                            # --- Dynamic R2 Styling & Card ---
                            if r_squared >= 0.8:
                                r2_color, r2_label, st_func = "#28a745", "Very Strong", st.success
                                interp_head = "🟢 **Very Strong Relationship:**"
                            elif r_squared >= 0.6:
                                r2_color, r2_label, st_func = "#ffc107", "Strong", st.warning
                                interp_head = "🟡 **Strong Relationship:**"
                            elif r_squared >= 0.3:
                                r2_color, r2_label, st_func = "#fd7e14", "Moderate", st.warning
                                interp_head = "🟠 **Moderate Relationship:**"
                            else:
                                r2_color, r2_label, st_func = "#dc3545", "Weak", st.error
                                interp_head = "🔴 **Weak Relationship:**"

                            r2_html = f"""<div style="background: {r2_color}15; padding: 24px; border-radius: 15px; border: 1px solid {r2_color}44; text-align: center; margin-bottom: 20px;">
<div style="font-size: 0.85rem; color: var(--text-color); opacity: 0.7; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Relationship Strength (R²)</div>
<div style="font-size: 3.5rem; font-weight: 900; color: {r2_color}; line-height: 1; margin: 0;">{r_squared:.3f}</div>
<div style="font-size: 1.25rem; font-weight: 700; color: {r2_color}; margin-top: 10px;">{r2_label}</div>
</div>"""
                            st.markdown(r2_html, unsafe_allow_html=True)

                            # Predictive Equation Label
                            st.write("**Trendline Equation:**")
                            # Simple y = mx + b form
                            y_short = y_label.split(" (")[0]
                            x_short = x_label.split(" (")[0]
                            sign = "+" if intercept >= 0 else "-"
                            st.code(f"{y_short} = ({slope:.2f} × {x_short}) {sign} {abs(intercept):.2f}", language="python")

                            slope_dir = "Positive" if slope > 0 else "Negative"
                            slope_desc = "higher X tends to correspond to higher Y" if slope > 0 else "higher X tends to correspond to lower Y"
                            st.markdown(f"**Slope:** {slope_dir}")
                            st.caption(slope_desc)

                        with stat_col2:
                            # Interpretation wording requested by user
                            base_msg = f"An R-Square value of **{r_squared:.3f}** means that **{x_label}** is responsible for approximately **{r_percent:.1f}%** of the observed variation in **{y_label}** across this corridor."
                            
                            # Dynamic slope explanation
                            slope_updown = "upward" if slope > 0 else "downward"
                            trend_highlow = "higher" if slope > 0 else "lower"
                            slope_text = f"Because the trendline slopes **{slope_updown}**, then higher **{x_label}** is generally associated with **{trend_highlow}** **{y_label}**."

                            if r_squared >= 0.8:
                                interp_body = f"{x_short} is a highly reliable predictor of {y_short}. Signal timing adjustments targeting {x_short} are very likely to produce measurable improvements in {y_short}."
                            elif r_squared >= 0.6:
                                interp_body = f"{x_short} shows a meaningful correlation with {y_short}. Engineers should prioritize {x_short} when optimizing signal timing plans to impact {y_short}."
                            elif r_squared >= 0.3:
                                interp_body = f"While {x_short} is a significant factor, other variables like intersection geometry, signal phasing, or pedestrian activity also play major roles."
                            else:
                                interp_body = f"{x_short} does not strongly predict {y_short} across this corridor. Consider investigating other variables or looking at intersection-specific issues."

                            st_func(f"{interp_head} {base_msg} {slope_text} {interp_body}")

                            # Dots interpretation
                            y_eval = "worse-than-expected" if ("Delay" in y_label or "Split Failures" in y_label) else "better-than-expected"
                            opposite_eval = "better-than-expected" if y_eval == "worse-than-expected" else "worse-than-expected"

                            st.markdown(f"""
                            **Reading the Dots (Relative to Trend):**
                            *   A dot **above** the trendline means the approach has higher **{y_short}** than predicted for its **{x_short}** ({y_eval}).
                            *   A dot **below** the trendline means the approach has lower **{y_short}** than predicted for its **{x_short}** ({opposite_eval}).
                            """)

                            # Ops units (+10% AOG)
                            if x_label == "Arrivals on Green (%)":
                                change_y = slope * 0.10
                                direction = "higher" if change_y > 0 else "lower"
                                abs_change = abs(change_y)

                                if "Delay" in y_label:
                                    val_str = f"{abs_change:.1f} seconds"
                                elif "Arrivals on Green" in y_label or "Split Failures" in y_label:
                                    val_str = f"{abs_change*100:.1f} percentage points"
                                else:
                                    val_str = f"{abs_change:.2f}"

                                st.success(f"**Practical Impact:** Every **+10%** increase in Arrivals on Green is associated with about **{val_str} {direction}** {y_short} on average.")
                                st.caption("_Note: This represents a statistical association across the corridor, not absolute proof of causation. Other factors like geometry, volumes, and spillback also affect outcomes._")

                    st.markdown("---")
                    with st.expander("Regression Dictionary", expanded=False):
                        st.markdown("""
                        *   **Independent Variable:** An independent variable is the factor that a researcher changes/manipulates to test its effect on the dependent variable.
                        *   **Dependent Variable:** A dependent variable depends on the independent variable for changes in response or outcome.
                        *   **Each Dot:** Represents one "approach" (a specific direction at a specific intersection, e.g., Fred Waring & Warner — Eastbound).
                        *   **The Trendline (Dashed Line):** Represents the "best-fit" linear relationship between your chosen variables. It shows the general corridor-wide trend.
                        *   **R² (Coefficient of Determination):** A statistical measure of how well the independent variable (X) explains the variation in the dependent variable (Y).
                        *   **Goal:** Use this to identify which intersections are performing better or worse than the corridor average and to predict how changes in one metric (like Volume) might impact another (like Delay).
                        """)

            else:
                st.warning("No data available for corridor-wide regression analysis.")

        with tab3:
            render_apples_tab(
                registry=INTERSECTION_REGISTRY,
                load_data_func=load_data,
                get_meta_value_func=get_meta_value,
                direction_map=DIRECTION_MAP,
                direction_colors=DIRECTION_COLORS
            )


if __name__ == "__main__":
    main()