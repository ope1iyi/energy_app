import streamlit as st
import pandas as pd
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
        df = pd.read_csv(uploaded_file, sep='\t', usecols=COLUMN_MAPPING.keys())
    else:
        df = pd.read_excel(uploaded_file, usecols=COLUMN_MAPPING.keys())

    df.rename(columns=COLUMN_MAPPING, inplace=True)
    df['start_time']              = pd.to_datetime(df['start_time'])
    df['stop_time']               = pd.to_datetime(df['stop_time'])
    df['avg_power_kW']            = df['avg_power_kW'] / 1000
    df['peak_power_kW']           = df['peak_power_kW'] / 1000
    df['peak_apparent_power_kVA'] = df['peak_apparent_power_kVA'] / 1000
    df['avg_apparent_power_kVA'] = df['avg_apparent_power_kVA'] / 1000
    df['Energy_kWh']              = df['Energy_kWh'] / 1000
    df['hour']                    = df['stop_time'].dt.hour
    df['day']                     = df['stop_time'].dt.day

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
    pf_display   = f"{pf:.3f}" if pf == pf else "N/A"

    st.subheader("📋 Overview")
    st.caption(
        f"Data logged for **{delta.days} days, {hours} hours** — "
        f"from **{start.strftime('%a, %d %b %Y')}** to **{end.strftime('%a, %d %b %Y')}**"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Power",       f"{avg_power} kW")
    col2.metric("Peak Power",          f"{peak_power} kW")
    col3.metric("Total Energy",        f"{total_energy} kWh")
    col4.metric("Trimmed Power Factor", pf_display)

    # PF quality note
    if pf == pf:  # not NaN
        if pf >= 0.95:
            st.success(f"Power factor {pf_display} — Excellent (≥ 0.95)")
        elif pf >= 0.85:
            st.warning(f"Power factor {pf_display} — Acceptable (0.85–0.94)")
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
    """Day hours 06:00–17:59 breakdown."""
    st.subheader("☀️ Day Consumption (06:00 – 17:59)")

    day_df = df[(df['hour'] >= 6) & (df['hour'] <= 17)]

    day_energy = (
        day_df.groupby('day')[['Energy_kWh']]
        .sum().round(2)
        .rename(columns={'Energy_kWh': 'Total Energy (kWh)'})
    )

    total_day = round(day_df['Energy_kWh'].sum(), 2)
    avg_day   = round(total_day / day_df['day'].nunique(), 2) if day_df['day'].nunique() else 0
    peak_day  = round(day_df['peak_power_kW'].max(), 2)
    day_pf    = trimmed_power_factor(day_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Day Energy",        f"{total_day} kWh")
    col2.metric("Avg Day Energy / Day",    f"{avg_day} kWh")
    col3.metric("Peak Day Power",          f"{peak_day} kW")
    col4.metric("Trimmed PF (day)",        f"{day_pf:.3f}" if day_pf == day_pf else "N/A")

    st.dataframe(day_energy, width='stretch')


def show_night_consumption(df: pd.DataFrame):
    """Night hours 18:00–05:59 breakdown."""
    st.subheader("🌙 Night Consumption (18:00 – 05:59)")

    night_df = df[(df['hour'] >= 18) | (df['hour'] < 6)]

    night_energy = (
        night_df.groupby('day')[['Energy_kWh']]
        .sum().round(2)
        .rename(columns={'Energy_kWh': 'Total Energy (kWh)'})
    )

    total_night = round(night_df['Energy_kWh'].sum(), 2)
    avg_night   = round(total_night / night_df['day'].nunique(), 2) if night_df['day'].nunique() else 0
    peak_night  = round(night_df['peak_power_kW'].max(), 2)
    night_pf    = trimmed_power_factor(night_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Night Energy",      f"{total_night} kWh")
    col2.metric("Avg Night Energy / Day",  f"{avg_night} kWh")
    col3.metric("Peak Night Power",        f"{peak_night} kW")
    col4.metric("Trimmed PF (night)",      f"{night_pf:.3f}" if night_pf == night_pf else "N/A")

    st.dataframe(night_energy, width='stretch')

def daily_power_summary(data: pd.DataFrame)-> str:
    '''Daily Power Summary'''
    st.subheader("Peak power, Average power per days logged")
    daily_power = data.resample('D', on='start_time')[['peak_power_kW']].max().round(2).reset_index().set_index('start_time')
    daily_avg_sum = data.resample('D', on='start_time').agg({'avg_power_kW':'mean',
                                                                'peak_power_kW': 'max'})

    max_power = (
        data.resample('15min', on='start_time')[['avg_power_kW']]
        .max()
        .resample('D')
        .max().rename(columns={'avg_power_kW': 'Max Power (kW)'}))
    # max_power[] = max_power[].dt.strftime('%a, %d %b %Y')
    st.dataframe(max_power)
    st.info(f"")

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
    with st.expander("📊 Voltage statistics — selected lines"):
        rows = []
        for label, avg_col, min_col, max_col in chosen_volt:
            rows.append({
                "Line":        label,
                "Avg (V)":     round(df[avg_col].mean(), 2),
                "Min (V)":     round(df[min_col].min(), 2) if min_col in df.columns else "—",
                "Max (V)":     round(df[max_col].max(), 2) if max_col in df.columns else "—",
                "Std Dev (V)": round(df[avg_col].std(), 2),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)


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
        show_voltage_current(df)

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

    except KeyError as e:
        st.error(f"Column not found: {e}. Make sure this is a raw Fluke export file.")
    except Exception as e:
        st.error(f"Error processing file: {e}")