import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Energy Insight Pro", page_icon="⚡", layout="wide")

# ── Column mapping ─────────────────────────────────────────────────────────────
COLUMN_MAPPING = {
    "Start(W. Central Africa Standard Time)": "start_time",
    "Stop(W. Central Africa Standard Time)": "stop_time",
    "PowerP_Total_avg": "avg_power_kW",
    "PowerP_Total_max": "peak_power_kW",
    "PowerS_Total_max": "peak_apparent_power_kVA",
    "TotalActiveEnergyForward_avg": "Energy_kWh",
    "PowerS_Total_avg": "avg_apparent_power_kVA",
    # Phase-to-neutral voltages
    "Vrms_AN_avg": "V_AN_avg", "Vrms_AN_min": "V_AN_min", "Vrms_AN_max": "V_AN_max",
    "Vrms_BN_avg": "V_BN_avg", "Vrms_BN_min": "V_BN_min", "Vrms_BN_max": "V_BN_max",
    "Vrms_CN_avg": "V_CN_avg", "Vrms_CN_min": "V_CN_min", "Vrms_CN_max": "V_CN_max",
    # Line-to-line voltages
    "Vrms_AB_avg": "V_AB_avg", "Vrms_AB_min": "V_AB_min", "Vrms_AB_max": "V_AB_max",
    "Vrms_BC_avg": "V_BC_avg", "Vrms_BC_min": "V_BC_min", "Vrms_BC_max": "V_BC_max",
    "Vrms_CA_avg": "V_CA_avg", "Vrms_CA_min": "V_CA_min", "Vrms_CA_max": "V_CA_max",
    # Phase currents
    "Irms_A_avg": "I_A_avg", "Irms_A_min": "I_A_min", "Irms_A_max": "I_A_max",
    "Irms_B_avg": "I_B_avg", "Irms_B_min": "I_B_min", "Irms_B_max": "I_B_max",
    "Irms_C_avg": "I_C_avg", "Irms_C_min": "I_C_min", "Irms_C_max": "I_C_max",
}


# ── Data loading & preparation ─────────────────────────────────────────────────

def load_and_prepare(uploaded_file) -> pd.DataFrame:
    """Read file, rename columns, convert units, add helper columns."""
    if uploaded_file.name.endswith(".xls"):
        try:
            df = pd.read_csv(uploaded_file, sep='\t', usecols=COLUMN_MAPPING.keys())
        except Exception as e:
            st.warning(f"Encountered an error with the columns, upload an excel file from fluke")
    elif uploaded_file.name.endswith(".xlsx"):
        try:
            df = pd.read_excel(uploaded_file, usecols=COLUMN_MAPPING.keys())
        except Exception as e:
            return st.error(f"Encountered an error with the columns.\
                     Ensure this is a raw Fluke export excel file")
    else:
        st.warning("Upload a fluke file, please")

    df.rename(columns=COLUMN_MAPPING, inplace=True)
    df['start_time']              = pd.to_datetime(df['start_time'])
    df['stop_time']               = pd.to_datetime(df['stop_time'])
    df['avg_power_kW']            = df['avg_power_kW'] / 1000
    df['peak_power_kW']           = df['peak_power_kW'] / 1000
    df['peak_apparent_power_kVA'] = df['peak_apparent_power_kVA'] / 1000
    df['avg_apparent_power_kVA'] = df['avg_apparent_power_kVA'] / 1000
    df['Energy_kWh']              = df['Energy_kWh'] / 1000
    df['hour']                    = df['stop_time'].dt.time
    df['date']                    = df['stop_time'].dt.normalize()  # full date, not just day-of-month

    return df

# ── Power factor ───────────────────────────────────────────────────────────────

def trimmed_power_factor(df: pd.DataFrame, min_apparent_kva: float = 0.5) -> float:
    """
    Replicate Fluke's trimmed power factor.
    Excludes intervals where apparent power < min_apparent_kva (near-zero load)
    to avoid noisy P/S ratios, then averages the remaining interval PFs.
    """
    active = df[df['peak_apparent_power_kVA'] >= min_apparent_kva].copy()
    if active.empty:
        return float('nan')
    
    total_kw = active['avg_power_kW'].sum()
    total_kva = active['avg_apparent_power_kVA'].sum()
    
    system_pf = total_kw / total_kva
    return round(min(system_pf, 1.0), 2)

# ── Section renderers ──────────────────────────────────────────────────────────

def show_overview(df: pd.DataFrame):
    """Logged period summary with st.metric cards."""
    start  = df['start_time'].min()
    end    = df['start_time'].max()
    delta  = end - start
    hours  = delta.seconds // 3600

    avg_power    = round(df['avg_power_kW'].mean(), 2)
    peak_power   = round(df['peak_power_kW'].max(), 2)
    total_energy = round(df['Energy_kWh'].sum(), 2)
    pf           = trimmed_power_factor(df)
    pf_display   = f"{pf:.2f}" if pf == pf else "N/A"

    st.subheader("📋 Overview")
    st.caption(
        f"Data logged for **{delta.days} days, {hours} hours** — "
        f"from **{start.strftime('%a, %d %b %Y')}** to **{end.strftime('%a, %d %b %Y')}**"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Active Power",       f"{avg_power} kW")
    col2.metric("Peak Active Power",          f"{peak_power} kW")
    col3.metric("Total Energy",        f"{total_energy} kWh")
    col4.metric("Trimmed Power Factor", pf_display)

    # PF quality note
    if pf == pf:  # not NaN
        if pf >= 0.95:
            st.success(f"Power factor {pf_display} — Excellent (≥ 0.95)")
        elif pf >= 0.85:
            st.warning(f"Power factor {pf_display} — Acceptable (0.85-0.94)")
        else:
            st.error(f"Power factor {pf_display} — Poor (< 0.85), consider correction")


def show_daily_energy_summary(df: pd.DataFrame):
    """Daily energy totals table."""
    st.subheader("⚡ Daily Energy Summary")

    daily_sum = (
        df.resample('D', on='start_time')[['Energy_kWh']]
        .sum().round(2)
        .reset_index()
        .rename(columns={'start_time': 'Date', 'Energy_kWh': 'Total Energy (kWh)'})
    )
    daily_sum['Date'] = daily_sum['Date'].dt.strftime('%a, %d %b %Y')

    st.dataframe(daily_sum, width='stretch', hide_index=True)
    st.info(f"**Total energy for days logged:** {round(df['Energy_kWh'].sum(), 2)} kWh")


def show_day_consumption(df: pd.DataFrame):
    """Day hours 09:00-17:00 breakdown."""
    st.subheader("☀️ Day Consumption (09:00 – 17:00)")

    day_df = df[(df['hour'] >= dt.time(9,0,0)) & (df['hour'] <= dt.time(17,0,0))]

    day_energy = (
        day_df.groupby('date')[['Energy_kWh']]
        .sum().round(2)
        .rename(columns={'Energy_kWh': 'Total Energy (kWh)'})
        .reset_index()
        .sort_values('date')
        .rename(columns={'date': 'Date'})
    )
    day_energy['Date'] = day_energy['Date'].dt.strftime('%a, %d %b %Y')

    total_day = round(day_df['Energy_kWh'].sum(), 2)
    avg_day   = round(total_day / day_df['date'].nunique(), 2) if day_df['date'].nunique() else 0
    peak_day  = round(day_df['peak_power_kW'].max(), 2)
    day_pf    = trimmed_power_factor(day_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Day Energy",        f"{total_day} kWh")
    col2.metric("Avg Day Energy / Day",    f"{avg_day} kWh")
    col3.metric("Peak Day Power",          f"{peak_day} kW")
    col4.metric("Trimmed PF (day)",        f"{day_pf:.3f}" if day_pf == day_pf else "N/A")

    st.dataframe(day_energy, width='stretch')


def show_night_consumption(df: pd.DataFrame):
    """Night hours 18:00-05:59 breakdown."""
    st.subheader("🌙 Night Consumption (18:00 - 05:59 next day)")

    night_df = df[(df['hour'] >= dt.time(18,0,0)) | (df['hour'] < dt.time(6,0,0))].copy()

    early_morning = night_df['hour'] < dt.time(6, 0, 0)
    night_df['night_date'] = night_df['date']
    night_df.loc[early_morning, 'night_date'] = night_df.loc[early_morning, 'date'] - pd.Timedelta(days=1)

    night_energy = (
        night_df.groupby('night_date')[['Energy_kWh']]
        .sum().round(2)
        .rename(columns={'Energy_kWh': 'Total Energy (kWh)'})
        .reset_index()
        .sort_values('night_date')
        .rename(columns={'night_date': 'Date'})
    )
    night_energy['Date'] = night_energy['Date'].dt.strftime('%a, %d %b %Y')

    total_night = round(night_df['Energy_kWh'].sum(), 2)
    avg_night   = round(total_night / night_df['date'].nunique(), 2) if night_df['date'].nunique() else 0
    peak_night  = round(night_df['peak_power_kW'].max(), 2)
    night_pf    = trimmed_power_factor(night_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Night Energy",      f"{total_night} kWh")
    col2.metric("Avg Night Energy / Day",  f"{avg_night} kWh")
    col3.metric("Peak Night Power",        f"{peak_night} kW")
    col4.metric("Trimmed PF (night)",      f"{night_pf:.3f}" if night_pf == night_pf else "N/A")

    st.dataframe(night_energy, width='stretch')

def daily_power_summary(data: pd.DataFrame):    
    """Daily power summary: max 15-min demand, average power, and peak apparent power per day."""
    st.subheader("📊 Daily Power Summary")

    power_15min = (
        data.set_index('stop_time')['peak_power_kW']
        .rolling(window='15min')
        .mean()
        .rename('max_15min_kW')
    )
  
    max_power_daily = (
        power_15min.resample('D')
        .max()
        .rename('Max 15-min Power (kW)')
    )

    daily_rest = (
        data.resample('D', on='stop_time')
        .agg(
            avg_power_kW            = ('avg_power_kW',  'mean'),
            peak_power_kVA          = ('peak_apparent_power_kVA', 'max'),
            peak_power_kW           = ('peak_power_kW',  'max')
        )
        .round(2)
    )

    summary = (
        daily_rest
        .join(max_power_daily)
        .round(2)
        .reset_index()
        .rename(columns={
            'stop_time':      'Date',
            'avg_power_kW':   'Avg Power (kW)',
            'peak_power_kW':  'Peak Power (kW)',
            'peak_power_kVA': 'Peak Power (kVA)'
        })
        [['Date', 'Max 15-min Power (kW)', 'Avg Power (kW)', 'Peak Power (kW)', 'Peak Power (kVA)']]
    )
    summary['Date'] = summary['Date'].dt.strftime('%a, %d %b %Y')

    st.dataframe(summary, width='stretch', hide_index=True)

    overall_max = round(max_power_daily.max(), 2)
    overall_avg = round(data['avg_power_kW'].mean(), 2)
    st.info(
        f"Overall max 15-min demand: **{overall_max} kW** &nbsp;|&nbsp; "
        f"Overall average power: **{overall_avg} kW**"
    )
def show_voltage_current(df: pd.DataFrame):
    """Interactive voltage and current charts — user picks which lines to plot."""
    st.subheader("🔌 Voltage & Current Profile")

    # ── All available lines ───────────────────────────────────────────────────
    ALL_VOLTAGE_LINES = [
        ("Phase A-N", "V_AN_avg", "V_AN_min", "V_AN_max"),
        ("Phase B-N", "V_BN_avg", "V_BN_min", "V_BN_max"),
        ("Phase C-N", "V_CN_avg", "V_CN_min", "V_CN_max"),
        ("Line A-B",  "V_AB_avg", "V_AB_min", "V_AB_max"),
        ("Line B-C",  "V_BC_avg", "V_BC_min", "V_BC_max"),
        ("Line C-A",  "V_CA_avg", "V_CA_min", "V_CA_max"),
    ]
    ALL_CURRENT_LINES = [
        ("Phase A", "I_A_avg", "I_A_min", "I_A_max"),
        ("Phase B", "I_B_avg", "I_B_min", "I_B_max"),
        ("Phase C", "I_C_avg", "I_C_min", "I_C_max"),
    ]

    # Only show lines that exist in the uploaded file
    avail_volt    = [t for t in ALL_VOLTAGE_LINES  if t[1] in df.columns]
    avail_current = [t for t in ALL_CURRENT_LINES  if t[1] in df.columns]

    # ── User selection ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        volt_labels = [t[0] for t in avail_volt]
        selected_volt = st.multiselect(
            "Voltage lines to plot",
            options=volt_labels,
            default=volt_labels[:3],   # default to phase-to-neutral
            help="Select one or more voltage lines to display on the chart"
        )

    with col2:
        curr_labels = [t[0] for t in avail_current]
        selected_curr = st.multiselect(
            "Current lines to plot",
            options=curr_labels,
            default=curr_labels,
            help="Select one or more current phases to display on the chart"
        )

    with col3:
        show_bands = st.checkbox("Show min/max bands", value=True)
        nominal = st.number_input(
            "Nominal voltage (V)",
            min_value=0, value=230, step=5,
            help="Draws a reference line and ±6% EN50160 tolerance band"
        )

    if not selected_volt:
        st.info("Select at least one voltage line above to plot the chart.")
        return

    # Map selected labels back to their column tuples
    volt_lookup = {t[0]: t for t in avail_volt}
    curr_lookup  = {t[0]: t for t in avail_current}
    chosen_volt  = [volt_lookup[l] for l in selected_volt]
    chosen_curr  = [curr_lookup[l] for l in selected_curr]

    # Assign a consistent color per line regardless of selection order
    PALETTE = ["#00e5a0", "#4d8eff", "#ffb347", "#ff5c8a", "#b388ff", "#40c4ff"]
    all_labels  = [t[0] for t in avail_volt] + [t[0] for t in avail_current]
    color_map   = {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(all_labels)}

    # ── Voltage chart ─────────────────────────────────────────────────────────
    fig_v = go.Figure()

    for (label, avg_col, min_col, max_col) in chosen_volt:
        color = color_map[label]

        if show_bands and min_col in df.columns and max_col in df.columns:
            fig_v.add_trace(go.Scatter(
                x=pd.concat([df['start_time'], df['start_time'][::-1]]),
                y=pd.concat([df[max_col], df[min_col][::-1]]),
                fill='toself',
                fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12)",
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip',
            ))

        fig_v.add_trace(go.Scatter(
            x=df['start_time'],
            y=df[avg_col],
            name=label,
            line=dict(color=color, width=1.5),
            hovertemplate=f"<b>{label}</b><br>%{{x|%d %b %H:%M}}<br>%{{y:.1f}} V<extra></extra>",
        ))

    if nominal > 0:
        fig_v.add_hline(
            y=nominal,
            line_dash="dash",
            line_color="rgba(255,255,255,0.3)",
            annotation_text=f"Nominal {nominal}V",
            annotation_position="bottom right",
        )
        fig_v.add_hrect(
            y0=nominal * 0.94, y1=nominal * 1.06,
            fillcolor="rgba(255,255,255,0.03)",
            line_width=0,
            annotation_text="±6% tolerance",
            annotation_position="top left",
        )

    fig_v.update_layout(
        title=f"Voltage over Time — {', '.join(selected_volt)}",
        xaxis_title="Time", yaxis_title="Voltage (V)",
        paper_bgcolor="#0d0f14", plot_bgcolor="#151820",
        font=dict(color="#e8ecf4"), legend=dict(bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified", height=420,
        margin=dict(t=40, b=40, l=60, r=20),
    )
    fig_v.update_xaxes(gridcolor="#2a2f42")
    fig_v.update_yaxes(gridcolor="#2a2f42")
    st.plotly_chart(fig_v, width='stretch')

    # ── Current chart ─────────────────────────────────────────────────────────
    if chosen_curr:
        fig_i = go.Figure()

        for (label, avg_col, min_col, max_col) in chosen_curr:
            color = color_map[label]

            if show_bands and min_col in df.columns and max_col in df.columns:
                fig_i.add_trace(go.Scatter(
                    x=pd.concat([df['start_time'], df['start_time'][::-1]]),
                    y=pd.concat([df[max_col], df[min_col][::-1]]),
                    fill='toself',
                    fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12)",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip',
                ))

            fig_i.add_trace(go.Scatter(
                x=df['start_time'],
                y=df[avg_col],
                name=label,
                line=dict(color=color, width=1.5),
                hovertemplate=f"<b>{label}</b><br>%{{x|%d %b %H:%M}}<br>%{{y:.2f}} A<extra></extra>",
            ))

        fig_i.update_layout(
            title=f"Current over Time — {', '.join(selected_curr)}",
            xaxis_title="Time", yaxis_title="Current (A)",
            paper_bgcolor="#0d0f14", plot_bgcolor="#151820",
            font=dict(color="#e8ecf4"), legend=dict(bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified", height=420,
            margin=dict(t=40, b=40, l=60, r=20),
        )
        fig_i.update_xaxes(gridcolor="#2a2f42")
        fig_i.update_yaxes(gridcolor="#2a2f42")
        st.plotly_chart(fig_i, width='stretch')

    # ── Voltage stats for selected lines only ─────────────────────────────────
    with st.expander("📊 Voltage & Current statistics — selected lines", expanded=True):

        # Voltage rows: Avg, Min, Max, Avg-of-Max, Std Dev
        volt_rows = []
        for label, avg_col, min_col, max_col in chosen_volt:
            volt_rows.append({
                "Line":           label,
                "Avg V":          round(df[avg_col].mean(), 2)          if avg_col in df.columns else None,
                "Min V":          round(df[min_col].min(), 2)           if min_col in df.columns else None,
                "Max V":          round(df[max_col].max(), 2)           if max_col in df.columns else None,
                # "Avg of Max V":   round(df[max_col].mean(), 2)          if max_col in df.columns else None,
                "Std Dev V":      round(df[avg_col].std(), 2)           if avg_col in df.columns else None,
            })

        if volt_rows:
            st.markdown("**Voltage statistics**")
            st.dataframe(pd.DataFrame(volt_rows), width='stretch', hide_index=True)

        # Current rows: Avg, Min, Max — highlight row with lowest Max current
        ALL_CURRENT_LINES_STAT = [
            ("Phase A", "I_A_avg", "I_A_min", "I_A_max"),
            ("Phase B", "I_B_avg", "I_B_min", "I_B_max"),
            ("Phase C", "I_C_avg", "I_C_min", "I_C_max"),
        ]
        curr_rows = []
        for label, avg_col, min_col, max_col in ALL_CURRENT_LINES_STAT:
            if avg_col not in df.columns:
                continue
            curr_rows.append({
                "Phase":      label,
                "Avg (A)":    round(df[avg_col].mean(), 2),
                "Min (A)":    round(df[min_col].min(), 2) if min_col in df.columns else None,
                "Max (A)":    round(df[max_col].max(), 2) if max_col in df.columns else None,
                "Avg of Max (A)": round(df[max_col].mean(), 2) if max_col in df.columns else None,
            })

        if curr_rows:
            st.markdown("**Current statistics** *(row with lowest Max current highlighted)*")
            curr_df = pd.DataFrame(curr_rows)

            # Find the phase with the lowest Max (A)
            min_max_idx = curr_df["Max (A)"].idxmin()

            def highlight_lowest_max(row):
                if row.name == min_max_idx:
                    return ["background-color: rgba(255,92,138,0.25); color: #ff5c8a; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.dataframe(
                curr_df.style.apply(highlight_lowest_max, axis=1),
                width='stretch',
                hide_index=True,
            )

def show_avg_power(df: pd.DataFrame):
    """Plot average power (avg_power_kW) over time with daily peak markers."""
    st.subheader("⚡ Average Power over Time")

    if 'avg_power_kW' not in df.columns:
        st.warning("avg_power_kW column not found in data.")
        return

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        show_peak = st.checkbox("Mark daily peak", value=True,
                                help="Highlights the highest power reading each day")
    with col2:
        show_rolling = st.checkbox("Show 1-hour rolling average", value=False,
                                   help="Smooths out short spikes to show the trend")

    # ── Build chart ───────────────────────────────────────────────────────────
    fig = go.Figure()

    # Main avg power line
    fig.add_trace(go.Scatter(
        x=df['start_time'],
        y=df['avg_power_kW'],
        name='Avg Power',
        line=dict(color="#00e5a0", width=1.5),
        hovertemplate="<b>Avg Power</b><br>%{x|%d %b %H:%M}<br>%{y:.2f} kW<extra></extra>",
    ))

    # Optional 1-hour rolling average (window = 4 × 15-min intervals)
    if show_rolling:
        rolling = df.set_index('start_time')['avg_power_kW'].rolling('1h').mean().reset_index()
        fig.add_trace(go.Scatter(
            x=rolling['start_time'],
            y=rolling['avg_power_kW'],
            name='1-hr Rolling Avg',
            line=dict(color="#ffb347", width=2, dash='dot'),
            hovertemplate="<b>1-hr Avg</b><br>%{x|%d %b %H:%M}<br>%{y:.2f} kW<extra></extra>",
        ))

    # Daily peak markers
    if show_peak:
        daily_peaks = (
            df.groupby(df['start_time'].dt.date)
            .apply(lambda g: g.loc[g['avg_power_kW'].idxmax()])
            .reset_index(drop=True)
        )
        fig.add_trace(go.Scatter(
            x=daily_peaks['start_time'],
            y=daily_peaks['avg_power_kW'],
            mode='markers',
            name='Daily Peak',
            marker=dict(color="#ff5c8a", size=9, symbol='diamond',
                        line=dict(color='white', width=1)),
            hovertemplate="<b>Daily Peak</b><br>%{x|%d %b %H:%M}<br>%{y:.2f} kW<extra></extra>",
        ))

    overall_avg = round(df['avg_power_kW'].mean(), 2)
    fig.add_hline(
        y=overall_avg,
        line_dash="dash",
        line_color="rgba(255,255,255,0.25)",
        annotation_text=f"Overall avg {overall_avg} kW",
        annotation_position="bottom right",
    )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Power (kW)",
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#151820",
        font=dict(color="#e8ecf4"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        height=420,
        margin=dict(t=20, b=40, l=60, r=20),
    )
    fig.update_xaxes(gridcolor="#2a2f42")
    fig.update_yaxes(gridcolor="#2a2f42")
    st.plotly_chart(fig, width='stretch')

    # ── Stats row ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Avg Power",  f"{overall_avg} kW")
    c2.metric("Max Avg Power",     f"{round(df['avg_power_kW'].max(), 2)} kW")
    c3.metric("Min Power",          f"{round(df['avg_power_kW'].min(), 2)} kW")
    c4.metric("Std Dev",            f"{round(df['avg_power_kW'].std(), 2)} kW")

# ── Main app ───────────────────────────────────────────────────────────────────

st.title("⚡ Energy Insight Pro")

uploaded_file = st.file_uploader(
    "Upload your Fluke export file",
    type=["xls", "xlsx"],
    help="Upload a raw .xls or .xlsx file exported directly from the Fluke logger"
)

if uploaded_file:
    try:
        df = load_and_prepare(uploaded_file)
        st.success(f"Loaded **{df.shape[0]} rows** from `{uploaded_file.name}`")

        st.markdown("---")
        show_overview(df)

        st.markdown("---")
        with st.expander("🔍 First 5 rows of processed data", expanded=False):
            st.dataframe(df.head())

        st.markdown("---")
        daily_power_summary(df)

        st.markdown("---")
        show_daily_energy_summary(df)

        st.markdown("---")
        show_day_consumption(df)

        st.markdown("---")
        show_night_consumption(df)
        
        st.markdown("---")
        show_voltage_current(df)

        st.markdown("---")
        show_avg_power(df)

    except KeyError as e:
        st.error(f"Column not found: {e}. Make sure this is a raw Fluke export file.")
    except Exception as e:
        st.error(f"Error processing file")