import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

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
    }
]

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
    
    df = df_app.copy()
    # Ensure numeric volume; 'Vehicle Samples 1' is the column from ClearGuide
    df["Vehicle Samples 1"] = pd.to_numeric(df["Vehicle Samples 1"], errors='coerce').fillna(0)
    df["ADT"] = df["Vehicle Samples 1"] / days
    
    # Map approach names (e.g., 'N' -> 'Northbound')
    df["Approach"] = df["Approach"].astype(str).str.strip()
    df["Approach Full"] = df["Approach"].map(direction_map).fillna(df["Approach"])
    df["days"] = days
    
    return df[["Approach", "Approach Full", "ADT", "Vehicle Samples 1", "days"]]

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
            app_adt["DateRange"] = file_date_range
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

    # Load data for all intersections
    all_approach_adt = []
    all_movement_shares = []
    summary_results = []
    
    # Study period tracking
    date_range_str = "N/A"
    
    # Progress bar for loading multiple files
    progress_text = f"Loading ADT data for {selected_corridor}..."
    progress_bar = st.progress(0, text=progress_text)
    
    for i, entry in enumerate(corridor_entries):
        progress_bar.progress((i + 1) / len(corridor_entries), text=f"Loading {entry['label']}...")
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
            app_adt["DateRange"] = file_date_range
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
    
    # Sorting logic
    if sort_by == "ADT (High to Low)":
        # Sort by the Two-Way ADT (if multiple roadways, take the max one for sorting the intersection)
        sort_order = df_summary.groupby("Intersection")["Two-Way ADT"].max().sort_values(ascending=False).index.tolist()
    elif sort_by == "ADT (Low to High)":
        sort_order = df_summary.groupby("Intersection")["Two-Way ADT"].max().sort_values(ascending=True).index.tolist()
    else: # Registry Order
        sort_order = [e["label"] for e in corridor_entries if e["label"] in df_summary["Intersection"].values]
    
    # --- KPI Cards ---
    st.subheader("Corridor KPIs")
    k1, k2 = st.columns(2)
    
    # 1. MAX Intersection ADT
    max_adt_val = df_summary["Two-Way ADT"].max()
    max_row = df_summary[df_summary["Two-Way ADT"] == max_adt_val].iloc[0]
    max_intersection = max_row["Intersection"]
    max_roadway = max_row["Roadway"]
    
    k1.markdown(f"""
<div style="background: var(--secondary-background-color); padding: 22px 15px; border-radius: 14px; border: 2px solid #1f4582; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.05); min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 0.9rem; color: #1f4582; text-transform: uppercase; font-weight: 900; letter-spacing: 1px; margin-bottom: 10px;">MAX Intersection ADT</div>
    <div style="font-size: 2.4rem; font-weight: 900; color: var(--text-color); line-height: 1; margin-bottom: 10px;">{max_adt_val:,.0f} <span style="font-size: 1.1rem; font-weight: 600; opacity: 0.7;">vehicles/day</span></div>
    <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-color); line-height: 1.2;">{max_intersection}</div>
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
    
    # 1. Two-Way ADT by Intersection (Bar Chart)
    title1 = f"<b>{selected_corridor}</b><br><sup>Two-Way ADT by Intersection | {date_range_str}</sup>"
    fig1 = px.bar(
        df_summary,
        x="Intersection",
        y="Two-Way ADT",
        color="Roadway",
        barmode="group",
        title=title1,
        text="Two-Way ADT",
        category_orders={"Intersection": sort_order},
        color_discrete_sequence=px.colors.qualitative.Prism,
        custom_data=["Roadway", "Approaches", "DateRange"]
    )
    fig1.update_traces(
        texttemplate='%{text:,.0f}', 
        textposition='outside',
        textfont_size=20,
        hovertemplate="<b>Intersection:</b> %{x}<br><b>Roadway:</b> %{customdata[0]}<br><b>Included Approaches:</b> %{customdata[1]}<br><b>Two-Way ADT:</b> %{y:,.0f} vehicles/day<br><b>Study Period:</b> %{customdata[2]}<extra></extra>"
    )
    fig1.update_layout(
        title_font_size=34,
        xaxis_title_font_size=26,
        yaxis_title_font_size=26,
        xaxis_tickfont_size=18,
        yaxis_tickfont_size=18,
        xaxis_title="", 
        yaxis_title="Daily Vehicles",
        yaxis_range=[0, max_adt_val * 1.15],
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
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Directional ADT Comparison (Grouped Bar Chart)
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
        st.markdown("---")
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
