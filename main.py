#%%
import pandas as pd
import plotly.express as px
file_path = 'metro_data.csv'
df = pd.read_csv(file_path)

# Display the first few rows of the DataFrame
df.head()
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


#%%