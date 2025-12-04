# German Power Plant Tracker (Streamlit)

Interactive dashboard to explore the German Power Plant dataset (capacity, status, technology, fuel, locations). Built with Streamlit + Plotly.

## Setup
- Place `GERMAN ENERGY DATA.xlsx` (and `Logo.png` if desired) in the app directory.
- Install deps: `pip install streamlit pandas plotly openpyxl`
- Run: `streamlit run app.py`

## Features
- Sidebar filters: Status, Type, Technology, Fuel, Start-year range, Owner.
- KPIs: plant count, total/average capacity, top type.
- Map: plotted by Technology, sized by capacity with rich hover details.
- Charts: capacity by category, capacity over time, status distribution.
- Raw data expander and footer logo/text.

## Notes
- Uses cached data loading for performance.
- Requires latitude/longitude for map points; rows missing both are excluded from the map.
