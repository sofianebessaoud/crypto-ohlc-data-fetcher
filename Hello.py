
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title='Cryptocurrency Historical OHLCV Data Fetcher', layout="wide", page_icon=":chart_with_upwards_trend:")

plt.style.use("dark_background")

st.title('Cryptocurrency Historical OHLC Data Fetcher')
st.markdown("Select the cryptocurrencies, start date, and end date to view historical data.")

def get_tradable_tokens():
    st.write('Fetching the list of all tradable tokens')
    progress_bar = st.progress(0)
    progress_percent = 0
    url = "https://api.exchange.coinbase.com/products"
    response = requests.get(url)
    data = response.json()
    tradable_tokens = []

    for info in data:
        if info['id'].split('-')[-1] == 'USD':
            if info['status'] == 'online':
                tradable_tokens.append(info['id'])
        progress_percent += 1/len(data)
        progress_bar.progress(progress_percent)
    return tradable_tokens

def get_historical_data(product_id, start, end, granularity):
    url = f"https://api.pro.coinbase.com/products/{product_id}/candles"
    params = {'start': start, 'end': end, 'granularity': granularity}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['product_id'] = product_id
        return df
    else:
        st.error(f"Failed to fetch data for {product_id}: {response.status_code}")
        return pd.DataFrame()

def fetch_data_for_tokens(token_list, start_date, end_date, granularity=86400):
    progress_bar = st.progress(0)
    progress_percent = 0

    token_data = {}
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    max_interval = timedelta(days=270)  # Approximately 9 months.

    for token in token_list:
        if token not in st.session_state.token_data:
            all_data = []
            current_start = start_dt
            while current_start < end_dt:
                current_end = min(current_start + max_interval, end_dt)
                df = get_historical_data(token, current_start.isoformat(), current_end.isoformat(), granularity)
                if not df.empty:
                    all_data.append(df)
                current_start = current_end + timedelta(seconds=1)
            if all_data:
                token_data[token] = pd.concat(all_data).sort_values('time')
        
        progress_percent += 1/len(token_list)
        progress_bar.progress(progress_percent)
    st.session_state.token_data.update(token_data)


def plot_data(df, token):
    plt.figure(figsize=(10, 4))
    sns.lineplot(x='time', y='close', data=df)
    plt.title(f'Close Price Over Time for {token}')
    plt.xlabel('Time')
    plt.ylabel('Price (USD)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return plt

@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')


start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=30), key='start_date')
end_date = st.date_input("End Date", datetime.now().date(), key='end_date')
start_date_str = start_date.isoformat()
end_date_str = end_date.isoformat()

# Check if data has been fetched before
if 'token_data' not in st.session_state:
    st.session_state.token_data = {}

if 'tradable_tokens' not in st.session_state:
    st.session_state.tradable_tokens = get_tradable_tokens()

# Check if tokens have been selected before
if 'selected_tokens' not in st.session_state:
    st.session_state.selected_tokens = []


tokens = st.multiselect("Select Tokens", ['All tradable tokens'] + st.session_state.tradable_tokens, st.session_state.selected_tokens)

st.session_state.selected_tokens = tokens

if st.button("Fetch Data"):
    if tokens and start_date and end_date:
        tokens = st.session_state.tradable_tokens if 'All tradable tokens' in tokens else tokens
        st.write(f"Fetching data from {start_date} to {end_date} for {len(tokens)} tokens")
        fetch_data_for_tokens(tokens, start_date_str, end_date_str)
    else:
        st.error("Please select at least one token and ensure dates are correctly set.")

if tokens and st.session_state.token_data:
    selected_token = st.selectbox("Select a token to display", st.session_state.token_data.keys())
    st.write(selected_token)
    data = st.session_state.token_data[selected_token]
    st.dataframe(data)
    fig = plot_data(data, selected_token)
    st.pyplot(fig)

if tokens and st.session_state.token_data:
    df = pd.concat([st.session_state.token_data[token].reset_index() for token in st.session_state.token_data.keys()])

    csv = df.to_csv(index=False) 

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='ohlc_data.csv',
        mime='text/csv',
    )
