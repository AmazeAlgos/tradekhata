import streamlit as st
import pandas as pd


def calculate_net(row):
    if row['Net Quantity'] == 0:
        return row['Total Buy Quantity'] * row['Average Buy Price']
    elif row['Net Quantity'] > 0:
        return row['Total Sell Quantity'] * row['Average Buy Price']
    else:
        return 0

def process_data(df):
    print(df)
    buy_data = df[df['Trade Type'] == 'buy']
    total_buy_qty = buy_data.groupby('Symbol')['Quantity'].sum()
    total_buy_value = (buy_data['Quantity'] * buy_data['Price']).groupby(buy_data['Symbol']).sum()

    # Calculate total sell quantity and total sell value for each symbol
    sell_data = df[df['Trade Type'] == 'sell']
    total_sell_qty = sell_data.groupby('Symbol')['Quantity'].sum()
    total_sell_value = (sell_data['Quantity'] * sell_data['Price']).groupby(sell_data['Symbol']).sum()

    # Calculate average buy and sell prices
    average_buy_price = total_buy_value / total_buy_qty
    average_sell_price = total_sell_value / total_sell_qty

    # Create a DataFrame for the result
    df = pd.DataFrame({
        'Symbol': df['Symbol'].unique(),
        'Exchange': df.groupby('Symbol')['Exchange'].first(),
        'Total Buy Quantity': total_buy_qty.reindex(df['Symbol'].unique(), fill_value=0).values,
        'Average Buy Price': average_buy_price.reindex(df['Symbol'].unique(), fill_value=0).values,
        'Total Sell Quantity': total_sell_qty.reindex(df['Symbol'].unique(), fill_value=0).values,
        'Average Sell Price': average_sell_price.reindex(df['Symbol'].unique(), fill_value=0).values,

    })
    df['Net Quantity']=df['Total Buy Quantity']-df['Total Sell Quantity']
    df['Buy Value'] = df.apply(calculate_net, axis=1)

    df['PNL'] = 0  # Initialize PNL column with zeros
    buy_price_zero_mask = df['Average Buy Price'] == 0
    negative_net_quantity_mask = df['Net Quantity'] < 0

    # Set PNL as 0 where Average Buy Price is 0 or Net Quantity is negative
    df.loc[buy_price_zero_mask | negative_net_quantity_mask, 'PNL'] = 0

    # Calculate PNL where conditions are not met
    positive_net_quantity_mask = ~negative_net_quantity_mask
    valid_buy_price_mask = ~buy_price_zero_mask
    valid_sell_price_mask = df['Average Sell Price'] != 0

    valid_rows_mask = positive_net_quantity_mask & valid_buy_price_mask & valid_sell_price_mask
    df.loc[valid_rows_mask, 'PNL'] = (df.loc[valid_rows_mask, 'Average Sell Price'] - df.loc[valid_rows_mask, 'Average Buy Price']) * df.loc[valid_rows_mask, 'Total Sell Quantity']
    df['ROI'] = df['PNL'] / df['Buy Value']
    df.loc[(df['Buy Value'] == 0) | (df['PNL'] == 0), 'ROI'] = 0

    df['Status'] = 'Data Missing'  # Initialize the column with 'Data Missing'

    # Set status as 'Closed' when net value column is 0
    df.loc[df['Net Quantity'] == 0, 'Status'] = 'Closed'

    # Set status as 'Holding' when net value column is greater than 0
    df.loc[df['Net Quantity'] > 0, 'Status'] = 'Holding'

    # Set status as 'Partial Exit' when both Sell Quantity and Net Quantity are greater than 0
    partial_exit_mask = (df['Total Sell Quantity'] > 0) & (df['Net Quantity'] > 0)
    df.loc[partial_exit_mask, 'Status'] = 'Partial Exit'
    df_all=df
    # df = df_all[df_all['Exchange']=='NSE']
    df = df[df['Status'] != 'Data Missing']
    wins = len(df[df['PNL'] > 0])
    losses = len(df[df['PNL'] < 0])
    total=wins+losses
    win_pct=wins*100/total
    loss_pct=losses*100/total
    total_win = df.loc[df['PNL'] > 0, 'PNL'].sum()
    total_loss = df.loc[df['PNL'] < 0, 'PNL'].sum()

    max_pnl = df['PNL'].max()
    min_pnl = df['PNL'].min()
    max_pnl_symbol = df.loc[df['PNL'].idxmax(), 'Symbol']
    min_pnl_symbol = df.loc[df['PNL'].idxmin(), 'Symbol']


    # Format the report
    report = f"""
    Key Metrics:
    - Wins: {wins:.2f}
    - losses: {losses:.2f}
    - Win %: {win_pct:.2f}
    - Loss %: {loss_pct:.2f}
    - Total Win: {total_win:.2f}
    - Total Loss: {total_loss:.2f}
    - Max PNL: {max_pnl}
    - ROI: {df['ROI'].mean()*100}
    - Min PNL: {min_pnl}
    - Symbol with Max PNL: {max_pnl_symbol}
    - Symbol with Min PNL: {min_pnl_symbol}
    """

    return report


def main():
    st.title('Trade Log Analysis')


    # File upload
    uploaded_file = st.file_uploader('Upload a file', type=['csv', 'xlsx'])

    if uploaded_file is not None:
        # Read the file
        if uploaded_file.type == 'text/csv':
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            # df = pd.read_excel(uploaded_file, skiprows=lambda x: x == 0 or pd.isnull(x))
            header_row = None
            for i, row in enumerate(pd.read_excel(uploaded_file, header=None).values):
                if not all(pd.isnull(cell) for cell in row):
                    header_row = i
                    break
            df = pd.read_excel(uploaded_file, header=header_row)
        # Drop rows with all NaN values
        df.dropna(axis=0, how='all', inplace=True)
        # Process the data
        processed_data = process_data(df)

        # Show the processed data
        st.subheader('Processed Data')
        st.write(processed_data)

if __name__ == '__main__':
    main()
