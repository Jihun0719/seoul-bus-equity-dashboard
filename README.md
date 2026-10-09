# Seoul Bus Infrastructure Equity Dashboard by District

## 1. Project Overview

This project aims to analyze the equity of bus infrastructure across Seoul's districts using public transportation and population data.

The dashboard compares bus stop distribution, population, living population, and district area to identify differences in bus infrastructure accessibility.

## 2. How to Run

**Requirements**
- Python 3.10 or later
- Streamlit
- Pandas
- Plotly
- Folium

**Installation**

```bash
pip install -r requirements.txt
```

**Run the Dashboard**

```bash
streamlit run app.py
```

The dashboard will be available at:

http://localhost:8501

*Note: These instructions are planned and will be verified after implementation.*

## 3. Data Used

**Primary Dataset**
- Seoul Bus Stop Location Information

**Additional Datasets**
- Daily Seoul Living Population Statistics by District
- District Area and Registered Population Statistics

**Data Source**
- Seoul Open Data Plaza

## 4. Class Design and Object Interactions

The project uses four main Python classes.

**BusStop**
- Stores individual bus stop information.
- Attributes: stop_id, latitude, longitude, district
- Methods: get_location(), get_district()

**District**
- Manages district-level data and calculates infrastructure indicators.
- Attributes: district_name, area, population, living_population, bus_stop_count
- Methods: calculate_stop_density(), calculate_stops_per_population(), calculate_equity_score()

**DataLoader**
- Loads and preprocesses public datasets.
- Methods: load_data(), clean_data(), merge_data()

**Visualizer**
- Creates dashboard maps, charts, and statistics.
- Methods: create_map(), create_bar_chart(), create_scatter_plot(), show_statistics()

**Object Interaction Flow**

DataLoader → BusStop / District → District Indicator Calculation → Visualizer → Dashboard

## 5. Dashboard Features

**Bus Infrastructure Map**
- District-level bus stop density heatmap
- Interactive district selection

**District Comparison**
- Bus stops per square kilometer
- Bus stops per 10,000 residents
- Bus stop availability relative to living population
- District rankings and equity scores

**Demand and Equity Analysis**
- Scatter plot comparing living population and bus stop counts
- Identification of relatively underserved districts
- Detailed district statistics

## 6. Development Status

This project is currently in the planning and development stage. Features and execution instructions will be updated as development progresses.
