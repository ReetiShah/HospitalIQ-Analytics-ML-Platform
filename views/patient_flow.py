"""views/patient_flow.py — Feature 1: Patient Flow Monitor."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
# from analytics_engine import PatientFlowMonitor  # type: ignore

from views.helpers import (
    synth_monthly_trend, synth_regional, synth_age_group,
    BLUE, TEAL, GREEN, AMBER, RED, TEXT, TEXT2, TEXT3, NAVY, GRID, BORDER, CHART_COLORS, US_STATES,
)
try:
    from analytics_engine import PatientFlowMonitor as _PFM
    _pfm = _PFM(); ENGINE_OK = True
except: ENGINE_OK = False

def _trend(state, y0, y1):
    if ENGINE_OK:
        try:
            df = _pfm.monthly_noshow_trend(state_code=state if state!="ALL" else None, start_year=y0, end_year=y1)
            if not df.empty:
                df["period"]=pd.to_datetime(df["period"]); return df,False
        except: pass
    return synth_monthly_trend(state if state!="ALL" else None, y0, y1), True

def _regional(yr):
    if ENGINE_OK:
        try:
            df=_pfm.regional_flow_summary(yr)
            if not df.empty: return df,False
        except: pass
    return synth_regional(), True

def _age(yr):
    if ENGINE_OK:
        try:
            df=_pfm.age_group_noshow(yr)
            if not df.empty: return df,False
        except: pass
    return synth_age_group(), True

def _layout(title):
    return dict(
        title=dict(text=title,font=dict(family="Inter,sans-serif",size=14,color=NAVY,weight="bold"),x=0,xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="white",
        font=dict(family="Inter,sans-serif",color=TEXT),
        margin=dict(l=8,r=8,t=44,b=8),
        xaxis=dict(gridcolor=GRID,tickfont=dict(size=11,color=TEXT2)),
        yaxis=dict(gridcolor=GRID,tickfont=dict(size=11,color=TEXT2)),
    )

def render():
    st.markdown('<div class="hiq-page-title">Patient Flow Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="hiq-page-sub">Feature 1 · Historical & Real-Time Appointment Analytics</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("⚙️ Filters", expanded=True):
        fc1,fc2,fc3 = st.columns(3)
        state = fc1.selectbox("State", ["ALL"]+sorted(US_STATES))
        y0    = fc2.selectbox("From Year", list(range(2015,2024)), index=5)
        y1    = fc3.selectbox("To Year",   list(range(2015,2024)), index=8)
    if y0>y1: st.error("'From Year' must be ≤ 'To Year'."); return

    df, synth = _trend(state, y0, y1)
    if synth: st.caption("") #added

    total=df["total_appointments"].sum(); no_show=df["no_shows"].sum()
    nsr=round(no_show/total*100,1) if total>0 else 0
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Total Appointments",f"{total:,}"); k2.metric("Total No-Shows",f"{no_show:,}")
    k3.metric("Avg No-Show Rate",f"{nsr}%"); k4.metric("Avg Wait Days",f"{df['avg_wait_days'].mean():.1f} d")
    st.markdown("<br>", unsafe_allow_html=True)

    tab1,tab2,tab3 = st.tabs(["Monthly Trend","Regional Breakdown","Age Distribution"])

    with tab1:
        agg=df.copy(); agg["period"]=pd.to_datetime(agg["period"])
        if state=="ALL":
            agg=(agg.groupby("period",as_index=False)
                 .agg(total_appointments=("total_appointments","sum"),
                      no_shows=("no_shows","sum"),
                      avg_wait_days=("avg_wait_days","mean"),
                      no_show_rate_pct=("no_show_rate_pct","mean")))
        c1,c2=st.columns(2,gap="large")
        with c1:
            fig=go.Figure()
            fig.add_trace(go.Bar(x=agg["period"],y=agg["total_appointments"],name="Total",marker_color=f"rgba(26,86,219,0.18)",marker_line_width=0))
            fig.add_trace(go.Bar(x=agg["period"],y=agg["no_shows"],name="No-Shows",marker_color=BLUE,marker_line_width=0))
            fig.update_layout(**_layout("Appointments vs No-Shows"),barmode="overlay",legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            avg_nsr=float(agg["no_show_rate_pct"].mean())
            fig2=go.Figure()
            fig2.add_trace(go.Scatter(x=agg["period"],y=agg["no_show_rate_pct"],fill="tozeroy",fillcolor="rgba(8,145,178,0.08)",line=dict(color=TEAL,width=2.5)))
            fig2.add_hline(y=avg_nsr,line_dash="dash",line_color=AMBER,opacity=0.8,annotation_text=f"Avg {avg_nsr:.1f}%",annotation_font_color=AMBER,annotation_font_size=10)
            fig2.update_layout(**_layout("No-Show Rate Over Time"),showlegend=False)
            fig2.update_yaxes(title_text="Rate (%)")
            st.plotly_chart(fig2,use_container_width=True)
        fig3=go.Figure(go.Scatter(x=agg["period"],y=agg["avg_wait_days"],mode="lines+markers",line=dict(color=GREEN,width=2.5),marker=dict(size=5,color=GREEN)))
        fig3.update_layout(**_layout("Avg Days Between Scheduling & Appointment"),showlegend=False)
        fig3.update_yaxes(title_text="Days")
        st.plotly_chart(fig3,use_container_width=True)

    with tab2:
        yr=st.selectbox("Year",list(range(2015,2024)),index=7,key="reg_yr")
        reg,_=_regional(yr)
        rc1,rc2=st.columns(2,gap="large")
        with rc1:
            fig=px.bar(reg,x="region",y="no_show_rate_pct",color="region",
                       color_discrete_sequence=CHART_COLORS,text="no_show_rate_pct")
            fig.update_traces(texttemplate="%{text:.1f}%",textposition="outside",marker_line_width=0)
            fig.update_layout(**_layout("No-Show Rate by Region"),showlegend=False)
            fig.update_yaxes(title_text="Rate (%)")
            st.plotly_chart(fig,use_container_width=True)
        with rc2:
            fig2=px.bar(reg,x="region",y="sms_effectiveness_pct",color="region",
                        color_discrete_sequence=[GREEN,TEAL,BLUE,AMBER],text="sms_effectiveness_pct")
            fig2.update_traces(texttemplate="%{text:.1f}%",textposition="outside",marker_line_width=0)
            fig2.update_layout(**_layout("SMS Effectiveness by Region"),showlegend=False)
            fig2.update_yaxes(title_text="Effectiveness (%)")
            st.plotly_chart(fig2,use_container_width=True)
        fig3=go.Figure()
        fig3.add_trace(go.Bar(x=reg["region"],y=reg["total_appointments"],name="Total Appointments",marker_color=f"rgba(26,86,219,0.2)",marker_line_width=0,yaxis="y"))
        fig3.add_trace(go.Scatter(x=reg["region"],y=reg["avg_wait_days"],mode="lines+markers",name="Avg Wait Days",line=dict(color=AMBER,width=2.5),marker=dict(size=9,color=AMBER),yaxis="y2"))
        fig3.update_layout(**_layout("Volume & Wait Days by Region"))
        fig3.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)"))
        fig3.update_layout(yaxis=dict(title_text="Appointments", gridcolor=GRID, tickfont=dict(size=11,color=TEXT2)))
        fig3.update_layout(yaxis2=dict(overlaying="y",side="right",tickfont=dict(size=11,color=AMBER),title_text="Wait Days",gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig3,use_container_width=True)

    with tab3:
        yr2=st.selectbox("Year",list(range(2015,2024)),index=7,key="age_yr")
        age,_=_age(yr2)
        ac1,ac2=st.columns(2,gap="large")
        with ac1:
            fig=px.bar(age,x="age_group",y="total_appointments",color_discrete_sequence=[BLUE],text="total_appointments")
            fig.update_traces(texttemplate="%{text:,}",textposition="outside",marker_line_width=0)
            fig.update_layout(**_layout("Appointment Volume by Age Group"),showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
        with ac2:
            colors=[GREEN if v<20 else AMBER if v<30 else RED for v in age["no_show_rate_pct"]]
            fig2=go.Figure(go.Bar(x=age["age_group"],y=age["no_show_rate_pct"],marker_color=colors,marker_line_width=0,text=age["no_show_rate_pct"].apply(lambda x:f"{x:.1f}%"),textposition="outside"))
            fig2.update_layout(**_layout("No-Show Rate by Age Group"))
            fig2.update_yaxes(title_text="Rate (%)")
            st.plotly_chart(fig2,use_container_width=True)

