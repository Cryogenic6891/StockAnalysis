import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

# URL of the page to scrape
url = "https://stockanalysis.com/list/toronto-stock-exchange/"

# Target filepath
file_path = 'tsx_all_stocks_2000_today.csv'

download_required = True
end_date = datetime.today().strftime('%Y-%m-%d')  # Gets today's date
status = ""

# Check if the file exists
if os.path.exists(file_path):
    # Get the file creation time
    creation_time = os.path.getctime(file_path)
    creation_date = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d')
    print(f"File created on: {creation_date}")
    modification_time = os.path.getmtime(file_path)
    modification_date = datetime.fromtimestamp(modification_time).strftime('%Y-%m-%d')
    if creation_date == end_date or modification_date == end_date:
        download_required = False
        status = "information already downloaded and cleaned"
else:
    print(f"The file '{file_path}' does not exist.")

if download_required:
    # Fetch the content from the URL
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Tickers for companies
    tickers = []
    table = soup.find('table')

    # Loop through the table rows and extract the tickers
    for row in table.find_all('tr')[1:]:  # Skip the header row
        cols = row.find_all('td')
        if cols:
            ticker = cols[1].text.strip()  # The ticker symbol should be in the second column
            ticker = ticker.replace('.', '-')  # Remove '.' and input '-'
            ticker = ticker.replace('TSX: ', '') + '.TO'  # Remove 'TSX: ' and append '.TO'
            tickers.append(ticker)

    # Load tickers into a DataFrame
    df = pd.DataFrame(tickers, columns=['Ticker'])

    # Check for missing data and fill with interpolation
    df = df.ffill()
    df.to_csv('canadian_stocks.csv')

    # Load the list of tickers from the CSV file
    df_tickers = pd.read_csv('canadian_stocks.csv')
    tickers = df_tickers['Ticker'].tolist()

    # Define the date range
    start_date = '2000-01-01'

    # Initialize an empty DataFrame to hold the combined data
    combined_data = pd.DataFrame()

    # Function to clean the downloaded data
    def clean_numeric_column(column):
        """Remove leading quotes and convert to numeric."""
        return pd.to_numeric(column.replace("'", "", regex=True), errors='coerce')

    # Loop through the tickers and download the data
    for ticker in tickers:
        print(f"Downloading data for {ticker}...")
        data = yf.download(ticker, start=start_date, end=end_date)
        
        # Clean numeric columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            data[col] = clean_numeric_column(data[col])
        
        # Rename the columns to include the ticker as a prefix
        data.columns = [f"{ticker}_{col}" for col in data.columns]
        
        # Concatenate the data to the combined DataFrame
        combined_data = pd.concat([combined_data, data], axis=1)

    # Reset the index to include the Date column as a regular column
    combined_data.reset_index(inplace=True)

    # Save the combined data to a CSV file
    combined_data.to_csv(file_path, index=False)

    status = "information downloaded and cleaned"

print(status)

finished_data = pd.read_csv(file_path, index_col='Date', parse_dates=True)

# Get unique tickers for dropdown options
unique_tickers = sorted(list(set([col.split('_')[0] for col in finished_data.columns if 'Close' in col])))

# Initialize Dash app
app = dash.Dash(__name__)

# Layout of the app
app.layout = html.Div([
    html.H1("Interactive Stock Price Dashboard"),
    dcc.Dropdown(
        id='ticker-dropdown',
        options=[{'label': ticker, 'value': ticker} for ticker in unique_tickers],
        value=['RY.TO', 'TD.TO'],  # Default value
        multi=True
    ),
    dcc.Graph(id='price-graph')
])

# Callback to update graph
@app.callback(
    Output('price-graph', 'figure'),
    [Input('ticker-dropdown', 'value')]
)
def update_graph(selected_tickers):
    fig = go.Figure()

    for ticker in selected_tickers:
        column_name = f"{ticker}_Close"
        if column_name in finished_data.columns:
            fig.add_trace(go.Scatter(x=finished_data.index, y=finished_data[column_name], mode='lines', name=ticker))

    fig.update_layout(title='Stock Prices Over Time', xaxis_title='Date', yaxis_title='Close Price')
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
