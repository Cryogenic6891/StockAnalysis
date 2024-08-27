import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os

import matplotlib.pyplot as plt
import numpy as np

# URL of the page to scrape
url = "https://stockanalysis.com/list/toronto-stock-exchange/"

# target filepath
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
    print(f"File last modified on: {modification_date}")
    if creation_date == end_date:
        download_required = False
        status = "information already downloaded and cleaned"
    elif modification_date == end_date:
        download_required = False
        status = "information already modified today"
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

    # Display the first few rows
    print(df.head())

    # Check for missing data and fill with interpolation
    print(df.isnull().sum())
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
        data['Open'] = clean_numeric_column(data['Open'])
        data['High'] = clean_numeric_column(data['High'])
        data['Low'] = clean_numeric_column(data['Low'])
        data['Close'] = clean_numeric_column(data['Close'])
        data['Volume'] = clean_numeric_column(data['Volume'])
        
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

def line_plot(tickers_to_plot):
    
    # Construct the column names with the prefix
    columns_to_plot = [f"{ticker}_Close" for ticker in tickers_to_plot]
    
    # Check if the columns exist in the DataFrame
    missing_columns = [col for col in columns_to_plot if col not in finished_data.columns]
    if missing_columns:
        print(f"Missing columns: {missing_columns}")
        return
    
    # Filter the DataFrame to include only the columns to plot
    data_to_plot = finished_data[columns_to_plot].dropna()
    
    # Plot the selected columns
    data_to_plot.plot(figsize=(14, 7))
    
    # Adjust the legend to display just the tickers
    plt.title('Stock Prices Over Time')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    plt.legend(tickers_to_plot)
    plt.show()

# Call the function with the finished data
line_plot(['RY.TO', 'TD.TO', 'CNQ.TO', 'SHOP.TO']) 