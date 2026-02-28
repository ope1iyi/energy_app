import streamlit as st
import pandas as pd

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
    "PowerS_Total_avg": "avg_apparent_power_kVA"

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
    df['power_factor']            = (df['avg_power_kW'] / df['peak_apparent_power_kVA']).clip(upper=1.0)

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
    return round(min(system_pf, 1.0), 3)

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

    st.dataframe(daily_sum, use_container_width=True, hide_index=True)
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

    st.dataframe(day_energy, use_container_width=True)


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

    st.dataframe(night_energy, use_container_width=True)


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
            st.dataframe(df.head(), use_container_width=True)

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