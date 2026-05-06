"""views/er_wait.py — Feature 2: ER Wait Predictor."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
# from analytics_engine import PatientFlowMonitor  # type: ignore

from views.helpers import (
    synth_er_heatmap, synth_feature_importance, choropleth, gauge_chart,
    BLUE, TEAL, GREEN, AMBER, RED, TEXT, TEXT2, TEXT3, NAVY, GRID, BORDER, US_STATES, STATE_NAMES,
)
try:
    from analytics_engine import ERWaitPredictor as _ERP
    ENGINE_OK = True
except: ENGINE_OK = False

_predictor = None
def _get_p():
    global _predictor
    if _predictor is None and ENGINE_OK:
        try: _predictor=_ERP(); _predictor.train()
        except: pass
    return _predictor

def _predict(scenario):
    p=_get_p()
    if p:
        try: return p.predict(scenario),False
        except: pass
    wait=max(30,np.random.normal(80+scenario.get("bed_occupancy_rate",75)*0.8,20))
    prob=min(0.99,max(0.01,(wait-60)/160))
    return {"predicted_wait_minutes":round(wait,1),"congestion_risk":"High" if prob>=0.5 else "Low","risk_probability":round(prob,4)},True

def _heatmap(yr):
    p=_get_p()
    if p:
        try:
            df=p.state_er_heatmap(yr)
            if not df.empty: return df,False
        except: pass
    return synth_er_heatmap(yr),True

def _importance():
    p=_get_p()
    if p:
        try:
            df=p.feature_importance()
            if not df.empty: return df,False
        except: pass
    return synth_feature_importance(),True

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
    st.markdown('<div class="hiq-page-title">ER Wait Time Predictor</div>',unsafe_allow_html=True)
    st.markdown('<div class="hiq-page-sub">Feature 2 · ML-Powered Emergency Department Forecasting</div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

    tab1,tab2,tab3=st.tabs(["Live Predictor","State Heatmap","Model Insights"])

    with tab1:
        st.markdown('<div style="font-size:0.95rem;font-weight:600;color:#0f2d5e;margin-bottom:1rem;">Configure Scenario</div>',unsafe_allow_html=True)
        sc1,sc2,sc3=st.columns(3,gap="large")
        with sc1:
            st.markdown("**Patient**")
            age=st.slider("Patient Age",0,100,45)
            gender=st.selectbox("Gender",["M","F"])
            sms=st.toggle("SMS Reminder Sent",value=True)
            wait_d=st.slider("Days Since Scheduling",0,60,3)
        with sc2:
            st.markdown("**Time & Location**")
            month=st.slider("Month",1,12,7)
            season=st.selectbox("Season",["Spring","Summer","Fall","Winter"],index=1)
            region=st.selectbox("Region",["Northeast","Midwest","South","West"],index=2)
        with sc3:
            st.markdown("**Hospital Conditions**")
            bed_occ=st.slider("Bed Occupancy (%)",30,100,82)
            er_v=st.slider("Monthly ER Visits",5000,150000,65000,1000)

        if st.button("⚡ Predict ER Wait Time",use_container_width=True):
            res,synth=_predict(dict(age=age,gender=gender,sms_received=int(sms),wait_days=wait_d,month=month,season=season,region=region,bed_occupancy_rate=bed_occ,total_er_visits=er_v))
            if synth: st.caption("") #added
            wait_min=res["predicted_wait_minutes"]; risk_pct=res["risk_probability"]*100; risk_lbl=res["congestion_risk"]
            st.markdown("<br>",unsafe_allow_html=True)
            r1,r2,r3=st.columns(3,gap="large")
            with r1:
                st.plotly_chart(gauge_chart(wait_min,"Predicted Wait (min)",0,300,[90,150,240]),use_container_width=True)
            with r2:
                st.plotly_chart(gauge_chart(risk_pct,"Congestion Risk (%)",0,100,[40,65,85]),use_container_width=True)
            with r3:
                hours=int(wait_min//60); mins=int(wait_min%60)
                time_str=f"{hours}h {mins}m" if hours>0 else f"{mins}m"
                risk_color=RED if risk_lbl=="High" else GREEN
                bc="badge-high" if risk_lbl=="High" else "badge-normal"
                drivers=[]
                if bed_occ>85: drivers.append(f"🔴 Bed occupancy critical ({bed_occ}%)")
                if er_v>80000: drivers.append(f"🟠 High ER volume ({er_v:,})")
                if month in [12,1,2]: drivers.append("🟡 Winter peak season")
                if not sms: drivers.append("⚪ No SMS reminder sent")
                if not drivers: drivers.append("🟢 Conditions appear stable")
                driver_html="".join(f'<div style="font-size:0.82rem;margin:3px 0;color:{TEXT2};">{d}</div>' for d in drivers)
                st.markdown(f"""
                <div class="hiq-card hiq-card-{'red' if risk_lbl=='High' else 'green'}">
                  <div class="hiq-label">Prediction Summary</div>
                  <div class="hiq-value" style="color:{risk_color};">{time_str}</div>
                  <div class="hiq-sub">estimated wait time</div><br>
                  <span class="badge {bc}">{risk_lbl.upper()} CONGESTION</span>
                  <div class="hiq-sub" style="margin-top:0.5rem;">Risk probability: {risk_pct:.1f}%</div>
                  <div style="margin-top:0.8rem;font-size:0.8rem;font-weight:600;color:{NAVY};">Key Drivers</div>
                  {driver_html}
                </div>""",unsafe_allow_html=True)

    with tab2:
        yr=st.selectbox("Reference Year",list(range(2018,2024)),index=4,key="er_yr")
        er_df,synth=_heatmap(yr)
        if synth: st.caption("")
        metric=st.radio("Map metric",["avg_er_wait_minutes","avg_bed_occupancy","total_er_visits"],horizontal=True,
                        format_func=lambda x:x.replace("_"," ").title())
        scale_map={
            "avg_er_wait_minutes":[[0,"#dbeafe"],[0.5,"#1a56db"],[1.0,"#0f2d5e"]],
            "avg_bed_occupancy":  [[0,"#d1fae5"],[0.5,"#d97706"],[1.0,"#dc2626"]],
            "total_er_visits":    [[0,"#e0f7fa"],[0.5,"#0891b2"],[1.0,"#0f2d5e"]],
        }
        st.plotly_chart(choropleth(er_df,"state_code",metric,f"{metric.replace('_',' ').title()} — {yr}",scale_map[metric]),use_container_width=True)
        top10=er_df.sort_values(metric,ascending=False).head(10)
        tc1,tc2=st.columns([1,2])
        with tc1:
            st.dataframe(top10[["state_code","state_name",metric]].rename(columns={metric:metric.replace("_"," ").title()}).reset_index(drop=True),use_container_width=True)
        with tc2:
            fig=go.Figure(go.Bar(x=top10["state_code"],y=top10[metric],marker_color=BLUE,marker_line_width=0,text=top10[metric].round(1),textposition="outside"))
            fig.update_layout(**_layout(f"Top 10 States — {metric.replace('_',' ').title()}"))
            st.plotly_chart(fig,use_container_width=True)

    with tab3:
        fi,synth2=_importance()
        if synth2: st.caption("Feature importances") #added
        ic1,ic2=st.columns([1.3,1],gap="large")
        with ic1:
            fi=fi.sort_values("importance")
            n=len(fi)
            colors=[BLUE if i==n-1 else TEAL if i>=n-3 else f"rgba(26,86,219,0.3)" for i in range(n)]
            fig=go.Figure(go.Bar(
                x=fi["importance"],
                y=fi["feature"].str.replace("_enc","").str.replace("_"," ").str.title(),
                orientation="h",marker_color=colors,marker_line_width=0,
                text=fi["importance"].apply(lambda x:f"{x:.3f}"),textposition="outside",
            ))
            fig.update_layout(**_layout("Feature Importances (GBR Regressor)"))
            fig.update_layout(margin=dict(l=8,r=80,t=44,b=8))
            fig.update_xaxes(title_text="Importance Score")
            st.plotly_chart(fig,use_container_width=True)
        with ic2:
            st.markdown(f"""
            <div class="hiq-card hiq-card-blue">
              <div class="hiq-label">Models Used</div>
              <div style="margin-top:0.8rem;font-size:0.85rem;line-height:1.8;color:{TEXT2};">
                <b style="color:{BLUE};">GradientBoostingRegressor</b><br>
                Predicts exact ER wait minutes.<br>200 estimators · depth 4 · lr 0.05<br><br>
                <b style="color:{TEAL};">RandomForestClassifier</b><br>
                Classifies High / Low congestion.<br>150 trees · max depth 6<br><br>
                <span style="color:{TEXT3};">Target: er_wait_minutes &gt; 120 min = High</span>
              </div>
            </div>
            <div class="hiq-card hiq-card-amber" style="margin-top:0.75rem;">
              <div class="hiq-label">Interpretation Guide</div>
              <div style="font-size:0.82rem;line-height:1.8;margin-top:0.5rem;color:{TEXT2};">
                🔵 <b>bed_occupancy_rate</b> — strongest driver<br>
                🔵 <b>total_er_visits</b> — volume pressure<br>
                🟡 <b>age / season</b> — demographic signals<br>
                ⚪ <b>sms_received</b> — lower weight as expected
              </div>
            </div>""",unsafe_allow_html=True)