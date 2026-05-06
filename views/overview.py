"""views/overview.py — Overview page."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
# from analytics_engine import PatientFlowMonitor  # type: ignore

from views.helpers import (
    synth_snapshot, synth_monthly_trend, synth_er_heatmap, synth_capacity_alerts,
    choropleth, BLUE, TEAL, GREEN, AMBER, RED, TEXT, TEXT2, TEXT3, NAVY, GRID, BORDER,
)

try:
    from analytics_engine import PatientFlowMonitor, ERWaitPredictor
    ENGINE_OK = True
except Exception:
    ENGINE_OK = False

def _snap():
    if ENGINE_OK:
        try:
            r = PatientFlowMonitor().realtime_snapshot()
            if r: return r, False
        except: pass
    return synth_snapshot(), True

def _trend():
    if ENGINE_OK:
        try:
            df = PatientFlowMonitor().monthly_noshow_trend(start_year=2021, end_year=2023)
            if not df.empty:
                df["period"] = pd.to_datetime(df["period"])
                return df, False
        except: pass
    return synth_monthly_trend(start_year=2021, end_year=2023), True

def _er():
    if ENGINE_OK:
        try:
            df = ERWaitPredictor().state_er_heatmap(2022)
            if not df.empty: return df, False
        except: pass
    return synth_er_heatmap(2022), True

def render():
    st.markdown('<div class="hiq-page-title">System Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="hiq-page-sub">Real-time hospital resource intelligence</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    snap, synth = _snap()
    if synth:
        st.info("") #removed

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Appointments / Month", f"{int(snap.get('appointments_this_month',0)):,}")
    k2.metric("No-Shows", f"{int(snap.get('no_shows_this_month',0)):,}")
    nsr = float(snap.get('no_show_rate', 0))
    k3.metric("No-Show Rate", f"{nsr:.1f}%", delta=f"{nsr-22:.1f}% vs avg", delta_color="inverse")
    k4.metric("Avg Wait Days", f"{float(snap.get('avg_wait_days',0)):.1f} d")
    k5.metric("SMS Sent", f"{int(snap.get('sms_sent',0)):,}")

    st.markdown("<br>", unsafe_allow_html=True)
    cl, cr = st.columns([1.1, 1], gap="large")

    with cl:
        trend_df, _ = _trend()
        agg = (trend_df.groupby("period", as_index=False)
               .agg(no_show_rate_pct=("no_show_rate_pct","mean")))
        agg["period"] = pd.to_datetime(agg["period"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=agg["period"], y=agg["no_show_rate_pct"],
            fill="tozeroy", fillcolor="rgba(26,86,219,0.08)",
            line=dict(color=BLUE, width=2.5), name="No-Show Rate %",
        ))
        fig.update_layout(
            title=dict(text="Nationwide No-Show Rate (2021–2023)",
                       font=dict(family="Inter,sans-serif",size=14,color=NAVY,weight="bold"),x=0,xanchor="left"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            font=dict(family="Inter,sans-serif",color=TEXT),
            margin=dict(l=8,r=8,t=44,b=8), showlegend=False,
            xaxis=dict(gridcolor=GRID, tickfont=dict(size=11,color=TEXT2)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=11,color=TEXT2), title_text="Rate (%)"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        er_df, _ = _er()
        fig2 = choropleth(er_df, "state_code", "avg_er_wait_minutes",
                          "Avg ER Wait Time by State (min)",
                          [[0,"#dbeafe"],[0.5,"#1a56db"],[1.0,"#0f2d5e"]])
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="hiq-section">Capacity Alert Summary — 2023</div>', unsafe_allow_html=True)
    alerts = synth_capacity_alerts(2023)
    high   = alerts[alerts["risk_tier"].isin(["High","Critical"])].sort_values("avg_occupancy",ascending=False).head(10)

    badge_map = {"Normal":"badge-normal","Elevated":"badge-elevated","High":"badge-high","Critical":"badge-critical"}
    rows_html = ""
    for _, r in high.iterrows():
        bc = badge_map.get(r["risk_tier"],"badge-normal")
        rows_html += f"""<tr>
          <td style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:{BLUE};padding:0.55rem 1rem;font-weight:600;">{r['state_code']}</td>
          <td style="font-size:0.85rem;color:{TEXT};padding:0.55rem 1rem;">{r['state_name']}</td>
          <td style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:{TEXT};padding:0.55rem 1rem;">{r['avg_occupancy']:.1f}%</td>
          <td style="font-size:0.85rem;color:{TEXT};padding:0.55rem 1rem;">{r['months_above_85']}</td>
          <td style="padding:0.55rem 1rem;"><span class="badge {bc}">{r['risk_tier']}</span></td>
        </tr>"""

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid {BORDER};border-radius:12px;overflow:hidden;">
      <thead><tr style="background:#f8fafc;border-bottom:1px solid {BORDER};">
        <th style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">STATE</th>
        <th style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">NAME</th>
        <th style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">AVG OCC.</th>
        <th style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">MONTHS &gt;85%</th>
        <th style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">RISK</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)