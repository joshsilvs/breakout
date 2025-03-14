import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Function to process the uploaded file
def process_trades(file, max_drawdown, max_trades, selected_assets, min_duration, max_duration):
    df = pd.read_excel(file, sheet_name="Master Playbook ")
    
    # Clean and extract relevant data
    df = df.dropna(how='all').reset_index(drop=True)
    header_row_index = df[df.iloc[:, 0] == 'Asset'].index[0]
    df.columns = df.iloc[header_row_index]
    df = df.iloc[header_row_index + 1:].reset_index(drop=True)
    df = df.rename(columns=lambda x: str(x).strip())
    df = df.dropna(subset=["Profit Factor", "Risk of Ruin", "SL $ Per Trade", "Ave Duration", "Strike Rate", "EV - $"]) 
    
    # Convert necessary columns to numeric
    for col in ["Profit Factor", "Risk of Ruin", "SL $ Per Trade", "TP - %", "SL - %", "Ave Duration", "Strike Rate", "EV - $"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate max daily loss based on stop loss
    df["Daily Max Loss"] = df["SL $ Per Trade"] * 10  # Assuming 10 contracts
    
    # Apply filters
    df_filtered = df[(df["Daily Max Loss"] <= max_drawdown) & (df["Ave Duration"] >= min_duration) & (df["Ave Duration"] <= max_duration)]
    if selected_assets:
        df_filtered = df_filtered[df_filtered["Asset"].isin(selected_assets)]
    
    # Select top trades per day based on Risk of Ruin and Profit Factor
    df_sorted = df_filtered.sort_values(["Risk of Ruin", "Profit Factor"], ascending=[True, False])
    best_trades = df_sorted.groupby("Day Of Week").head(max_trades)
    
    return best_trades, df

# Function to simulate future gains using Monte Carlo
def monte_carlo_simulation(start_balance, trades, strike_rate, ev_per_trade):
    balance = [start_balance]
    for _ in range(trades):
        win = np.random.rand() < (strike_rate / 100)  # Simulating a win based on strike rate
        balance.append(balance[-1] + ev_per_trade if win else balance[-1] - abs(ev_per_trade))
    return balance

# Streamlit UI
st.set_page_config(page_title="Trading Plan Dashboard", layout="wide")
st.title("🚀 Trading Plan Dashboard")

# Upload file
uploaded_file = st.file_uploader("📂 Upload your Excel file", type=["xlsx"])

if uploaded_file:
    # Sidebar settings
    with st.sidebar:
        st.header("🔧 Filters")
        max_drawdown = st.number_input("Max Daily Drawdown ($)", min_value=500, max_value=5000, value=1000, step=100)
        max_trades = st.slider("Max Trades Per Day", min_value=1, max_value=5, value=2)
        min_duration, max_duration = st.slider("Filter by Trade Duration (Minutes)", min_value=1, max_value=300, value=(10, 120))
    
        # Load data to get unique assets
        df_preview = pd.read_excel(uploaded_file, sheet_name="Master Playbook ")
        df_preview = df_preview.dropna(how='all').reset_index(drop=True)
        header_row_index = df_preview[df_preview.iloc[:, 0] == 'Asset'].index[0]
        df_preview.columns = df_preview.iloc[header_row_index]
        df_preview = df_preview.iloc[header_row_index + 1:].reset_index(drop=True)
        df_preview = df_preview.rename(columns=lambda x: str(x).strip())
        assets = df_preview["Asset"].dropna().unique()
    
        selected_assets = st.multiselect("Filter by Assets", options=assets, default=list(assets))
    
    # Process the trades
    best_trades, original_data = process_trades(uploaded_file, max_drawdown, max_trades, selected_assets, min_duration, max_duration)
    
    # Display results as a Trading Plan
    st.write("### 📜 Your Optimized Trading Plan")
    for day in best_trades["Day Of Week"].unique():
        st.subheader(f"📅 {day}")
        day_trades = best_trades[best_trades["Day Of Week"] == day]
        for _, trade in day_trades.iterrows():
            st.markdown(f"""
            - **📊 Asset**: `{trade['Asset']}`
            - **⏳ Range**: `{trade['Range Start']} - {trade['Range End']}`
            - **🕒 Average Duration**: `{trade['Ave Duration']:.2f} min`
            - **📈 Profit Factor**: `{trade['Profit Factor']:.2f}`
            - **⚖️ Risk of Ruin**: `{trade['Risk of Ruin']:.6f}`
            - **🎯 TP %**: `{trade['TP - %']:.2f}` | **🛑 SL %**: `{trade['SL - %']:.2f}`
            ---
            """)
    
    # Monte Carlo Simulation Graph
    st.write("### 📊 Future Gain Prediction")
    trades_to_simulate = st.slider("Number of Future Trades to Simulate", min_value=50, max_value=1000, value=200)
    start_balance = st.number_input("Starting Balance ($)", min_value=1000, max_value=50000, value=10000, step=1000)
    avg_ev = best_trades["EV - $"].mean()
    avg_sr = best_trades["Strike Rate"].mean()
    
    if not np.isnan(avg_ev) and not np.isnan(avg_sr):
        simulation_results = monte_carlo_simulation(start_balance, trades_to_simulate, avg_sr, avg_ev)
        df_simulation = pd.DataFrame({"Trades": list(range(trades_to_simulate + 1)), "Balance": simulation_results})
        fig = px.line(df_simulation, x="Trades", y="Balance", title="Projected Account Growth Over Time")
        st.plotly_chart(fig, use_container_width=True)
    
    # Download option
    csv = best_trades.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download Trading Plan as CSV", csv, "trading_plan.csv", "text/csv")
    
    # Display the full dataset for reference
    st.write("### 🔍 Full Trade Dataset (Before Filtering)")
    st.dataframe(original_data, use_container_width=True)
