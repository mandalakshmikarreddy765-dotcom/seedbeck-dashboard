import time
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Seebeck Predictive Maintenance Dashboard",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Embedded Seebeck Failure & Degradation Predictor")
st.markdown("Real-time telemetry and edge AI anomaly detection monitor.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Cloud Web Endpoint Settings")

# Default Beeceptor / Cloud URL
endpoint_url = st.sidebar.text_input(
    "Beeceptor Endpoint URL",
    value="https://seebeck-telemetry.free.beeceptor.com/api/data",
)

poll_interval = st.sidebar.slider(
    "Refresh Interval (seconds)", min_value=1, max_value=5, value=2
)
start_btn = st.sidebar.button("Start Live Web Stream", type="primary")
stop_btn = st.sidebar.button("Stop Stream")

# Initialize Session State Data Frame
if "telemetry_data" not in st.session_state:
    st.session_state.telemetry_data = pd.DataFrame(
        columns=["timestamp", "delta_t", "r_int", "s_est", "anomaly"]
    )

# --- DASHBOARD LAYOUT PLACEHOLDERS ---
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
status_placeholder = st.empty()
chart_col1, chart_col2 = st.columns(2)

# --- MAIN MONITORING LOOP ---
if start_btn:
    st.sidebar.success("Listening to Web Telemetry...")

    while True:
        if stop_btn:
            st.sidebar.info("Stream Stopped.")
            break

        try:
            # Fetch latest JSON telemetry from Beeceptor/HTTP Endpoint
            response = requests.get(endpoint_url, timeout=3)

            if response.status_code == 200 and response.text.strip():
                data = response.json()

                # Parse JSON fields
                dT = float(data.get("delta_t", 0.0))
                r_int = float(data.get("r_int", 0.0))
                s_est = float(data.get("s_est", 0.0))
                anomaly = (
                    bool(data.get("anomaly"))
                    if isinstance(data.get("anomaly"), bool)
                    else (str(data.get("anomaly")).lower() == "true")
                )
                timestamp = time.strftime("%H:%M:%S")

                # Store into Session DataFrame
                new_entry = {
                    "timestamp": timestamp,
                    "delta_t": dT,
                    "r_int": r_int,
                    "s_est": s_est,
                    "anomaly": anomaly,
                }
                st.session_state.telemetry_data = pd.concat(
                    [
                        st.session_state.telemetry_data,
                        pd.DataFrame([new_entry]),
                    ],
                    ignore_index=True,
                )

                # Keep last 30 entries for clear trending
                if len(st.session_state.telemetry_data) > 30:
                    st.session_state.telemetry_data = (
                        st.session_state.telemetry_data.iloc[-30:]
                    )

                df = st.session_state.telemetry_data

                # 1. Metric Cards Update
                metric_col1.metric("Temperature Gradient (ΔT)", f"{dT:.1f} °C")
                metric_col2.metric(
                    "Internal Resistance (R_int)", f"{r_int:.2f} Ω"
                )
                metric_col3.metric("Seebeck Coeff (S_est)", f"{s_est:.4f} mV/K")
                metric_col4.metric(
                    "Edge AI Status",
                    "FAULT DETECTED" if anomaly else "HEALTHY",
                    delta_color="inverse" if anomaly else "normal",
                )

                # 2. System Alert Banner
                if anomaly:
                    status_placeholder.error(
                        "🚨 **SYSTEM ANOMALY DETECTED:** Internal resistance degradation or thermal saturation limit reached!"
                    )
                else:
                    status_placeholder.success(
                        "✅ **SYSTEM STATUS NORMAL:** Operating within calibrated physical bounds."
                    )

                # 3. Real-Time Charts
                with chart_col1:
                    fig_r = px.line(
                        df,
                        x="timestamp",
                        y="r_int",
                        title="Internal Resistance Trend (R_int)",
                        markers=True,
                    )
                    fig_r.add_hline(
                        y=3.5,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Threshold (3.5Ω)",
                    )
                    st.plotly_chart(fig_r, use_container_width=True)

                with chart_col2:
                    fig_dt = px.line(
                        df,
                        x="timestamp",
                        y="delta_t",
                        title="Temperature Difference Trend (ΔT)",
                        markers=True,
                    )
                    fig_dt.add_hline(
                        y=10.0,
                        line_dash="dash",
                        line_color="orange",
                        annotation_text="Min ΔT Limit (10°C)",
                    )
                    st.plotly_chart(fig_dt, use_container_width=True)

        except Exception as e:
            status_placeholder.warning(
                "Waiting for incoming web telemetry from Wokwi/Beeceptor..."
            )

        time.sleep(poll_interval)