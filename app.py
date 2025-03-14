import streamlit as st
import pandas as pd

# Function to process the uploaded file
def process_trades(file, max_drawdown, max_trades, selected_assets):
    df = pd.read_excel(file, sheet_name="Master Playbook ")
    
    # Clean and extract relevant data
    df = df.dropna(how='all').reset_index(drop=True)
    header_row_index = df[df.iloc[:, 0] == 'Asset'].index[0]
    df.columns = df.iloc[header_row_index]
    df = df.iloc[header_row_index + 1:].reset_index(drop=True)
    df = df.rename(columns=lambda x: str(x).strip())
    df = df.dropna(subset=["Profit Factor", "Risk of Ruin", "SL $ Per Trade"]) 
    
    # Convert necessary columns to numeric
    for col in ["Profit Factor", "Risk of Ruin", "SL $ Per Trade", "TP - %", "SL - %"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate max daily loss based on stop loss
    df["Daily Max Loss"] = df["SL $ Per Trade"] * 10  # Assuming 10 contracts
    
    # Apply filters
    df = df[df["Daily Max Loss"] <= max_drawdown]
    if selected_assets:
        df = df[df["Asset"].isin(selected_assets)]
    
    # Select top trades per day based on Risk of Ruin and Profit Factor
    df_sorted = df.sort_values(["Risk of Ruin", "Profit Factor"], ascending=[True, False])
    best_trades = df_sorted.groupby("Day Of Week").head(max_trades)
    
    return best_trades

# Streamlit UI
st.title("Trading Plan Dashboard")

# Upload file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    # Sidebar settings
    max_drawdown = st.sidebar.number_input("Max Daily Drawdown ($)", min_value=500, max_value=5000, value=1000, step=100)
    max_trades = st.sidebar.slider("Max Trades Per Day", min_value=1, max_value=5, value=2)
    
    # Load data to get unique assets
    df_preview = pd.read_excel(uploaded_file, sheet_name="Master Playbook ")
    df_preview = df_preview.dropna(how='all').reset_index(drop=True)
    header_row_index = df_preview[df_preview.iloc[:, 0] == 'Asset'].index[0]
    df_preview.columns = df_preview.iloc[header_row_index]
    df_preview = df_preview.iloc[header_row_index + 1:].reset_index(drop=True)
    df_preview = df_preview.rename(columns=lambda x: str(x).strip())
    assets = df_preview["Asset"].dropna().unique()
    
    selected_assets = st.sidebar.multiselect("Filter by Assets", options=assets, default=list(assets))
    
    # Process the trades
    best_trades = process_trades(uploaded_file, max_drawdown, max_trades, selected_assets)
    
    # Display results as a Trading Plan
    st.write("### Daily Trading Plan")
    for day in best_trades["Day Of Week"].unique():
        st.write(f"#### {day}")
        day_trades = best_trades[best_trades["Day Of Week"] == day]
        for _, trade in day_trades.iterrows():
            st.write(f"- **Asset**: {trade['Asset']}")
            st.write(f"  - **Range**: {trade['Range Start']} - {trade['Range End']}")
            st.write(f"  - **Profit Factor**: {trade['Profit Factor']}")
            st.write(f"  - **Risk of Ruin**: {trade['Risk of Ruin']}")
            st.write(f"  - **TP %**: {trade['TP - %']} | **SL %**: {trade['SL - %']}")
            st.write("---")
    
    # Download option
    csv = best_trades.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "trading_plan.csv", "text/csv")
