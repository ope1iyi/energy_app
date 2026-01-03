import streamlit as st
import pandas as pd
# import plotly.express as px

COLUMN_MAPPING = {
    "Start(W. Central Africa Standard Time)": "start_time",
    "Stop(W. Central Africa Standard Time)": "stop_time",
    "PowerP_Total_avg": "avg_power_kW",
    "PowerP_Total_max":"peak_power_kW",
    "PowerS_Total_max": "peak_apparent_power_kVA",
    "TotalActiveEnergyForward_avg": "Energy_kWh"
}

st.title("Energy Insight Pro")
st.write("## Welcome")
uploaded_file = st.file_uploader("Upload your fluke excel file", type=["xls", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".xls"):
        df = pd.read_csv(uploaded_file, sep='\t', usecols=COLUMN_MAPPING.keys())
        st.write(f"Data uploaded successfully with {df.shape[0]} rows and {df.shape[1]} columns")
        
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, usecols=COLUMN_MAPPING.keys())
        st.write(f"Data uploaded successfully with {df.shape[0]} rows and {df.shape[1]} columns")

    df.rename(columns=COLUMN_MAPPING, inplace=True)
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['stop_time'] = pd.to_datetime(df['stop_time'])
    df['avg_power_kW'] = df['avg_power_kW'] / 1000
    df['peak_power_kW'] = df['peak_power_kW'] / 1000
    df['peak_apparent_power_kVA'] = df['peak_apparent_power_kVA']/1000
    df["Energy_kWh"] = df["Energy_kWh"] / 1000

    st.write(df.head())

    #Show summary stats
    st.write("## Summary Statistics")
    st.write("Power summary")
    st.write(df.resample('D', on='start_time')[['peak_power_kW', 'avg_power_kW','peak_apparent_power_kVA']].max())

    st.write("Energy summary")
    st.write(df.resample('D', on='start_time')[['Energy_kWh']].sum())
    st.write(f"Total energy consumed for days logged is {round(df['Energy_kWh'].sum(),2)} kWh")
    st.write(f"Average energy consumed daily is {round(df['Energy_kWh'].mean(),2)}")  
    