# streamlit run main.py

#%%
import streamlit as st
st.set_page_config(page_title="Housing Dashboard", layout="wide")  # MUST be before all Streamlit code

import pandas as pd
import plotly.express as px
import warnings
warnings.filterwarnings("ignore")

file_path = 'metro_data.csv'
df = pd.read_csv(file_path)

# Optionally, show a preview on the page instead of terminal
st.dataframe(df.head())
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

# Preview
long_df.head()
#%%



#%%
atlanta = long_df[long_df['RegionName'] == 'Atlanta, GA'].copy()
atlanta['HomeValue'] = pd.to_numeric(atlanta['HomeValue'], errors='coerce')
atlanta = atlanta.dropna(subset=['HomeValue'])
atlanta_avg = atlanta.groupby('Date')['HomeValue'].mean().reset_index()

print(atlanta[['Date', 'HomeValue']].head(10))
print(atlanta['HomeValue'].describe())


fig = px.line(
    atlanta,
    x='Date',
    y='HomeValue',
    title='Atlanta, GA Home Values Over Time',
    labels={'HomeValue': 'ZHVI ($)', 'Date': 'Date'},
    hover_data={'Date': True, 'HomeValue': ':.2f'}  # Format ZHVI to 2 decimals
)

fig.update_layout(
    xaxis_title='Date',
    yaxis_title='ZHVI ($)',
    hovermode='x unified',
    template='plotly_white'
)

fig.show()

st.title("Atlanta Housing Data")
fig = px.line(atlanta_avg, x="Date", y="HomeValue", title="GA ZHVI Over Time")
st.plotly_chart(fig)
#%%


#%%

# Question 1: “What has become the most affordable region in the U.S. over the past 10 years?”
# Filter for June 2015 and June 2024 using end-of-month dates
subset = long_df[long_df['Date'].isin([
    pd.to_datetime('2015-06-30'),
    pd.to_datetime('2024-06-30')
])]

# Pivot the data so each RegionName has two columns: 2015 and 2024
pivot = subset.pivot_table(index='RegionName', columns=subset['Date'].dt.year, values='HomeValue')

# Rename columns and drop regions with missing values
pivot.columns = ['ZHVI_2015', 'ZHVI_2024']
pivot = pivot.dropna()

# Calculate percent change over the 10-year period
pivot['PercentChange'] = ((pivot['ZHVI_2024'] - pivot['ZHVI_2015']) / pivot['ZHVI_2015']) * 100

# Sort regions by lowest percent increase (most affordable growth)
most_affordable = pivot.sort_values(by='PercentChange')

# Show top 10 in terminal
print("Top 10 Most Affordable ZHVI Growth Regions (2015–2024):")
print(most_affordable.head(10))

# Streamlit output
st.subheader("Top 10 Most Affordable Regions (2015–2024)")
st.dataframe(most_affordable.head(10).style.format({
    "ZHVI_2015": "${:,.0f}",
    "ZHVI_2024": "${:,.0f}",
    "PercentChange": "{:.2f}%"
}))

#%%