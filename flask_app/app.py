from flask import Flask, render_template, request
import os
import pandas as pd
import time
from scipy.stats import trim_mean


app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDERS = os.path.join(BASE_DIR,'uploads')
os.makedirs(UPLOAD_FOLDERS, exist_ok=True)
pd.set_option("display.max_columns",None)


COLUMN_MAPPING = {
    "Start(W. Central Africa Standard Time)": "start_time",
    "Stop(W. Central Africa Standard Time)": "stop_time",
    "PowerP_Total_avg": "avg_power_kW",
    "PowerP_Total_max":"peak_power_kW",
    "PowerS_Total_max": "peak_apparent_power_kVA",
    "TotalActiveEnergyForward_avg": "Energy_kWh"
}

@app.route('/', methods=['GET', 'POST'])
def home():
    analysis_result = None
    intro=None
    table_result = None
    energy_summary = None
    if request.method == 'POST':
        #Get file from request
        file = request.files['file']
        if file:
            file_path = os.path.join(UPLOAD_FOLDERS, file.filename)
            file.save(file_path)

            if file.filename.endswith(".xls"): 
                df = pd.read_csv(file_path, sep='\t', usecols=COLUMN_MAPPING.keys())
                print(f"{file.filename} uploaded sucessfully!!")
                
            elif file.filename.endswith(".xlsx"):
                df = pd.read_excel(file_path, usecols=COLUMN_MAPPING.keys())
                print(f"{file.filename} uploaded sucessfully!!")
            else:
                ...

            table_result = create_columns(df=df)
            #create_column function will come first, to create the necessary fetures needed
            intro = overview(df=df)

            energy_summary = daily_energy_summary(data=df)

    return render_template('index.html', result=table_result, energy_summary=energy_summary, intro=intro)


def create_columns(df: pd.DataFrame)-> pd.DataFrame:
    #Rename the columns 
    df.rename(columns=COLUMN_MAPPING, inplace=True) 
    #and standardization 
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['stop_time'] = pd.to_datetime(df['stop_time'])
    df['avg_power_kW'] = df['avg_power_kW'] / 1000
    df['peak_power_kW'] = df['peak_power_kW'] / 1000
    df['peak_apparent_power_kVA'] = df['peak_apparent_power_kVA']/1000
    df["Energy_kWh"] = df["Energy_kWh"] / 1000
    df['hour'] = df['stop_time'].dt.hour
    df['day'] = df['stop_time'].dt.day
    
    return df.head().to_html(classes="table table-striped", index=False)

def overview(df: pd.DataFrame)-> str:
    min = df['start_time'].min()
    max = df['start_time'].max()
    delta = max - min
    hours = delta.seconds //3600 #convert the remaing seconds to hours
    # power_factor = 
    avg_power = df['avg_power_kW'].mean()
    peak_power = df['peak_power_kW'].max().round(2)
    text = f"""
    <p>The data was logged for <b>{delta.days} days, {hours} hours</b> spanning from <b>{min.strftime('%a, %d/%b/%Y')}</b> to <b>{max.strftime('%a, %d/%b/%Y')}</b></p>
    
    <p><b>Average power: {avg_power.round(2)} kW</b></p>
    <p><b>Peak power: {peak_power}</b></p>
    <p><b>Total energy for days logged: {df['Energy_kWh'].sum().round(2)} kWh</b></p>
    """
    return text



def daily_energy_summary(data: pd.DataFrame)-> str:
    '''Daily energy sum'''
    daily_sum = data.resample('D', on='start_time')[['Energy_kWh']].sum().round(2).reset_index().set_index('start_time')
    total_sum = round(data['Energy_kWh'].sum(), 2)

    summary_text = f"""
    <h3>SUM OF DAILY ENERGY FOR DAYS LOGGED</h3>
    {daily_sum.to_html(classes="table table-bordered")}
    <p><b>Total energy for days logged: </b>{total_sum} kWh</p>
    """
    return summary_text
    
def night_consumption(df: pd.DataFrame)->pd.DataFrame:
    df.groupby(['day','hour'])
    ...

if __name__ == '__main__':
    app.run(debug=True)