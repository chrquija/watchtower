import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def _apply_comparison_layout(fig, y_axis_label, tickformat=None):
    """
    Applies a standard, clean layout for comparison charts in the apples-to-apples tab.
    Ensures that titles and legends have enough breathing room even at 100% zoom.
    """
    fig.update_layout(
        font=dict(family="Arial, sans-serif"),
        # Increase top margin significantly to prevent crowding
        margin=dict(t=150, b=50, l=50, r=30),
        # Position title at the top of the container area
        title=dict(
            y=0.96,
            x=0.02,
            xanchor='left',
            yanchor='top',
            font=dict(size=18)
        ),
        # Anchor legend just above the plot area, but below the title
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            borderwidth=1,
            bgcolor="rgba(255, 255, 255, 0.4)"
        ),
        xaxis=dict(title=dict(text="<b>Approach</b>")),
        yaxis=dict(
            title=dict(text=f"<b>{y_axis_label}</b>"),
            tickformat=tickformat
        ),
        height=550
    )

def render_apples_tab(registry, load_data_func, get_meta_value_func, direction_map):
    """
    Renders a tab for comparing two different time periods (datasets) 
    for the same intersection (Apples-to-Apples Comparison).
    """
    # 1. Selection logic
    # Find intersections that have multiple datasets for comparison
    comparable_intersections = [i for i in registry if len(i["datasets"]) > 1]
    
    if not comparable_intersections:
        st.info("No intersections with multiple datasets found for comparison in the current registry.")
        return

    # 2. Create container for results (this will appear first in the UI)
    results_container = st.container()

    # 3. Selection widgets at the bottom
    st.markdown("---")
    st.write("### Comparison Selection")
    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
    
    with col_sel1:
        selected_label = st.selectbox(
            "Select Intersection",
            options=[i["label"] for i in comparable_intersections],
            key="apples_intersection_selector"
        )
        selected_intersection = next(i for i in comparable_intersections if i["label"] == selected_label)
    
    dataset_options = [d["date_label"] for d in selected_intersection["datasets"]]
    with col_sel2:
        p1_label = st.selectbox("Baseline Period (P1)", options=dataset_options, index=0)
    with col_sel3:
        p2_label = st.selectbox("Comparison Period (P2)", options=dataset_options, index=min(1, len(dataset_options)-1))

    if p1_label == p2_label:
        st.warning("Please select two different time periods to generate a comparison.")
        return

    # 4. Fill results container
    with results_container:
        # Data Loading
        d1 = next(d for d in selected_intersection["datasets"] if d["date_label"] == p1_label)
        d2 = next(d for d in selected_intersection["datasets"] if d["date_label"] == p2_label)

        with st.spinner(f"Loading data for {p1_label} and {p2_label}..."):
            data1 = load_data_func(d1["url"])
            data2 = load_data_func(d2["url"])

        if data1 is None or data2 is None:
            st.error("Could not load data for one or both time periods. Please check the data source.")
            return

        df_meta1, df_int1, df_app1, _ = data1
        df_meta2, df_int2, df_app2, _ = data2

        # Extract date ranges for display
        dr1 = f"{get_meta_value_func(df_meta1, 'Start Date')} to {get_meta_value_func(df_meta1, 'End Date')}"
        dr2 = f"{get_meta_value_func(df_meta2, 'Start Date')} to {get_meta_value_func(df_meta2, 'End Date')}"

        st.write("### High-Level KPI Comparison")
        
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        def get_delta_str(v1, v2, is_pct=False):
            if pd.isna(v1) or pd.isna(v2): return None
            diff = v2 - v1
            if is_pct:
                # If values are on 0-1 scale, diff * 100 is percentage points
                if v1 < 1 and v2 < 1:
                    return f"{diff*100:+.1f}% pts"
                return f"{diff:+.1f}%"
            return f"{diff:+.1f}" if abs(diff) < 1000 else f"{int(diff):+,}"

        def format_val(v, is_pct=False, is_int=False):
            if pd.isna(v): return "N/A"
            if is_pct:
                if v >= 1: return f"{v:.1f}%"
                return f"{v:.1%}"
            if is_int: return f"{int(v):,}"
            return f"{v:.1f}"

        # Metric mapping
        metrics = [
            ("Delay Range 1", "Average Delay (s)", kpi_col1, False, False, "inverse"),
            ("Arrivals On Green Range 1", "Arrivals On Green", kpi_col2, True, False, "normal"),
            ("Split Failures Range 1", "Split Failures", kpi_col3, True, False, "inverse"),
            ("Vehicle Samples 1", "Total Vehicles", kpi_col4, False, True, "off")
        ]

        for col_name, label, column, is_pct, is_int, d_color in metrics:
            v1 = df_int1[col_name].iloc[0]
            v2 = df_int2[col_name].iloc[0]
            
            with column:
                st.metric(
                    f"{label} ({p2_label})", 
                    format_val(v2, is_pct, is_int), 
                    delta=get_delta_str(v1, v2, is_pct),
                    delta_color=d_color
                )
                st.caption(f"{p1_label}: {format_val(v1, is_pct, is_int)}")

        # Comparative Visualizations
        st.markdown("---")
        st.write("### Performance by Approach Comparison")

        # Helper to prep and concat data
        def prep_df(df, label):
            df_new = df.copy()
            df_new["Approach"] = df_new["Approach"].astype(str).str.strip()
            df_new["Approach Full"] = df_new["Approach"].map(direction_map).fillna(df_new["Approach"])
            df_new["Period"] = label
            return df_new

        df_comp_app = pd.concat([prep_df(df_app1, p1_label), prep_df(df_app2, p2_label)], ignore_index=True)

        # Normalize pct columns if needed
        for col in ["Arrivals On Green Range 1", "Split Failures Range 1"]:
            if df_comp_app[col].max() > 1:
                df_comp_app[col] = df_comp_app[col] / 100.0

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            fig_delay = px.bar(
                df_comp_app,
                x="Approach Full",
                y="Delay Range 1",
                color="Period",
                barmode="group",
                title=f"<b>{selected_label}</b><br><sup>Comparison: Average Delay (s) | {p1_label} vs {p2_label}</sup>",
                labels={"Delay Range 1": "Average Delay (s)", "Approach Full": "Approach"},
                color_discrete_map={p1_label: "#94a3b8", p2_label: "#1f4582"},
                text_auto='.1f'
            )
            _apply_comparison_layout(fig_delay, "Control Delay (seconds)")
            fig_delay.update_traces(
                textfont_size=12,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>Approach:</b> %{x}<br><b>%{fullData.name}:</b> %{y:.1f} seconds<extra></extra>"
            )
            st.plotly_chart(fig_delay, use_container_width=True)

        with chart_col2:
            fig_aog = px.bar(
                df_comp_app,
                x="Approach Full",
                y="Arrivals On Green Range 1",
                color="Period",
                barmode="group",
                title=f"<b>{selected_label}</b><br><sup>Comparison: Arrivals On Green | {p1_label} vs {p2_label}</sup>",
                labels={"Arrivals On Green Range 1": "Arrivals On Green (%)", "Approach Full": "Approach"},
                color_discrete_map={p1_label: "#94a3b8", p2_label: "#1f4582"},
                text_auto='.1%'
            )
            _apply_comparison_layout(fig_aog, "Arrivals On Green (%)", tickformat=".0%")
            fig_aog.update_traces(
                textfont_size=12,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>Approach:</b> %{x}<br><b>%{fullData.name}:</b> %{y:.1%}<extra></extra>"
            )
            st.plotly_chart(fig_aog, use_container_width=True)

        chart_col3, chart_col4 = st.columns(2)
        with chart_col3:
            fig_sf = px.bar(
                df_comp_app,
                x="Approach Full",
                y="Split Failures Range 1",
                color="Period",
                barmode="group",
                title=f"<b>{selected_label}</b><br><sup>Comparison: Split Failures | {p1_label} vs {p2_label}</sup>",
                labels={"Split Failures Range 1": "Split Failures (%)", "Approach Full": "Approach"},
                color_discrete_map={p1_label: "#94a3b8", p2_label: "#1f4582"},
                text_auto='.1%'
            )
            _apply_comparison_layout(fig_sf, "Split Failures (%)", tickformat=".0%")
            fig_sf.update_traces(
                textfont_size=12,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>Approach:</b> %{x}<br><b>%{fullData.name}:</b> %{y:.1%}<extra></extra>"
            )
            st.plotly_chart(fig_sf, use_container_width=True)

        with chart_col4:
            fig_vol = px.bar(
                df_comp_app,
                x="Approach Full",
                y="Vehicle Samples 1",
                color="Period",
                barmode="group",
                title=f"<b>{selected_label}</b><br><sup>Comparison: Total Volume | {p1_label} vs {p2_label}</sup>",
                labels={"Vehicle Samples 1": "Total Volume (Vehicles)", "Approach Full": "Approach"},
                color_discrete_map={p1_label: "#94a3b8", p2_label: "#1f4582"},
                text_auto=',.0f'
            )
            _apply_comparison_layout(fig_vol, "Total Vehicles")
            fig_vol.update_traces(
                textfont_size=12,
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>Approach:</b> %{x}<br><b>%{fullData.name}:</b> %{y:,.0f} vehicles<extra></extra>"
            )
            st.plotly_chart(fig_vol, use_container_width=True)

        st.markdown("---")
        st.info(f"**Baseline Period (P1):** {p1_label} ({dr1})  \n"
                f"**Comparison Period (P2):** {p2_label} ({dr2})")
