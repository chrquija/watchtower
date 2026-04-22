import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

DIRECTION_MAP = {
    "N": "Northbound",
    "S": "Southbound",
    "E": "Eastbound",
    "W": "Westbound",
    "NW": "Northwestbound",
    "SE": "Southeastbound",
    "NE": "Northeastbound",
    "SW": "Southwestbound"
}

# --- ADT REGISTRY ---
# Each entry contains:
# - label: Display name
# - url: Raw GitHub URL to the Excel file
# - corridors: List of corridors this intersection belongs to
# - roadway_pairings: Explicit pairings of approaches for two-way ADT calculation

ADT_REGISTRY = [
    {
        "label": "Highway 111 & Washington St",
        "lat": 33.715095, "lon": -116.29489,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/1_Hwy111_WashingtonSt_04012026_05132026.xlsx",
        "corridors": ["Highway 111 (Washington → Adams)", "Washington Street (Hwy 111 → Ave 48)"],
        "roadway_pairings": [
            {"roadway": "Highway 111", "approaches": ["SE", "NW"]},
            {"roadway": "Washington Street", "approaches": ["N", "S"]}
        ]
    },
    {
        "label": "Highway 111 & Simon Drive",
        "lat": 33.7125, "lon": -116.291855,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/2.1_HWY111_SimonDr_04012026_05132026.xlsx",
        "corridors": ["Highway 111 (Washington → Adams)"],
        "roadway_pairings": [
            {"roadway": "Highway 111", "approaches": ["SE", "NW"]},
            {"roadway": "Simon Drive", "approaches": ["NE", "SW"]}
        ]
    },
    {
        "label": "Highway 111 & La Quinta Center",
        "lat": 33.710335, "lon": -116.289635,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/3_HWY111_LaQuintaCenter_04012026_05132026.xlsx",
        "corridors": ["Highway 111 (Washington → Adams)"],
        "roadway_pairings": [
            {"roadway": "Highway 111", "approaches": ["SE", "NW"]},
            {"roadway": "La Quinta Center", "approaches": ["NE", "SW"]}
        ]
    },
    {
        "label": "Highway 111 & Adams St",
        "lat": 33.70831, "lon": -116.28619,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/4_HWY111_ADAMSST_04012026_05132026.xlsx",
        "corridors": ["Highway 111 (Washington → Adams)", "Adams Street (Hwy 111 → Ave 48)"],
        "roadway_pairings": [
            {"roadway": "Highway 111", "approaches": ["SE", "W"]},
            {"roadway": "Adams Street", "approaches": ["N", "S"]}
        ]
    },
    {
        "label": "Avenue 47 & Washington St",
        "lat": 33.70756, "lon": -116.294565,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/5.2_WashingtonSt_Ave47_04012026_05132026.xlsx",
        "corridors": ["Avenue 47 (Washington → Adams)", "Washington Street (Hwy 111 → Ave 48)"],
        "roadway_pairings": [
            {"roadway": "Avenue 47", "approaches": ["E", "W"]},
            {"roadway": "Washington Street", "approaches": ["N", "S"]}
        ]
    },
    {
        "label": "Washington Street & Point Happy Way",
        "lat": 33.71253, "lon": -116.29475,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/6_WashingtonSt_PointHappyWay_04012026_05132026.xlsx",
        "corridors": ["Washington Street (Hwy 111 → Ave 48)"],
        "roadway_pairings": [
            {"roadway": "Washington Street", "approaches": ["N", "S"]},
            {"roadway": "Point Happy Way", "approaches": ["E", "W"]}
        ]
    },
    {
        "label": "Washington Street & Avenue 48",
        "lat": 33.69993, "lon": -116.294875,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/7.1_WashingtonSt_Ave48_04012026_05132026.xlsx",
        "corridors": ["Washington Street (Hwy 111 → Ave 48)"],
        "roadway_pairings": [
            {"roadway": "Washington Street", "approaches": ["N", "S"]},
            {"roadway": "Avenue 48", "approaches": ["W"]}
        ]
    },
    {
        "label": "Adams Street & Avenue 48",
        "lat": 33.699985, "lon": -116.28613,
        "url": "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/8_Avenue48_AdamsST_04012026_05132026.xlsx",
        "corridors": ["Adams Street (Hwy 111 → Ave 48)"],
        "roadway_pairings": [
            {"roadway": "Adams Street", "approaches": ["N", "S"]},
            {"roadway": "Avenue 48", "approaches": ["E", "W"]}
        ]
    },
    {
        "label": "Adams St",
        "lat": 33.70756, "lon": -116.28619,
        "url": None, # Marker only for Avenue 47 corridor
        "corridors": ["Avenue 47 (Washington → Adams)"],
        "roadway_pairings": []
    }
]

# --- SEGMENT REGISTRY ---
# Defines the subsegments for each corridor and which approach from which intersection
# to use for each direction to calculate the midpoint ADT.
SEGMENT_REGISTRY = {
    "Highway 111 (Washington → Adams)": [
        {
            "subsegment": "Highway 111 & Washington St ↔ Highway 111 & Simon Drive",
            "directions": [
                {"from_int": "Highway 111 & Washington St", "to_int": "Highway 111 & Simon Drive", "approach": "SE"},
                {"from_int": "Highway 111 & Simon Drive", "to_int": "Highway 111 & Washington St", "approach": "NW"}
            ],
            "order": 1
        },
        {
            "subsegment": "Highway 111 & Simon Drive ↔ Highway 111 & La Quinta Center",
            "directions": [
                {"from_int": "Highway 111 & Simon Drive", "to_int": "Highway 111 & La Quinta Center", "approach": "SE"},
                {"from_int": "Highway 111 & La Quinta Center", "to_int": "Highway 111 & Simon Drive", "approach": "NW"}
            ],
            "order": 2
        },
        {
            "subsegment": "Highway 111 & La Quinta Center ↔ Highway 111 & Adams St",
            "directions": [
                {"from_int": "Highway 111 & La Quinta Center", "to_int": "Highway 111 & Adams St", "approach": "SE"},
                {"from_int": "Highway 111 & Adams St", "to_int": "Highway 111 & La Quinta Center", "approach": "W"}
            ],
            "order": 3
        }
    ],
    "Washington Street (Hwy 111 → Ave 48)": [
        {
            "subsegment": "Highway 111 & Washington St ↔ Washington Street & Point Happy Way",
            "directions": [
                {"from_int": "Highway 111 & Washington St", "to_int": "Washington Street & Point Happy Way", "approach": "S"},
                {"from_int": "Washington Street & Point Happy Way", "to_int": "Highway 111 & Washington St", "approach": "N"}
            ],
            "order": 1
        },
        {
            "subsegment": "Washington Street & Point Happy Way ↔ Avenue 47 & Washington St",
            "directions": [
                {"from_int": "Washington Street & Point Happy Way", "to_int": "Avenue 47 & Washington St", "approach": "S"},
                {"from_int": "Avenue 47 & Washington St", "to_int": "Washington Street & Point Happy Way", "approach": "N"}
            ],
            "order": 2
        },
        {
            "subsegment": "Avenue 47 & Washington St ↔ Washington Street & Avenue 48",
            "directions": [
                {"from_int": "Avenue 47 & Washington St", "to_int": "Washington Street & Avenue 48", "approach": "S"},
                {"from_int": "Washington Street & Avenue 48", "to_int": "Avenue 47 & Washington St", "approach": "N"}
            ],
            "order": 3
        }
    ],
    "Adams Street (Hwy 111 → Ave 48)": [
        {
            "subsegment": "Highway 111 & Adams St ↔ Adams Street & Avenue 48",
            "directions": [
                {"from_int": "Highway 111 & Adams St", "to_int": "Adams Street & Avenue 48", "approach": "S"},
                {"from_int": "Adams Street & Avenue 48", "to_int": "Highway 111 & Adams St", "approach": "N"}
            ],
            "order": 1
        }
    ],
    "Avenue 47 (Washington → Adams)": [
        {
            "subsegment": "Avenue 47 & Washington St ↔ Adams St",
            "directions": [
                {"from_int": "Avenue 47 & Washington St", "to_int": "Adams St", "approach": "E"},
                {"from_int": "Adams St", "to_int": "Avenue 47 & Washington St", "approach": "W", "data_source": "Avenue 47 & Washington St"}
            ],
            "order": 1
        }
    ]
}

# --- ADT Transformation Helpers ---

def compute_day_count(df_meta, get_meta_value_func):
    """
    Computes number of days between Metadata 'Start Date' and 'End Date' (inclusive).
    """
    start_str = get_meta_value_func(df_meta, "Start Date")
    end_str = get_meta_value_func(df_meta, "End Date")
    
    try:
        # pd.to_datetime is flexible with most standard formats
        start_date = pd.to_datetime(start_str)
        end_date = pd.to_datetime(end_str)
        delta = (end_date - start_date).days + 1
        return max(delta, 1)
    except Exception:
        return 1

def compute_approach_adt(df_app, df_meta, direction_map, get_meta_value_func):
    """
    Calculates ADT for each approach.
    ADT = Vehicle Samples 1 / number_of_days
    """
    days = compute_day_count(df_meta, get_meta_value_func)
    
    # Get date range for labeling
    start = get_meta_value_func(df_meta, "Start Date")
    end = get_meta_value_func(df_meta, "End Date")
    date_range = f"{start} to {end}"
    
    df = df_app.copy()
    # Ensure numeric volume; 'Vehicle Samples 1' is the column from ClearGuide
    df["Vehicle Samples 1"] = pd.to_numeric(df["Vehicle Samples 1"], errors='coerce').fillna(0)
    df["ADT"] = df["Vehicle Samples 1"] / days
    
    # Map approach names (e.g., 'N' -> 'Northbound')
    df["Approach"] = df["Approach"].astype(str).str.strip()
    df["Approach Full"] = df["Approach"].map(direction_map).fillna(df["Approach"])
    df["days"] = days
    df["DateRange"] = date_range
    
    return df[["Approach", "Approach Full", "ADT", "Vehicle Samples 1", "days", "DateRange"]]

def compute_intersection_adt(df_int, df_meta, get_meta_value_func):
    """
    Calculates total intersection ADT.
    ADT = Intersection Vehicle Samples 1 / number_of_days
    """
    days = compute_day_count(df_meta, get_meta_value_func)
    
    df = df_int.copy()
    # 'Vehicle Samples 1' on the 'Intersection' sheet is the total for the intersection
    df["Vehicle Samples 1"] = pd.to_numeric(df["Vehicle Samples 1"], errors='coerce').fillna(0)
    total_volume = df["Vehicle Samples 1"].sum()
    total_adt = total_volume / days
    
    return total_adt, total_volume

def compute_movement_share(df_mov, direction_map=None):
    """
    Calculates the share (percentage) of each movement relative to the INTERSECTION total.
    (Updated to aggregate at intersection level first)
    """
    df = df_mov.copy()
    df["Vehicle Samples 1"] = pd.to_numeric(df["Vehicle Samples 1"], errors='coerce').fillna(0)
    
    # Aggregate by movement across all approaches
    # ClearGuide movements are usually 'Left', 'Thru', 'Right', 'U-Turn'
    mov_agg = df.groupby("Movement")["Vehicle Samples 1"].sum().reset_index()
    total_int_volume = mov_agg["Vehicle Samples 1"].sum()
    
    mov_agg["Share"] = (mov_agg["Vehicle Samples 1"] / total_int_volume).fillna(0)
    mov_agg["Intersection Total Volume"] = total_int_volume
    
    return mov_agg

def compute_two_way_adt(approach_adt_df, roadway_pairings):
    """
    Aggregates approach-level ADT into roadway-level Two-Way ADT based on registry config.
    """
    results = []
    for pairing in roadway_pairings:
        roadway = pairing["roadway"]
        approaches = pairing["approaches"]
        
        # Filter to only the specified approaches in the pairing
        relevant = approach_adt_df[approach_adt_df["Approach"].isin(approaches)]
        
        # If no relevant approach data is found for this pairing, skip it
        # This prevents false zeros in the charts caused by missing approach data
        if relevant.empty:
            continue
            
        two_way_adt = relevant["ADT"].sum()
        
        results.append({
            "Roadway": roadway,
            "Approaches": ", ".join(approaches),
            "Two-Way ADT": two_way_adt
        })
    
    return pd.DataFrame(results)

# --- NEW SEGMENT ADT HELPERS ---

def get_segment_adt_dataframe(selected_corridor, segment_registry, adt_registry, load_data_func, get_meta_value_func, direction_map, sort_by="Registry Order"):
    """
    Computes midpoint segment ADT for the selected corridor based on the SEGMENT_REGISTRY.
    Returns a dataframe formatted for the segment-midpoint chart.
    """
    if selected_corridor not in segment_registry or not segment_registry[selected_corridor]:
        return pd.DataFrame() # Return empty if no segment data defined

    segments = segment_registry[selected_corridor]
    all_segment_data = []

    # Cache for loaded data to avoid reloading same file multiple times
    intersection_cache = {}

    for seg_config in segments:
        subsegment_name = seg_config["subsegment"]
        seg_order = seg_config["order"]
        two_way_adt_by_dr = {} # DateRange -> Two-Way ADT
        
        # We need to process each direction to get directional ADT
        direction_rows = []
        
        for dir_config in seg_config["directions"]:
            from_int_label = dir_config["from_int"]
            to_int_label = dir_config["to_int"]
            approach = dir_config["approach"]
            
            # Use data_source if provided (for cases where we only have one intersection's data)
            # but still want to label the direction correctly.
            data_int_label = dir_config.get("data_source", from_int_label)
            
            # Find the intersection in ADT_REGISTRY
            int_entry = next((item for item in adt_registry if item["label"] == data_int_label), None)
            if not int_entry:
                continue
                
            # Load intersection data (using cache)
            if data_int_label not in intersection_cache:
                dfs = load_data_func(int_entry["url"])
                if not dfs:
                    continue
                intersection_cache[data_int_label] = dfs
            
            dfs = intersection_cache[data_int_label]
            df_meta, _, df_app, _ = dfs
            
            # Compute approach ADT
            app_adt_df = compute_approach_adt(df_app, df_meta, direction_map, get_meta_value_func)
            
            # Filter for the specific approach
            target_app_adt = app_adt_df[app_adt_df['Approach'] == approach]
            
            for _, row in target_app_adt.iterrows():
                dr = row['DateRange']
                directional_adt = row['ADT']
                
                direction_rows.append({
                    "Corridor": selected_corridor,
                    "Subsegment": subsegment_name,
                    "Direction Label": f"{from_int_label} → {to_int_label}",
                    "From Intersection": from_int_label,
                    "To Intersection": to_int_label,
                    "From Approach": approach,
                    "Total Period Volume": row['Vehicle Samples 1'],
                    "Days": row['days'],
                    "Directional ADT": directional_adt,
                    "DateRange": dr,
                    "SegmentOrder": seg_order
                })
                
                two_way_adt_by_dr[dr] = two_way_adt_by_dr.get(dr, 0) + directional_adt
        
        # Add the Two-Way Segment ADT to each row
        for row in direction_rows:
            row["Two-Way Segment ADT"] = two_way_adt_by_dr.get(row["DateRange"], 0)
            all_segment_data.append(row)

    if not all_segment_data:
        return pd.DataFrame()

    df_final = pd.DataFrame(all_segment_data)

    # Sorting Logic
    if sort_by == "Registry Order":
        df_final = df_final.sort_values(by=["SegmentOrder", "Direction Label"])
    elif sort_by == "ADT (High to Low)":
        # Sort by Two-Way Segment ADT descending, then by order to keep subsegments together
        df_final = df_final.sort_values(by=["Two-Way Segment ADT", "SegmentOrder"], ascending=[False, True])
    elif sort_by == "ADT (Low to High)":
        df_final = df_final.sort_values(by=["Two-Way Segment ADT", "SegmentOrder"], ascending=[True, True])

    return df_final

# --- Future UI Preparation ---

def get_adt_export_data(selected_corridor, adt_registry, load_data_func, get_meta_value_func, direction_map):
    """
    Gather and prepare all ADT data for the selected corridor for Excel export.
    """
    corridor_entries = [entry for entry in adt_registry if selected_corridor in entry["corridors"]]
    
    all_approach_adt = []
    all_movement_shares = []
    summary_results = []
    
    for entry in corridor_entries:
        if not entry.get("url"):
            continue
        data = load_data_func(entry["url"])
        if data:
            df_meta, df_int, df_app, df_mov = data
            
            # Get date range for this specific file
            start = get_meta_value_func(df_meta, "Start Date")
            end = get_meta_value_func(df_meta, "End Date")
            file_date_range = f"{start} to {end}"
            
            # 1. Approach ADT
            app_adt = compute_approach_adt(df_app, df_meta, direction_map, get_meta_value_func)
            app_adt["Intersection"] = entry["label"]
            all_approach_adt.append(app_adt)
            
            # 2. Movement Share
            mov_share = compute_movement_share(df_mov)
            mov_share["Intersection"] = entry["label"]
            mov_share["DateRange"] = file_date_range
            all_movement_shares.append(mov_share)
            
            # 3. Two-Way ADT per Roadway
            two_way_df = compute_two_way_adt(app_adt, entry["roadway_pairings"])
            for _, row in two_way_df.iterrows():
                summary_results.append({
                    "Intersection": entry["label"],
                    "Roadway": row["Roadway"],
                    "Two-Way ADT": row["Two-Way ADT"]
                })
    
    if not summary_results:
        return None
        
    return {
        "ADT Summary": pd.DataFrame(summary_results),
        "Approach ADT": pd.concat(all_approach_adt, ignore_index=True),
        "Movement Share": pd.concat(all_movement_shares, ignore_index=True)
    }

def render_adt_tab(selected_corridor, adt_registry, load_data_func, get_meta_value_func, direction_map, direction_colors, sort_by="Registry Order", show_raw=False):
    """
    Renders the ADT Analysis tab content.
    """
    corridor_entries = [entry for entry in adt_registry if selected_corridor in entry["corridors"]]
    
    if not corridor_entries:
        st.warning(f"No intersections found for corridor: {selected_corridor}")
        return

    # --- PHASE 2: Fetch Segment ADT Data ---
    df_segments = get_segment_adt_dataframe(
        selected_corridor, 
        SEGMENT_REGISTRY, 
        adt_registry, 
        load_data_func, 
        get_meta_value_func, 
        direction_map, 
        sort_by
    )

    # Load data for all intersections (needed for other charts/KPIs)
    all_approach_adt = []
    all_movement_shares = []
    summary_results = []
    
    # Study period tracking
    date_range_str = "N/A"
    
    # Progress bar for loading multiple files
    progress_text = f"Loading ADT data for {selected_corridor}..."
    progress_bar = st.progress(0, text=progress_text)
    
    valid_entries = [e for e in corridor_entries if e.get("url")]
    for i, entry in enumerate(valid_entries):
        progress_bar.progress((i + 1) / len(valid_entries), text=f"Loading {entry['label']}...")
        data = load_data_func(entry["url"])
        if data:
            df_meta, df_int, df_app, df_mov = data
            
            # Get date range for this specific file
            start = get_meta_value_func(df_meta, "Start Date")
            end = get_meta_value_func(df_meta, "End Date")
            file_date_range = f"{start} to {end}"
            
            # Global range tracking
            if date_range_str == "N/A":
                date_range_str = file_date_range
            elif date_range_str != file_date_range:
                date_range_str = "Mixed"
            
            # 1. Approach ADT
            app_adt = compute_approach_adt(df_app, df_meta, direction_map, get_meta_value_func)
            app_adt["Intersection"] = entry["label"]
            all_approach_adt.append(app_adt)
            
            # 2. Movement Share
            mov_share = compute_movement_share(df_mov)
            mov_share["Intersection"] = entry["label"]
            mov_share["DateRange"] = file_date_range
            all_movement_shares.append(mov_share)
            
            # 3. Two-Way ADT per Roadway
            two_way_df = compute_two_way_adt(app_adt, entry["roadway_pairings"])
            for _, row in two_way_df.iterrows():
                summary_results.append({
                    "Intersection": entry["label"],
                    "Roadway": row["Roadway"],
                    "Approaches": row["Approaches"],
                    "Two-Way ADT": row["Two-Way ADT"],
                    "DateRange": file_date_range,
                    "Order": i
                })
        else:
            st.error(f"Failed to load data for {entry['label']}")

    progress_bar.empty()
    
    if not summary_results:
        st.error("No data could be loaded for the selected corridor.")
        return

    df_summary = pd.DataFrame(summary_results)
    df_all_app = pd.concat(all_approach_adt, ignore_index=True)
    df_all_mov = pd.concat(all_movement_shares, ignore_index=True)
    
    # Sorting logic for other charts (Intersection based)
    if sort_by == "ADT (High to Low)":
        sort_order = df_summary.groupby("Intersection")["Two-Way ADT"].max().sort_values(ascending=False).index.tolist()
    elif sort_by == "ADT (Low to High)":
        sort_order = df_summary.groupby("Intersection")["Two-Way ADT"].max().sort_values(ascending=True).index.tolist()
    else: # Registry Order
        sort_order = [e["label"] for e in corridor_entries if e["label"] in df_summary["Intersection"].values]
    
    # --- KPI Cards ---
    st.subheader("Corridor KPIs")
    k1, k2 = st.columns(2)
    
    # 1. Segment Average Daily Traffic (ADT)
    if not df_segments.empty:
        # Calculate the average of all unique subsegments' Two-Way ADT
        segment_adt_val = df_segments.groupby("Subsegment")["Two-Way Segment ADT"].first().mean()
    else:
        # Fallback to max intersection ADT if no segment data is available
        segment_adt_val = df_summary["Two-Way ADT"].max()
    
    k1.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 22px 15px; border-radius: 14px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.9rem; color: #1f4582; text-transform: uppercase; font-weight: 900; letter-spacing: 1px; margin-bottom: 10px;">Segment Average Daily Traffic (ADT)</div>
    <div style="font-size: 2.4rem; font-weight: 900; color: var(--text-color); line-height: 1; margin-bottom: 10px;">{segment_adt_val:,.0f} <span style="font-size: 1.1rem; font-weight: 600; opacity: 0.7;">vehicles/day</span></div>
    <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-color); line-height: 1.2;">{selected_corridor}</div>
    <div style="font-size: 0.95rem; margin-top: 4px; height: 1.2rem;"></div> <!-- Spacer to align with second card -->
</div>
""", unsafe_allow_html=True)
    
    # 2. Highest Approach Volume (Total Period Volume)
    max_app_idx = df_all_app["Vehicle Samples 1"].idxmax()
    max_app_row = df_all_app.loc[max_app_idx]
    max_app_vol = max_app_row["Vehicle Samples 1"]
    max_app_name = max_app_row["Approach Full"]
    max_app_int = max_app_row["Intersection"]
    
    k2.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 22px 15px; border-radius: 14px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.9rem; color: #1f4582; text-transform: uppercase; font-weight: 900; letter-spacing: 1px; margin-bottom: 10px;">Highest Approach Volume</div>
    <div style="font-size: 2.4rem; font-weight: 900; color: var(--text-color); line-height: 1; margin-bottom: 10px;">{max_app_vol:,.0f} <span style="font-size: 1.1rem; font-weight: 600; opacity: 0.7;">vehicles</span></div>
    <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-color); line-height: 1.2;">{max_app_int}</div>
    <div style="font-size: 0.95rem; font-style: italic; color: var(--text-color); opacity: 0.7; margin-top: 4px;">{max_app_name}</div>
</div>
""", unsafe_allow_html=True)
    
    # --- Charts ---
    st.divider()
    
    # 1. Segment Midpoint ADT (NEW Replacement Chart)
    if df_segments.empty:
        st.info(f"Insufficient data for full segment midpoint ADT calculation on **{selected_corridor}**.")
    else:
        # --- UI Improvement 1: Subsegment Filter ---
        unique_subsegments = df_segments.sort_values(by="SegmentOrder")["Subsegment"].unique().tolist()
        
        # Determine filter default and options
        filter_options = ["All subsegments"] + unique_subsegments
        
        # Add a container for the filter to keep it near the chart
        filter_col1, filter_col2 = st.columns([1, 3])
        with filter_col1:
            selected_subseg = st.selectbox(
                "Filter by Subsegment:",
                options=filter_options,
                index=0,
                key=f"subseg_filter_{selected_corridor}"
            )
        
        # Filter the dataframe for the chart
        if selected_subseg != "All subsegments":
            plot_df = df_segments[df_segments["Subsegment"] == selected_subseg].copy()
            # If a single subsegment is selected, we might want to adjust the order/display
            plot_subsegments = [selected_subseg]
        else:
            plot_df = df_segments.copy()
            # Determine unique subsegments in order for the X-axis
            plot_subsegments = unique_subsegments
            if sort_by == "ADT (High to Low)":
                plot_subsegments = plot_df.sort_values(by="Two-Way Segment ADT", ascending=False)["Subsegment"].unique().tolist()
            elif sort_by == "ADT (Low to High)":
                plot_subsegments = plot_df.sort_values(by="Two-Way Segment ADT", ascending=True)["Subsegment"].unique().tolist()

        # --- UI Improvement 4: Rename Chart Title ---
        title1 = f"<b>{selected_corridor}</b><br><sup>Midpoint ADT by Subsegment | {date_range_str}</sup>"
        
        # --- UI Improvement 2: Improve Layout for Crowded Corridors ---
        # Dynamically adjust height and margins based on number of subsegments
        num_subsegments = len(plot_subsegments)
        chart_height = 700 + (max(0, num_subsegments - 2) * 50)
        top_margin = 160 if num_subsegments > 2 else 140
        
        fig1 = px.bar(
            plot_df,
            x="Subsegment",
            y="Directional ADT",
            color="Direction Label",
            barmode="group",
            title=title1,
            text="Directional ADT",
            category_orders={"Subsegment": plot_subsegments},
            color_discrete_sequence=px.colors.qualitative.Prism,
            height=chart_height,
            custom_data=[
                "Direction Label", "From Intersection", "To Intersection", 
                "From Approach", "Total Period Volume", "Days", 
                "Directional ADT", "Two-Way Segment ADT", "DateRange"
            ]
        )

        fig1.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            textfont_size=20,
            hovertemplate=(
                "<b>Subsegment:</b> %{x}<br>"
                "<b>Direction:</b> %{customdata[0]}<br>"
                "<b>From Intersection:</b> %{customdata[1]}<br>"
                "<b>To Intersection:</b> %{customdata[2]}<br>"
                "<b>From Approach:</b> %{customdata[3]}<br>"
                "<b>Total Period Volume:</b> %{customdata[4]:,.0f} vehicles<br>"
                "<b>Days:</b> %{customdata[5]}<br>"
                "<b>Directional ADT:</b> %{customdata[6]:,.0f} vehicles/day<br>"
                "<b>Two-Way Segment ADT:</b> %{customdata[7]:,.0f} vehicles/day<br>"
                "<b>Study Period:</b> %{customdata[8]}<extra></extra>"
            )
        )

        # Add Two-Way Total Labels as annotations
        # --- UI Improvement 3: Fix Total Label Wording ---
        annotations = []
        for subseg in plot_subsegments:
            subseg_data = plot_df[plot_df["Subsegment"] == subseg]
            if not subseg_data.empty:
                max_y = subseg_data["Directional ADT"].max()
                two_way_total = subseg_data["Two-Way Segment ADT"].iloc[0]
                
                annotations.append(dict(
                    x=subseg,
                    y=max_y,
                    text=f"<b>Two-Way ADT: {two_way_total:,.0f}</b><br>vehicles/day",
                    showarrow=False,
                    yshift=65, # Slightly more shift to avoid overlapping bar labels
                    font=dict(size=18, color="#1f4582"),
                    bgcolor="rgba(255, 255, 255, 0.85)",
                    bordercolor="#1f4582",
                    borderwidth=1,
                    borderpad=5
                ))

        fig1.update_layout(
            title_font_size=34,
            xaxis_title_font_size=26,
            yaxis_title_font_size=26,
            xaxis_tickfont_size=18 if num_subsegments <= 3 else 16,
            yaxis_tickfont_size=18,
            xaxis_title="", 
            yaxis_title="Daily Vehicles (ADT)",
            yaxis_range=[0, plot_df["Directional ADT"].max() * 1.5], # Extra room for annotations
            margin=dict(t=top_margin, b=130),
            legend=dict(
                orientation="h", 
                yanchor="top", 
                y=-0.2, 
                xanchor="center", 
                x=0.5,
                font=dict(size=16),
                itemsizing='constant'
            ),
            annotations=annotations
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Directional ADT Comparison (Grouped Bar Chart)
    st.divider()
    title2 = f"<b>{selected_corridor}</b><br><sup>Directional ADT Comparison | {date_range_str}</sup>"
    # Filter to main 4 directions + diagonals
    valid_dirs = ["N", "S", "E", "W", "NB", "SB", "EB", "WB", "NE", "NW", "SE", "SW"]
    df_dir = df_all_app[df_all_app["Approach"].isin(valid_dirs)]
    fig2 = px.bar(
        df_dir,
        x="Intersection",
        y="ADT",
        color="Approach Full",
        barmode="group",
        title=title2,
        text="ADT",
        category_orders={"Intersection": sort_order},
        color_discrete_map=direction_colors,
        custom_data=["Approach Full", "Vehicle Samples 1", "days", "DateRange"]
    )
    fig2.update_traces(
        texttemplate='%{text:,.0f}', 
        textposition='outside',
        textfont_size=20,
        hovertemplate="<b>Intersection:</b> %{x}<br><b>Approach:</b> %{customdata[0]}<br><b>ADT:</b> %{y:,.0f} vehicles/day<br><b>Total Period Volume:</b> %{customdata[1]:,.0f} vehicles<br><b>Days in Study Period:</b> %{customdata[2]}<br><b>Study Period:</b> %{customdata[3]}<extra></extra>"
    )
    fig2.update_layout(
        title_font_size=34,
        xaxis_title_font_size=26,
        yaxis_title_font_size=26,
        xaxis_tickfont_size=18,
        yaxis_tickfont_size=18,
        xaxis_title="", 
        yaxis_title="Daily Vehicles",
        yaxis_range=[0, df_dir["ADT"].max() * 1.15],
        # Added margin and moved legend to bottom to prevent overlap with title
        margin=dict(t=150, b=120),
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
    st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Turning Movement Share (Stacked Bar Chart)
    st.divider()
    title3 = f"<b>{selected_corridor}</b><br><sup>Turning Movement Share | {date_range_str}</sup>"
    
    # Label logic: only show if share >= 8%
    df_all_mov["Label"] = df_all_mov["Share"].apply(lambda x: f"{x:.1%}" if x >= 0.08 else "")
    
    fig3 = px.bar(
        df_all_mov,
        x="Intersection",
        y="Share",
        color="Movement",
        title=title3,
        text="Label",
        category_orders={"Intersection": sort_order},
        labels={"Share": "Movement Share"},
        color_discrete_sequence=px.colors.qualitative.Safe,
        custom_data=["Movement", "Vehicle Samples 1", "Intersection Total Volume", "DateRange"]
    )
    fig3.update_traces(
        textposition='inside',
        textfont_size=24,
        hovertemplate="<b>Intersection:</b> %{x}<br><b>Movement:</b> %{customdata[0]}<br><b>Movement Volume:</b> %{customdata[1]:,.0f} vehicles<br><b>Intersection Total Volume:</b> %{customdata[2]:,.0f} vehicles<br><b>Movement Share:</b> %{y:.1%}<br><b>Study Period:</b> %{customdata[3]}<extra></extra>"
    )
    fig3.update_layout(
        title_font_size=34,
        xaxis_title_font_size=26,
        yaxis_title_font_size=26,
        xaxis_tickfont_size=18,
        yaxis_tickfont_size=18,
        xaxis_title="", 
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1], # Cap at 100%
        # Added margin and moved legend to bottom to prevent overlap with title
        margin=dict(t=150, b=120),
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
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Movement share is calculated from total intersection volume, so each bar sums to 100%.")
    
    # --- Summary Tables ---
    if show_raw:
        st.divider()
        st.subheader("Two-Way ADT: Raw Data")
        st.dataframe(
            df_summary[["Intersection", "Roadway", "Approaches", "Two-Way ADT", "DateRange"]]
            .sort_values(["Intersection", "Roadway"])
            .style.format({"Two-Way ADT": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True
        )
        
        st.subheader("Two-Way ADT: Roadway Summary")
        roadway_summary = df_summary.groupby("Roadway")["Two-Way ADT"].agg(
            Average_ADT="mean",
            Max_ADT="max",
            Min_ADT="min",
            Intersections="count"
        ).reset_index()
        
        roadway_summary.columns = ["Roadway", "Average ADT", "Max ADT", "Min ADT", "# Intersections"]
        
        st.dataframe(
            roadway_summary.style.format({
                "Average ADT": "{:,.0f}",
                "Max ADT": "{:,.0f}",
                "Min ADT": "{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
