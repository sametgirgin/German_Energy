"""
Streamlit dashboard: German Power Plant Tracker.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_CSV = "GERMAN ENERGY DATA.xlsx - GERMAN POWER .csv"
DATA_EXCEL = "GERMAN ENERGY DATA.xlsx"
EXCEL_SHEET = "Sheet1"
COLOR_SEQUENCE = px.colors.qualitative.Dark24


st.set_page_config(
    page_title="German Power Plant Tracker",
    layout="wide",
    page_icon="⚡",
)


@st.cache_data(show_spinner=True)
def load_data(
    csv_path: str = DATA_CSV,
    excel_path: str = DATA_EXCEL,
    excel_sheet: str = EXCEL_SHEET,
) -> pd.DataFrame:
    """
    Load data from the Excel workbook. A CSV can also be used if present.
    Applies basic cleaning: numeric conversions and trimmed strings.
    """
    df: Optional[pd.DataFrame] = None
    excel_file = Path(excel_path)

    # Prefer Excel; optionally allow CSV if the user provides one.
    if excel_file.exists():
        df = pd.read_excel(excel_file, sheet_name=excel_sheet)
    elif Path(csv_path).exists():
        df = pd.read_csv(csv_path)
    else:
        st.error(f"'{excel_path}' not found in the app directory.", icon="🚫")
        return pd.DataFrame()

    # Basic cleaning
    df["Capacity (MW)"] = pd.to_numeric(df.get("Capacity (MW)"), errors="coerce")
    df["Start year"] = pd.to_numeric(df.get("Start year"), errors="coerce")
    df["Retired year"] = pd.to_numeric(df.get("Retired year"), errors="coerce")
    for col in ["Status", "Technology", "Fuel", "Owner", "Plant / Project name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def get_year_range(series: pd.Series) -> Tuple[int, int]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return (2000, 2025)
    return (int(numeric.min()), int(numeric.max()))


def sidebar_filters(data: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")

    status_options = sorted(data["Status"].dropna().unique())
    default_status = ["Operating"] if "Operating" in status_options else [
        s for s in status_options if s.lower() == "operating"
    ]
    statuses = st.sidebar.multiselect(
        "Status",
        status_options,
        default=default_status if default_status else status_options,
        help="Filter plant status; defaults to Operating when available.",
    )

    type_options = sorted(data["Type"].dropna().unique()) if "Type" in data.columns else []
    types = st.sidebar.multiselect(
        "Type",
        type_options,
        default=[],
    )

    tech_options = sorted(data["Technology"].dropna().unique()) if "Technology" in data.columns else []
    techs = st.sidebar.multiselect(
        "Technology",
        tech_options,
        default=[],
    )

    fuel_options = sorted(data["Fuel"].dropna().unique())
    fuels = st.sidebar.multiselect(
        "Fuel",
        fuel_options,
        default=[],
    )

    year_min, year_max = get_year_range(data["Start year"])
    start_year_range = st.sidebar.slider(
        "Start year range",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
        step=1,
    )

    owner_options = sorted(data["Owner"].dropna().unique())
    owners = st.sidebar.multiselect(
        "Owner (optional)",
        owner_options,
        default=[],
    )

    filtered = data.copy()
    if statuses:
        status_lower = {s.lower() for s in statuses}
        filtered = filtered[
            filtered["Status"].str.lower().isin(status_lower)
        ]

    if types:
        filtered = filtered[filtered["Type"].isin(types)]

    if techs:
        filtered = filtered[filtered["Technology"].isin(techs)]

    if fuels:
        filtered = filtered[filtered["Fuel"].isin(fuels)]

    if owners:
        filtered = filtered[filtered["Owner"].isin(owners)]

    filtered = filtered[
        filtered["Start year"].between(start_year_range[0], start_year_range[1])
    ]

    return filtered


def render_kpis(data: pd.DataFrame) -> None:
    total_plants = len(data)
    total_capacity_mw = data["Capacity (MW)"].sum(skipna=True)
    avg_capacity = data["Capacity (MW)"].mean(skipna=True)
    type_col = "Type" if "Type" in data.columns else "Technology"
    most_common_type = (
        data[type_col].mode(dropna=True).iloc[0]
        if type_col in data.columns and not data[type_col].mode(dropna=True).empty
        else "N/A"
    )

    cols = st.columns(4)
    cols[0].metric("Plants", f"{total_plants:,}")
    cols[1].metric("Total Capacity", f"{total_capacity_mw/1000:,.2f} GW")
    cols[2].metric("Avg Capacity", f"{avg_capacity:,.1f} MW")
    cols[3].metric("Top Type", most_common_type)


def render_map(data: pd.DataFrame) -> None:
    #st.subheader("Geospatial View")
    map_data = data.dropna(subset=["Latitude", "Longitude", "Capacity (MW)"])
    if map_data.empty:
        st.info("No locations available with latitude/longitude.", icon="ℹ️")
        return

    color_by = "Technology" if "Technology" in map_data.columns else None
    if color_by is None:
        st.info("Technology column not available for coloring the map.", icon="ℹ️")
        return

    fig = px.scatter_mapbox(
        map_data,
        lat="Latitude",
        lon="Longitude",
        color=color_by,
        size="Capacity (MW)",
        hover_name="Plant / Project name",
        hover_data={
            "Capacity (MW)": ":,.1f",
            "Owner": True,
            "Status": True,
            "Technology": True if "Technology" in map_data.columns else False,
        },
        color_discrete_sequence=COLOR_SEQUENCE,
        size_max=35,
        zoom=4.5,
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=10, r=10, t=10, b=10),
        height=520,
        legend_title=color_by,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_capacity_by_dimension(data: pd.DataFrame) -> None:
    st.subheader("Total Capacity by Technology/Fuel")
    dim_options = []
    if "Type" in data.columns:
        dim_options.append("Type")
    if "Fuel" in data.columns:
        dim_options.append("Fuel")
    if not dim_options and "Technology" in data.columns:
        dim_options.append("Technology")
    dimension = st.radio(
        "Group by",
        dim_options,
        horizontal=True,
        index=0,
        key="capacity_group_by",
    )
    grouped = (
        data.groupby(dimension, as_index=False)["Capacity (MW)"]
        .sum()
        .sort_values("Capacity (MW)", ascending=False)
    )
    fig = px.bar(
        grouped,
        x=dimension,
        y="Capacity (MW)",
        color=dimension,
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={"Capacity (MW)": "Capacity (MW)"},
    )
    fig.update_layout(xaxis_title=dimension, yaxis_title="Capacity (MW)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_timeline(data: pd.DataFrame) -> None:
    st.subheader("Capacity Added Over Time")
    timeline_df = (
        data.dropna(subset=["Start year"])
        .groupby("Start year", as_index=False)["Capacity (MW)"]
        .sum()
        .sort_values("Start year")
    )
    if timeline_df.empty:
        st.info("No start year data available for the selected filters.", icon="ℹ️")
        return
    fig = px.area(
        timeline_df,
        x="Start year",
        y="Capacity (MW)",
        color_discrete_sequence=[COLOR_SEQUENCE[0]],
    )
    fig.update_layout(xaxis_title="Start year", yaxis_title="Capacity (MW)")
    st.plotly_chart(fig, use_container_width=True)


def render_status_distribution(data: pd.DataFrame) -> None:
    st.subheader("Status Distribution")
    status_df = data["Status"].fillna("Unknown").value_counts().reset_index()
    status_df.columns = ["Status", "Count"]
    fig = px.pie(
        status_df,
        names="Status",
        values="Count",
        color="Status",
        color_discrete_sequence=COLOR_SEQUENCE,
        hole=0.3,
    )
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    logo_path = Path("Logo.png")
    title_col, flag_col = st.columns([8, 1])
    with title_col:
        st.title("German Power Plant Tracker")
        st.caption(
            "Explore Germany's power generation landscape by capacity, technology, and geography. "
            "Use the filters to focus on specific technologies, fuels, owners, or time periods."
        )
    with flag_col:
        st.markdown(
            "<div style='text-align:right; font-size: 42px;'>🇩🇪</div>",
            unsafe_allow_html=True,
        )

    data = load_data()
    if data.empty:
        st.stop()

    filtered = sidebar_filters(data)
    # st.info(f"{len(filtered):,} plants match your filters.", icon="📊")

    render_kpis(filtered)

    st.markdown("---")
    render_map(filtered)

    st.markdown("---")
    left, right, extra = st.columns([1.4, 1.4, 1])
    with left:
        render_capacity_by_dimension(filtered)
    with right:
        render_timeline(filtered)
    with extra:
        render_status_distribution(filtered)

    st.markdown("---")
    with st.expander("Show raw data"):
        st.dataframe(
            filtered[
                [
                    "Type" if "Type" in filtered.columns else "Technology",
                    "Plant / Project name",
                    "Capacity (MW)",
                    "Status",
                    "Start year",
                    "Retired year",
                    "Fuel",
                    "Owner",
                    "Latitude",
                    "Longitude",
                    "Subnational unit (state, province)",
                ]
            ],
            use_container_width=True,
        )

    # Footer logo
    if logo_path.exists():
        st.markdown("---")
        st.image(str(logo_path), use_container_width=False, width=200)

    st.caption(
        "\"Germany Integrated Power Tracker\" is a comprehensive study and dataset monitoring the rapid "
        "transformation of Germany's energy landscape. It tracks the operational status, capacity, "
        "and geolocation of power assets across the country, serving as a vital tool for analyzing "
        "Germany's \"Energiewende\" (energy transition). Key focus areas include the phase-out of coal "
        "and nuclear assets, the expansion of renewables (wind, solar), and the emerging hydrogen economy."
    )


if __name__ == "__main__":
    main()
