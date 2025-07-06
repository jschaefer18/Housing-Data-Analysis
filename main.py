# streamlit run main.py hi

#%%
import streamlit as st
import pandas as pd
import plotly.express as px
import warnings
import plotly.graph_objects as go
from prophet import Prophet

st.set_page_config(page_title="Housing Dashboard", layout="wide")
warnings.filterwarnings("ignore")

#%%
# === Load and reshape housing data ===
housing_file_path = 'metro_data.csv'
df = pd.read_csv(housing_file_path)

date_columns = df.columns[5:]  # First 5 are region/state info
long_df = pd.melt(
    df,
    id_vars=['RegionID', 'SizeRank', 'RegionName', 'RegionType', 'StateName'],
    value_vars=date_columns,
    var_name='Date',
    value_name='HomeValue'
)
long_df['Date'] = pd.to_datetime(long_df['Date'])

#%%
# === Load and clean income data ===
income_file_path = 'personal_income.csv'
salary_df = pd.read_csv(income_file_path, skiprows=3)
salary_df.rename(columns={"GeoName": "RegionName"}, inplace=True)
salary_df["RegionName"] = salary_df["RegionName"].str.strip()

salary_subset = salary_df[["RegionName", "2015", "2023"]].copy()
salary_subset.rename(columns={"2015": "Income_2015", "2023": "Income_2023"}, inplace=True)
salary_subset["Income_2015"] = pd.to_numeric(salary_subset["Income_2015"], errors="coerce")
salary_subset["Income_2023"] = pd.to_numeric(salary_subset["Income_2023"], errors="coerce")
salary_subset.dropna(subset=["Income_2015", "Income_2023"], inplace=True)
salary_subset["IncomePercentChange"] = (
    (salary_subset["Income_2023"] - salary_subset["Income_2015"]) / salary_subset["Income_2015"]
) * 100

# Drop national average row and clean names
salary_subset = salary_subset[salary_subset["RegionName"] != "United States (Metropolitan Portion)"]
salary_subset["RegionName"] = salary_subset["RegionName"].str.replace(r"\s*\(.*\)", "", regex=True).str.strip()

#%%
# === Compute affordability using housing and income ===
housing_subset = long_df[long_df['Date'].isin([
    pd.to_datetime('2015-06-30'),
    pd.to_datetime('2024-06-30')
])]

pivot = housing_subset.pivot_table(
    index='RegionName',
    columns=housing_subset['Date'].dt.year,
    values='HomeValue'
)
pivot.columns = ['ZHVI_2015', 'ZHVI_2024']
pivot = pivot.dropna()
pivot['PercentChange'] = ((pivot['ZHVI_2024'] - pivot['ZHVI_2015']) / pivot['ZHVI_2015']) * 100

combined = pivot.merge(salary_subset, on="RegionName", how="inner")

#%%
# === Add state rankings ===
state_scores = pd.read_csv("state_rankings.csv")
state_scores.columns = ["StateName", "StateScore"]

# Merge state score into housing/income table
full_data = combined.merge(df[["RegionName", "StateName"]], on="RegionName", how="left")
full_data = full_data.merge(state_scores, on="StateName", how="left")

# Drop any rows with missing values
full_data.dropna(subset=["StateScore"], inplace=True)

full_data = full_data[full_data["RegionName"] != "Midland, TX"]

# Calculate weighted score (40% housing, 30% income, 30% state)
full_data["Score"] = (
    (100 - full_data["PercentChange"]) * 0.4 +
    (full_data["IncomePercentChange"]) * 0.3 +
    (full_data["StateScore"]) * 0.3
)

top_score = full_data.sort_values(by="Score", ascending=False).head(10)

# Streamlit output
st.subheader("Top 10 Best Cities to Live In")
st.dataframe(top_score[[
    "RegionName", "StateName", "ZHVI_2015", "ZHVI_2024", "PercentChange",
    "Income_2015", "Income_2023", "IncomePercentChange", "StateScore", "Score"
]].style.format({
    "ZHVI_2015": "${:,.0f}",
    "ZHVI_2024": "${:,.0f}",
    "PercentChange": "{:.2f}%",
    "Income_2015": "${:,.0f}",
    "Income_2023": "${:,.0f}",
    "IncomePercentChange": "{:.2f}%",
    "StateScore": "{:.1f}",
    "Score": "{:.2f}"
}))

#%%
# === Johnstown, PA line chart ===
johnstown = long_df[long_df['RegionName'] == 'Johnstown, PA'].copy()
johnstown['HomeValue'] = pd.to_numeric(johnstown['HomeValue'], errors='coerce')
johnstown = johnstown.dropna(subset=['HomeValue'])
johnstown_avg = johnstown.groupby('Date')['HomeValue'].mean().reset_index()

fig = px.line(
    johnstown,
    x='Date',
    y='HomeValue',
    title='Johnstown, PA Home Values Over Time',
    labels={'HomeValue': 'ZHVI ($)', 'Date': 'Date'},
    hover_data={'Date': True, 'HomeValue': ':.2f'}
)
fig.update_layout(
    xaxis_title='Date',
    yaxis_title='ZHVI ($)',
    hovermode='x unified',
    template='plotly_white'
)
fig.show()

st.title("Johnstown, PA Housing Data")
fig = px.line(johnstown_avg, x="Date", y="HomeValue", title="Johnstown, PA ZHVI Over Time")
st.plotly_chart(fig)
#%%



#%%
# --- Begin “Worst Cities” Section ---
# Filter only cities in states with decent quality (>=70)
high_quality = state_scores[state_scores['StateScore'] >= 70]['StateName'].tolist()
df_good_states = full_data[full_data['StateName'].isin(high_quality)]

# If you want the opposite (i.e., bad states), invert:
bad_states = state_scores[state_scores['StateScore'] < 70]['StateName'].tolist()
df_bad_states = full_data[full_data['StateName'].isin(bad_states)]

# Compute a “DangerScore”: high housing growth (bad), low income growth (bad), low state score (bad)
df_bad_states = df_bad_states.copy()
df_bad_states['DangerScore'] = (
    df_bad_states['PercentChange'] * 0.5
    - df_bad_states['IncomePercentChange'] * 0.3
    - df_bad_states['StateScore'] * 0.2
)

# Rank worst (highest DangerScore)
worst10 = df_bad_states.sort_values('DangerScore', ascending=False).head(10)

# --- Begin “Worst Cities” Section ---
st.subheader("Top 10 Worst Cities to Live In")

# Show table first
st.dataframe(
    worst10[[
        'RegionName','StateName','ZHVI_2015','ZHVI_2024','PercentChange',
        'Income_2015','Income_2023','IncomePercentChange','StateScore','DangerScore'
    ]].style.format({
        'ZHVI_2015':'${:,.0f}','ZHVI_2024':'${:,.0f}','PercentChange':'{:.2f}%',
        'Income_2015':'${:,.0f}','Income_2023':'${:,.0f}','IncomePercentChange':'{:.2f}%',
        'StateScore':'{:.1f}','DangerScore':'{:.2f}'
    })
)

# Then the line chart
worst_city = worst10.iloc[0]['RegionName']
chart_df = long_df[long_df['RegionName'] == worst_city].dropna(subset=['HomeValue'])
chart_avg = chart_df.groupby('Date')['HomeValue'].mean().reset_index()

st.subheader(f"{worst_city} Housing Data")
fig = px.line(
    chart_avg,
    x='Date',
    y='HomeValue',
    title=f"{worst_city} ZHVI Over Time",
    labels={'HomeValue': 'ZHVI ($)', 'Date': 'Date'}
)
fig.update_layout(xaxis_title='Date', yaxis_title='ZHVI ($)', template='plotly_white')
st.plotly_chart(fig)
# --- End Section ---
#%%



#%%
# Aggregate national median home value
national = long_df.groupby("Date")["HomeValue"].median().reset_index()
national = national.dropna()

# Rename for Prophet format
prophet_df = national.rename(columns={"Date": "ds", "HomeValue": "y"})

# Train Prophet model
model = Prophet()
model.fit(prophet_df)

# Forecast next 5 years (60 months)
future = model.make_future_dataframe(periods=60, freq='M')
forecast = model.predict(future)

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(x=prophet_df["ds"], y=prophet_df["y"], name="Actual", line=dict(color='blue')))
fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], name="Predicted", line=dict(color='orange', dash='dash')))
fig.update_layout(
    title="Projected US Median Housing Prices (Next 5 Years)",
    xaxis_title="Date",
    yaxis_title="ZHVI ($)",
    hovermode="x unified",
    template="plotly_white"
)

st.subheader("US Housing Price Forecast")
st.plotly_chart(fig)



# Get 2025 actual and 2030 predicted values
price_2025 = national[national["Date"].dt.year == 2025]["HomeValue"].median()
price_2030 = forecast[forecast["ds"].dt.year == 2030]["yhat"].median()

# Calculate percent increase
percent_diff = ((price_2030 - price_2025) / price_2025) * 100

# Display result
st.markdown(f"**Projected Percent Increase in US Median Home Prices (2025 → 2030):** {percent_diff:.2f}%")

#%%