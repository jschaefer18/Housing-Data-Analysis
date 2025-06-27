# streamlit run main.py

#%%
import streamlit as st
import pandas as pd
import plotly.express as px
import warnings

st.set_page_config(page_title="Housing Dashboard", layout="wide")
warnings.filterwarnings("ignore")

# Load housing data
housing_file_path = 'metro_data.csv'
df = pd.read_csv(housing_file_path)


#%%


# %%
date_columns = df.columns[5:]  # First 5 are region/state info

# Melt into long format
long_df = pd.melt(
    df,
    id_vars=['RegionID', 'SizeRank', 'RegionName', 'RegionType', 'StateName'],
    value_vars=date_columns,
    var_name='Date',
    value_name='HomeValue'
)

# Convert 'Date' to datetime
long_df['Date'] = pd.to_datetime(long_df['Date'])


#%%

#%%
# Load income data
income_file_path = 'personal_income.csv'
salary_df = pd.read_csv(income_file_path, skiprows=3)

# Rename + clean
salary_df.rename(columns={"GeoName": "RegionName"}, inplace=True)
salary_df["RegionName"] = salary_df["RegionName"].str.strip()

# Narrow to relevant columns
salary_subset = salary_df[["RegionName", "2015", "2023"]].copy()
salary_subset.rename(columns={"2015": "Income_2015", "2023": "Income_2023"}, inplace=True)

# Convert and drop bad rows
salary_subset["Income_2015"] = pd.to_numeric(salary_subset["Income_2015"], errors="coerce")
salary_subset["Income_2023"] = pd.to_numeric(salary_subset["Income_2023"], errors="coerce")
salary_subset.dropna(subset=["Income_2015", "Income_2023"], inplace=True)

# Calculate income percent change
salary_subset["IncomePercentChange"] = (
    (salary_subset["Income_2023"] - salary_subset["Income_2015"]) / salary_subset["Income_2015"]
) * 100



#%%



#%%
# Step 1: Create housing affordability summary (ZHVI % change)
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

# Drop the national summary row
salary_subset = salary_subset[salary_subset["RegionName"] != "United States (Metropolitan Portion)"]

# Clean RegionName in salary data to match metro_data.csv format
# Strip out " (Metropolitan Statistical Area)" suffix
salary_subset["RegionName"] = salary_subset["RegionName"].str.replace(r"\s*\(.*\)", "", regex=True).str.strip()

# Merge with housing growth data
combined = pivot.merge(salary_subset, on="RegionName", how="inner")

# Create Affordability Score
combined["AffordabilityScore"] = combined["IncomePercentChange"] - combined["PercentChange"]

# Show top 10 most affordable regions
top_affordable = combined.sort_values(by="AffordabilityScore", ascending=False).head(10)

# Streamlit Output
st.subheader("Top 10 Most Affordable Regions (2015–2024 Housing vs 2015–2023 Income)")
st.dataframe(top_affordable.style.format({
    "ZHVI_2015": "${:,.0f}",
    "ZHVI_2024": "${:,.0f}",
    "PercentChange": "{:.2f}%",
    "Income_2015": "${:,.0f}",
    "Income_2023": "${:,.0f}",
    "IncomePercentChange": "{:.2f}%",
    "AffordabilityScore": "{:.2f}"
}))



#%%






#%%
lafayette = long_df[long_df['RegionName'] == 'Lafayette, LA'].copy()
lafayette['HomeValue'] = pd.to_numeric(lafayette['HomeValue'], errors='coerce')
lafayette = lafayette.dropna(subset=['HomeValue'])
lafayette_avg = lafayette.groupby('Date')['HomeValue'].mean().reset_index()

print(lafayette[['Date', 'HomeValue']].head(10))
print(lafayette['HomeValue'].describe())

fig = px.line(
    lafayette,
    x='Date',
    y='HomeValue',
    title='Lafayette, LA Home Values Over Time',
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

st.title("Lafayette, LA Housing Data")
fig = px.line(lafayette_avg, x="Date", y="HomeValue", title="Lafayette, LA ZHVI Over Time")
st.plotly_chart(fig)
#%%


#%%
# Filter for Wisconsin cities using RegionName suffix
wi_subset = long_df[
    (long_df["RegionName"].str.endswith(", WI")) &
    (long_df["Date"].isin([
        pd.to_datetime("2015-06-30"),
        pd.to_datetime("2024-06-30")
    ]))
]

# Pivot ZHVI for 2015 and 2024
wi_pivot = wi_subset.pivot_table(index='RegionName', columns=wi_subset['Date'].dt.year, values='HomeValue')
wi_pivot.columns = ['ZHVI_2015', 'ZHVI_2024']
wi_pivot.dropna(inplace=True)

# Calculate percent change in home values
wi_pivot['PercentChange'] = ((wi_pivot['ZHVI_2024'] - wi_pivot['ZHVI_2015']) / wi_pivot['ZHVI_2015']) * 100

# Merge with income data
merged_wi = wi_pivot.merge(salary_subset, on='RegionName', how='inner')

# Calculate affordability score (lower is more affordable)
merged_wi["AffordabilityScore"] = merged_wi["PercentChange"] / merged_wi["IncomePercentChange"]

# Sort and get top 10
top10_wi = merged_wi.sort_values("AffordabilityScore").head(10).reset_index()  # <--- this keeps RegionName as a column

# Streamlit display
st.subheader("Top 10 Most Affordable WI Cities (2015–2024)")
st.dataframe(top10_wi[[
    "RegionName", "ZHVI_2015", "ZHVI_2024", "PercentChange",
    "Income_2015", "Income_2023", "IncomePercentChange", "AffordabilityScore"
]].style.format({
    "ZHVI_2015": "${:,.0f}",
    "ZHVI_2024": "${:,.0f}",
    "PercentChange": "{:.2f}%",
    "Income_2015": "${:,.0f}",
    "Income_2023": "${:,.0f}",
    "IncomePercentChange": "{:.2f}%",
    "AffordabilityScore": "{:.2f}"
}))
#%%

