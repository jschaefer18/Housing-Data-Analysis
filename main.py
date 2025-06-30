# streamlit run main.py

#%%
import streamlit as st
import pandas as pd
import plotly.express as px
import warnings

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
# === Midland, TX line chart ===
midland = long_df[long_df['RegionName'] == 'Midland, TX'].copy()
midland['HomeValue'] = pd.to_numeric(midland['HomeValue'], errors='coerce')
midland = midland.dropna(subset=['HomeValue'])
midland_avg = midland.groupby('Date')['HomeValue'].mean().reset_index()

fig = px.line(
    midland,
    x='Date',
    y='HomeValue',
    title='Midland, TX Home Values Over Time',
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

st.title("Midland, TX Housing Data")
fig = px.line(midland_avg, x="Date", y="HomeValue", title="Midland, TX ZHVI Over Time")
st.plotly_chart(fig)
#%%
