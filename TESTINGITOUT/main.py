"""
⚡ EV Pop Dashboard — Washington State Electric Vehicles
Focus: Market Analysis (#1) + Range Analysis (#5)
Style: Kawaii cartoon · periwinkle-blue theme · iPhone-friendly

Run locally:
    pip install streamlit pandas plotly
    streamlit run app.py

Deploy: push this file + the CSV to your repo, point Streamlit Cloud at app.py.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ────────────────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚡ EV Pop Dashboard",
    page_icon="🚗",
    layout="centered",  # 'centered' reads better on iPhone than 'wide'
    initial_sidebar_state="collapsed",
)

# ────────────────────────────────────────────────────────────
# THEME — periwinkle blue from the screenshot + kawaii accents
# ────────────────────────────────────────────────────────────
BLUE = "#9DB4E8"  # periwinkle (address-bar blue)
BLUE_DEEP = "#5C7CD1"
BLUE_INK = "#2E3F6E"
PINK = "#FFB3D1"  # kawaii accent
MINT = "#A8E6CF"
CREAM = "#FFF7FB"
YELLOW = "#FFE066"

PALETTE = [BLUE_DEEP, PINK, MINT, YELLOW, "#C9A7EB", "#FF9AA2", "#7FD8E8", "#B5EAD7"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&family=Quicksand:wght@500;600;700&display=swap');

.stApp {{
    background: linear-gradient(160deg, {CREAM} 0%, #EAF0FF 55%, #DDE7FF 100%);
}}
html, body, [class*="css"] {{ font-family: 'Quicksand', sans-serif; }}
h1, h2, h3 {{ font-family: 'Baloo 2', cursive; color: {BLUE_INK}; }}

/* Hero header */
.hero {{
    background: linear-gradient(135deg, {BLUE} 0%, {BLUE_DEEP} 100%);
    border-radius: 28px;
    padding: 26px 22px;
    text-align: center;
    color: white;
    box-shadow: 0 10px 30px rgba(92,124,209,0.35);
    border: 4px solid white;
    margin-bottom: 8px;
}}
.hero h1 {{ color: white; margin: 0; font-size: 1.9rem; line-height: 1.15; }}
.hero p  {{ margin: 6px 0 0; font-size: 0.95rem; opacity: 0.95; }}

/* Kawaii metric cards */
.kcard {{
    background: white;
    border-radius: 22px;
    padding: 16px 14px;
    text-align: center;
    box-shadow: 0 6px 16px rgba(92,124,209,0.18);
    border: 3px solid {BLUE};
    margin-bottom: 10px;
}}
.kcard .emoji {{ font-size: 1.8rem; }}
.kcard .num   {{ font-family: 'Baloo 2'; font-size: 1.5rem; font-weight: 800; color: {BLUE_DEEP}; }}
.kcard .lbl   {{ font-size: 0.78rem; color: {BLUE_INK}; font-weight: 600; }}

.section {{
    background: white;
    border-radius: 24px;
    padding: 14px 14px 6px;
    box-shadow: 0 6px 18px rgba(92,124,209,0.15);
    border: 3px dashed {PINK};
    margin: 14px 0;
}}
.section h3 {{ margin-top: 4px; }}

/* Streamlit widget tweaks */
.stSelectbox label, .stSlider label, .stMultiSelect label {{
    font-weight: 700 !important; color: {BLUE_INK} !important;
}}
div[data-testid="stMetricValue"] {{ color: {BLUE_DEEP}; }}
#MainMenu, footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────
# DATA
# ────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("Electric_Vehicle_Population_Data.csv")
    df.columns = [c.strip() for c in df.columns]
    # tidy a couple of fields we use a lot
    df["Make"] = df["Make"].str.title()
    df["Model"] = df["Model"].str.upper()
    return df


try:
    df = load_data()
except FileNotFoundError:
    st.error("😿 Couldn't find **Electric_Vehicle_Population_Data.csv**. "
             "Put it in the same folder as app.py (or repo root).")
    st.stop()

# ────────────────────────────────────────────────────────────
# HERO
# ────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <h1>⚡🚗 EV Pop Dashboard 🚗⚡</h1>
    <p>Washington State Electric Vehicles · {len(df):,} cuties registered (◕‿◕)</p>
</div>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────
# FILTERS (collapsible — keeps the phone screen tidy)
# ────────────────────────────────────────────────────────────
with st.expander("🎀 Filters", expanded=False):
    years = sorted(df["Model Year"].dropna().unique())
    yr_lo, yr_hi = st.select_slider(
        "Model Year range",
        options=years,
        value=(years[0], years[-1]),
    )
    ev_types = st.multiselect(
        "EV Type",
        options=sorted(df["Electric Vehicle Type"].dropna().unique()),
        default=sorted(df["Electric Vehicle Type"].dropna().unique()),
    )

mask = (df["Model Year"].between(yr_lo, yr_hi)) & (df["Electric Vehicle Type"].isin(ev_types))
d = df[mask]

if d.empty:
    st.warning("No cars match these filters (╥﹏╥) — try widening them.")
    st.stop()

# ────────────────────────────────────────────────────────────
# KAWAII KPI ROW
# ────────────────────────────────────────────────────────────
top_make = d["Make"].value_counts().idxmax()
ranges = d.loc[d["Electric Range"] > 0, "Electric Range"]
avg_range = int(ranges.mean()) if not ranges.empty else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="kcard"><div class="emoji">🚙</div>'
                f'<div class="num">{len(d):,}</div>'
                f'<div class="lbl">EVs in view</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kcard"><div class="emoji">👑</div>'
                f'<div class="num">{top_make}</div>'
                f'<div class="lbl">Top brand</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kcard"><div class="emoji">🔋</div>'
                f'<div class="num">{avg_range} mi</div>'
                f'<div class="lbl">Avg range*</div></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# #1 — MARKET ANALYSIS
# ════════════════════════════════════════════════════════════
st.markdown('<div class="section"><h3>🏆 Market Analysis — Who rules the road?</h3>',
            unsafe_allow_html=True)

top_n = st.slider("Show top N makes", 5, 20, 10)
make_counts = d["Make"].value_counts().head(top_n).reset_index()
make_counts.columns = ["Make", "Count"]

fig_make = px.bar(
    make_counts, x="Count", y="Make", orientation="h",
    color="Make", color_discrete_sequence=PALETTE, text="Count",
)
fig_make.update_traces(textposition="outside", cliponaxis=False,
                       marker_line_color="white", marker_line_width=2)
fig_make.update_layout(
    showlegend=False, height=420,
    yaxis={"categoryorder": "total ascending", "title": ""},
    xaxis={"title": "Registered vehicles"},
    margin=dict(l=4, r=20, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Quicksand", color=BLUE_INK),
)
st.plotly_chart(fig_make, use_container_width=True, config={"displayModeBar": False})

# Most popular model within the most popular make
st.markdown(f"**🌟 Most popular {top_make} models**")
top_models = (d[d["Make"] == top_make]["Model"]
              .value_counts().head(5).reset_index())
top_models.columns = ["Model", "Count"]
fig_model = px.pie(top_models, names="Model", values="Count", hole=0.55,
                   color_discrete_sequence=PALETTE)
fig_model.update_traces(textinfo="label+percent",
                        marker_line_color="white", marker_line_width=3)
fig_model.update_layout(showlegend=False, height=320,
                        margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Quicksand", color=BLUE_INK))
st.plotly_chart(fig_model, use_container_width=True, config={"displayModeBar": False})

# adoption over time
yearly = d.groupby("Model Year").size().reset_index(name="Count")
fig_year = px.area(yearly, x="Model Year", y="Count",
                   color_discrete_sequence=[BLUE_DEEP])
fig_year.update_traces(line_color=BLUE_DEEP, fillcolor="rgba(92,124,209,0.25)")
fig_year.update_layout(height=280, title="📈 Adoption by model year",
                       margin=dict(l=4, r=10, t=40, b=10),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       font=dict(family="Quicksand", color=BLUE_INK))
st.plotly_chart(fig_year, use_container_width=True, config={"displayModeBar": False})
st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# #5 — RANGE ANALYSIS
# ════════════════════════════════════════════════════════════
st.markdown('<div class="section"><h3>🔋 Range Analysis — How far can they go?</h3>',
            unsafe_allow_html=True)

# Note: many rows have range 0 (not researched) — exclude those for honesty
dr = d[d["Electric Range"] > 0]

if dr.empty:
    st.info("No researched-range values in this filter selection.")
else:
    # avg range by make (top makes only, to stay readable on phone)
    top_makes_list = d["Make"].value_counts().head(10).index
    range_by_make = (dr[dr["Make"].isin(top_makes_list)]
                     .groupby("Make")["Electric Range"].mean()
                     .sort_values(ascending=True).reset_index())
    fig_rng = px.bar(range_by_make, x="Electric Range", y="Make", orientation="h",
                     color="Electric Range", color_continuous_scale=["#FFB3D1", BLUE_DEEP],
                     text=range_by_make["Electric Range"].round(0))
    fig_rng.update_traces(textposition="outside", cliponaxis=False,
                          marker_line_color="white", marker_line_width=2)
    fig_rng.update_layout(height=400, coloraxis_showscale=False,
                          yaxis={"title": ""}, xaxis={"title": "Avg electric range (mi)"},
                          margin=dict(l=4, r=24, t=10, b=10),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Quicksand", color=BLUE_INK))
    st.plotly_chart(fig_rng, use_container_width=True, config={"displayModeBar": False})

    # BEV vs PHEV range distribution
    fig_box = px.box(dr, x="Electric Vehicle Type", y="Electric Range",
                     color="Electric Vehicle Type", color_discrete_sequence=[BLUE_DEEP, PINK])
    fig_box.update_layout(height=340, showlegend=False,
                          title="🥊 BEV vs PHEV range spread",
                          xaxis={"title": ""}, yaxis={"title": "Range (mi)"},
                          margin=dict(l=4, r=10, t=40, b=10),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Quicksand", color=BLUE_INK))
    st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})

    # range improving over time?
    rng_year = dr.groupby("Model Year")["Electric Range"].mean().reset_index()
    fig_ry = px.line(rng_year, x="Model Year", y="Electric Range", markers=True,
                     color_discrete_sequence=[MINT])
    fig_ry.update_traces(line_width=4, marker=dict(size=9, color=BLUE_DEEP,
                                                   line=dict(color="white", width=2)))
    fig_ry.update_layout(height=300, title="🚀 Avg range over the years",
                         xaxis={"title": ""}, yaxis={"title": "Avg range (mi)"},
                         margin=dict(l=4, r=10, t=40, b=10),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(family="Quicksand", color=BLUE_INK))
    st.plotly_chart(fig_ry, use_container_width=True, config={"displayModeBar": False})

st.markdown('</div>', unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────
st.caption("*Avg range excludes records where range = 0 (not yet researched). "
           "Data: WA State EV Population Dataset 🌸")