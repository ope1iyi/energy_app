from flask import Flask, render_template, request, flash, redirect
import os
import pandas as pd



app = Flask(__name__)
app.secret_key = 'Ecowatt'
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
    "TotalActiveEnergyForward_avg": "Energy_kWh",
    "PowerS_Total_avg": "avg_apparent_power_kVA"
}

@app.route('/', methods=['GET', 'POST'])
def home():
    analysis_result = None
    intro=None
    table_result = None
    energy_summary = None
    night_summary = None
    day_summary=None
    if request.method == 'POST':
        #Get file from request
        file = request.files.get('file')
        if not file or file.filename == '':
            flash("No file selected. Please choose .xls or .xlsx")
            return redirect(request.url)
        file_path = os.path.join(UPLOAD_FOLDERS, file.filename)
        file.save(file_path)
        try: 
            if file.filename.endswith(".xls"): 
                    df = pd.read_csv(file_path, sep='\t', usecols=COLUMN_MAPPING.keys())
                    print(f"{file.filename} uploaded successfully!!")
                    
            elif file.filename.endswith(".xlsx"):
                    df = pd.read_excel(file_path, usecols=COLUMN_MAPPING.keys())
                    print(f"{file.filename} uploaded successfully!!")
            else:
                    flash("Unsupported file format. " \
                    "Please upload a .xls or .xls file that has not been worked on")
                    return redirect(request.url)
            table_result = create_columns(df=df)  #create_column function will come first, to create the necessary fetures needed
            intro = overview(df=df)

            energy_summary = daily_energy_summary(data=df)
            night_summary = night_consumption(df=df)
            day_summary = day_consumption(df=df)
        except (ValueError, pd.errors.OutOfBoundsDatetime, KeyError) as e:
                os.remove(file_path)                
                flash('Error: This data is not cleaned.' \
                'it contains incorrect format')
                return redirect(request.url)
        except Exception as e:
                os.remove(file_path)
                app.logger.error(f"Error processing file {file.filename}: {e}")
                flash("An error occurred. Upload a clean exported file")
                return redirect(request.url)
            
    return render_template('index.html', 
                           result=table_result, 
                           energy_summary=energy_summary, 
                           intro=intro, 
                           night_summary=night_summary,
                           day_summary=day_summary
                           )


def create_columns(df: pd.DataFrame)-> pd.DataFrame:
    #Rename the columns 
    df.rename(columns=COLUMN_MAPPING, inplace=True) 
    #and standardization 
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['stop_time'] = pd.to_datetime(df['stop_time'])
    df['avg_power_kW'] = df['avg_power_kW'] / 1000
    df['peak_power_kW'] = df['peak_power_kW'] / 1000
    df['peak_apparent_power_kVA'] = df['peak_apparent_power_kVA']/1000
    df['avg_apparent_power_kVA'] = df['avg_apparent_power_kVA'] / 1000
    df["Energy_kWh"] = df["Energy_kWh"] / 1000
    df['hour'] = df['stop_time'].dt.hour
    df['day'] = df['stop_time'].dt.day
    df['power_factor'] = (df['avg_power_kW'] / df['peak_apparent_power_kVA']).clip(upper=1.0).round(3)
    return df.head().to_html(classes="table table-striped", index=False)

def overview(df: pd.DataFrame)-> str:
    min = df['start_time'].min()
    max = df['start_time'].max()
    delta = max - min
    hours = delta.seconds //3600 #convert the remaing seconds to hours
    # power_factor = 
    avg_power = df['avg_power_kW'].mean()
    peak_power = df['peak_power_kW'].max().round(2)
    total_energy = df['Energy_kWh'].sum().round(2)
    pf           = trimmed_power_factor(df)
    pf_display   = f"{pf:.3f}" if pf == pf else "N/A"

    if pf >= 0.95:
        pf_note, pf_color = "Excellent (≥ 0.95)", "#00c853"
    elif pf >= 0.85:
        pf_note, pf_color = "Acceptable (0.85–0.94)", "#ff9800"
    else:
        pf_note, pf_color = "Poor (< 0.85) — consider correction", "#f44336"


    text = f"""
    <p>The data was logged for <b>{delta.days} days, {hours} hours</b> spanning from <b>{min.strftime('%a, %d/%b/%Y')}</b> to <b>{max.strftime('%a, %d/%b/%Y')}</b></p>
    
    <p><b>Average power: {avg_power.round(2)} kW</b></p>
    <p><b>Peak power: {peak_power} kW</b></p>
    <p><b>Total energy for days logged: {df['Energy_kWh'].sum().round(2)} kWh</b></p>
    <p><b>Total energy for days logged:</b> {total_energy} kWh</p>
    <p><b>Trimmed Power Factor:</b> <span style="color:{pf_color}; font-weight:700;">{pf_display}</span> — {pf_note}</p>
    """
    return text

def daily_power_summary(data: pd.DataFrame)-> str:
    '''Daily energy sum'''
    daily_peak_sum = data.resample('D', on='start_time')[['peak_power_kW']].sum().round(2).reset_index().set_index('start_time')
    daily_avg_sum = data.resample('D', on='start_time')[['avg_power_kW']].sum().round(2).reset_index().set_index('start_time')
    total_sum = round(data['Energy_kWh'].sum(), 2)

    return f"""
    <h3>SUM OF DAILY ENERGY FOR DAYS LOGGED</h3>
    {daily_peak_sum.to_html(classes="table table-bordered")}
    <p><b>Total energy for days logged: </b>{total_sum} kWh</p>
    """


def daily_energy_summary(data: pd.DataFrame)-> str:
    '''Daily energy sum'''
    daily_sum = data.resample('D', on='start_time')[['Energy_kWh']].sum().round(2).reset_index().set_index('start_time')
    total_sum = round(data['Energy_kWh'].sum(), 2)

    return f"""
    <h3>SUM OF DAILY ENERGY FOR DAYS LOGGED</h3>
    {daily_sum.to_html(classes="table table-bordered")}
    <p><b>Total energy for days logged: </b>{total_sum} kWh</p>
    """
    
def night_consumption(df: pd.DataFrame) -> str:
    """Night hours: 18:00 – 05:59"""
    night_mask = (df['hour'] >= 18) | (df['hour'] < 6)
    night_df = df[night_mask]

    night_energy = night_df.groupby('day')[['Energy_kWh']].sum().round(2)
    night_energy.columns = ['Total Energy (kWh)']

    avg_night_energy = round(night_df['Energy_kWh'].sum() / night_df['day'].nunique(), 2)
    total_night_energy = round(night_df['Energy_kWh'].sum(), 2)
    peak_night_power = round(night_df['peak_power_kW'].max(), 2)

    return f"""
    <h3>NIGHT CONSUMPTION (18:00 – 05:59)</h3>
    {night_energy.to_html(classes="table table-bordered")}
    <p><b>Total night energy: </b>{total_night_energy} kWh</p>
    <p><b>Average night energy per day: </b>{avg_night_energy} kWh</p>
    <p><b>Peak night power: </b>{peak_night_power} kW</p>
    """

def day_consumption(df: pd.DataFrame) -> str:
    """Day hours: 06:00 – 17:59"""
    day_mask = (df['hour'] >= 6) & (df['hour'] <= 17)
    day_df = df[day_mask]

    day_energy = day_df.groupby('day')[['Energy_kWh']].sum().round(2)
    day_energy.columns = ['Total Energy (kWh)']

    avg_day_energy = round(day_df['Energy_kWh'].sum() / day_df['day'].nunique(), 2)
    total_day_energy = round(day_df['Energy_kWh'].sum(), 2)
    peak_day_power = round(day_df['peak_power_kW'].max(), 2)

    return f"""
    <h3>DAY CONSUMPTION (06:00 – 17:59)</h3>
    {day_energy.to_html(classes="table table-bordered")}
    <p><b>Total day energy: </b>{total_day_energy} kWh</p>
    <p><b>Average day energy per day: </b>{avg_day_energy} kWh</p>
    <p><b>Peak day power: </b>{peak_day_power} kW</p>
    """

def trimmed_power_factor(df: pd.DataFrame, min_apparent_kva: float = 0.0) -> float:
    """
    Replicate Fluke's trimmed power factor.
    Drops intervals where apparent power < min_apparent_kva (near-zero / idle load)
    to avoid noisy P/S values, then averages the remaining interval PFs.
    """
    active = df[df['peak_apparent_power_kVA'] >= min_apparent_kva].copy()
    if active.empty:
        return float('nan')
    total_kw = active['avg_power_kW'].sum()
    total_kva = active['avg_apparent_power_kVA'].sum()
    
    system_pf = total_kw / total_kva
    return round(min(system_pf, 1.0), 2)

if __name__ == '__main__':
    app.run(debug=True)