"""views/bed_occupancy.py — Feature 3: Bed Occupancy Forecast."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from views.helpers import (
    synth_bed_forecast, synth_capacity_alerts, forecast_chart,
    BLUE, TEAL, GREEN, AMBER, RED, TEXT, TEXT2, TEXT3, NAVY, GRID, BORDER, US_STATES, STATE_NAMES,
)
try:
    from analytics_engine import BedOccupancyForecaster as _BOF
    ENGINE_OK = True
except: ENGINE_OK = False

_forecaster = None
def _get_f():
    global _forecaster
    if _forecaster is None and ENGINE_OK:
        try: _forecaster=_BOF()
        except: pass
    return _forecaster

def _forecast(state, periods):
    f=_get_f()
    if f:
        try:
            df=f.forecast(state if state!="ALL" else None,periods)
            if not df.empty: return df,False
        except: pass
    return synth_bed_forecast(state if state!="ALL" else None,periods),True

def _alerts(yr):
    f=_get_f()
    if f:
        try:
            df=f.capacity_alerts(yr)
            if not df.empty: return df,False
        except: pass
    return synth_capacity_alerts(yr),True

def _layout(title):
    return dict(
        title=dict(text=title,font=dict(family="Inter,sans-serif",size=14,color=NAVY,weight="bold"),x=0,xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="white",
        font=dict(family="Inter,sans-serif",color=TEXT),
        margin=dict(l=8,r=8,t=44,b=8),
        xaxis=dict(gridcolor=GRID,tickfont=dict(size=11,color=TEXT2)),
        yaxis=dict(gridcolor=GRID,tickfont=dict(size=11,color=TEXT2)),
    )

COLOR_MAP={"Critical":RED,"High":AMBER,"Elevated":TEAL,"Normal":GREEN}

def render():
    st.markdown('<div class="hiq-page-title">Bed Occupancy Forecast</div>',unsafe_allow_html=True)
    st.markdown('<div class="hiq-page-sub">Feature 3 · Time-Series Capacity Planning with Prophet</div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

    tab1,tab2,tab3=st.tabs(["State Forecast","Multi-State Compare","Capacity Alerts"])

    with tab1:
        fc1,fc2=st.columns([2,1],gap="large")
        state=fc1.selectbox("State",["ALL"]+sorted(US_STATES),key="fc_state")
        periods=fc2.slider("Forecast Months Ahead",1,12,6)
        df,synth=_forecast(state,periods)
        if synth: st.caption("") #added
        title=f"Bed Occupancy — {'Nationwide' if state=='ALL' else STATE_NAMES.get(state,state)}"
        st.plotly_chart(forecast_chart(df,title),use_container_width=True)

        future=df[df["is_forecast"]==True].copy()
        if not future.empty:
            st.markdown('<div style="font-size:0.95rem;font-weight:600;color:#0f2d5e;margin:1rem 0 0.5rem 0;">Forecast Detail</div>',unsafe_allow_html=True)
            badge_map={"Normal":"badge-normal","Elevated":"badge-elevated","High":"badge-high","Critical":"badge-critical"}
            cols=st.columns(min(len(future),6))
            for i,(_, row) in enumerate(future.iterrows()):
                if i>=6: break
                al=str(row.get("alert_level","Normal")); bc=badge_map.get(al,"badge-normal")
                col_val=COLOR_MAP.get(al,BLUE)
                with cols[i]:
                    st.markdown(f"""
                    <div class="hiq-card" style="text-align:center;padding:0.9rem 0.6rem;">
                      <div class="hiq-label">{row['ds'].strftime('%b %Y')}</div>
                      <div style="font-size:1.4rem;font-weight:700;color:{col_val};line-height:1.2;">{row['yhat']:.1f}%</div>
                      <div style="font-size:0.72rem;color:{TEXT3};margin:2px 0;">{row['yhat_lower']:.1f}–{row['yhat_upper']:.1f}</div>
                      <span class="badge {bc}" style="margin-top:6px;">{al}</span>
                    </div>""",unsafe_allow_html=True)

        with st.expander("ℹ️ Alert Level Definitions"):
            st.markdown("""
            | Level | Range | Meaning |
            |---|---|---|
            | 🟢 Normal | < 70% | Sufficient capacity |
            | 🟡 Elevated | 70–85% | Monitor closely |
            | 🔴 High | 85–95% | Activate surge protocols |
            | 🚨 Critical | > 95% | Emergency escalation |
            """)

    with tab2:
        selected=st.multiselect("Select States (2–5)",sorted(US_STATES),default=["CA","TX","NY","FL"],max_selections=5)
        periods2=st.slider("Forecast Months",1,12,6,key="ms_p")
        if len(selected)<2:
            st.warning("Select at least 2 states to compare.")
        else:
            all_dfs=[]
            for sc in selected:
                d,_=_forecast(sc,periods2); d["state_code"]=sc; all_dfs.append(d)
            combined=pd.concat(all_dfs,ignore_index=True)
            combined["ds"]=pd.to_datetime(combined["ds"])
            hist=combined[~combined["is_forecast"]]; fore=combined[combined["is_forecast"]]
            colors=[BLUE,TEAL,GREEN,AMBER,RED]
            fig=go.Figure()
            for i,sc in enumerate(selected):
                col=colors[i%len(colors)]; name=STATE_NAMES.get(sc,sc)
                h=hist[hist["state_code"]==sc]; f=fore[fore["state_code"]==sc]
                fig.add_trace(go.Scatter(x=h["ds"],y=h["yhat"],name=f"{name} (hist)",line=dict(color=col,width=1.8),mode="lines"))
                fig.add_trace(go.Scatter(x=f["ds"],y=f["yhat"],name=f"{name} (forecast)",line=dict(color=col,width=2.5,dash="dot"),mode="lines+markers",marker=dict(size=6,color=col)))
            fig.add_hline(y=85,line_dash="dash",line_color=AMBER,opacity=0.7,annotation_text="High Risk 85%",annotation_font_color=AMBER,annotation_font_size=10)
            fig.update_layout(**_layout("Multi-State Bed Occupancy Comparison"))
            fig.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=10)))
            fig.update_yaxes(title_text="Occupancy (%)",range=[30,108])
            st.plotly_chart(fig,use_container_width=True)
            rows=[]
            for sc in selected:
                f=fore[fore["state_code"]==sc]
                if not f.empty:
                    rows.append({"State":STATE_NAMES.get(sc,sc),"Avg Forecast (%)":round(f["yhat"].mean(),1),"Peak (%)":round(f["yhat"].max(),1),"Min (%)":round(f["yhat"].min(),1),"Months > 85%":int((f["yhat"]>85).sum())})
            if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True)

    with tab3:
        yr=st.selectbox("Year",list(range(2018,2024)),index=5,key="alert_yr")
        alerts,synth3=_alerts(yr)
        if synth3: st.caption("") #added
        k1,k2,k3,k4=st.columns(4)
        k1.metric("States Monitored",len(alerts))
        k2.metric("Critical States",len(alerts[alerts["risk_tier"]=="Critical"]))
        k3.metric("High Risk States",len(alerts[alerts["risk_tier"]=="High"]))
        k4.metric("Avg Occupancy",f"{alerts['avg_occupancy'].mean():.1f}%")
        st.markdown("<br>",unsafe_allow_html=True)
        ac1,ac2=st.columns([1.4,1],gap="large")
        with ac1:
            top20=alerts.sort_values("avg_occupancy",ascending=False).head(20)
            bar_colors=[COLOR_MAP.get(t,TEAL) for t in top20["risk_tier"]]
            fig=go.Figure(go.Bar(x=top20["state_code"],y=top20["avg_occupancy"],marker_color=bar_colors,marker_line_width=0,text=top20["avg_occupancy"].apply(lambda x:f"{x:.0f}%"),textposition="outside"))
            fig.add_hline(y=85,line_dash="dash",line_color=AMBER,opacity=0.8,annotation_text="High Risk (85%)",annotation_font_color=AMBER,annotation_font_size=10)
            fig.add_hline(y=95,line_dash="dash",line_color=RED,opacity=0.7,annotation_text="Critical (95%)",annotation_font_color=RED,annotation_font_size=10)
            fig.update_layout(**_layout(f"Avg Bed Occupancy by State — {yr}"))
            fig.update_yaxes(title_text="Occupancy (%)",range=[0,115])
            st.plotly_chart(fig,use_container_width=True)
        with ac2:
            tier_order=["Critical","High","Elevated","Normal"]
            tier_counts=alerts["risk_tier"].value_counts().reindex(tier_order,fill_value=0)
            fig2=go.Figure(go.Pie(
                labels=tier_counts.index,values=tier_counts.values,hole=0.55,
                marker=dict(colors=[COLOR_MAP[t] for t in tier_counts.index],line=dict(color="white",width=2)),
                textfont=dict(family="IBM Plex Mono",size=11),
            ))
            fig2.update_layout(
                title=dict(text="Risk Tier Distribution",font=dict(family="Inter,sans-serif",size=14,color=NAVY,weight="bold"),x=0,xanchor="left"),
                paper_bgcolor="rgba(0,0,0,0)",font=dict(family="Inter,sans-serif",color=TEXT),
                margin=dict(l=8,r=8,t=44,b=8),legend=dict(font=dict(size=11),bgcolor="rgba(0,0,0,0)"),
                annotations=[dict(text=f"{len(alerts)}<br><span style='font-size:11px'>States</span>",x=0.5,y=0.5,showarrow=False,font=dict(family="Inter",size=20,color=NAVY))],
            )
            st.plotly_chart(fig2,use_container_width=True)

        # Table
        badge_map={"Normal":"badge-normal","Elevated":"badge-elevated","High":"badge-high","Critical":"badge-critical"}
        rows_html=""
        for _,r in alerts.sort_values("avg_occupancy",ascending=False).iterrows():
            bc=badge_map.get(r["risk_tier"],"badge-normal")
            bar_w=min(int(r["avg_occupancy"]),100); col=COLOR_MAP.get(r["risk_tier"],TEAL)
            rows_html+=f"""<tr style="border-bottom:1px solid {BORDER};">
              <td style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:{BLUE};padding:0.5rem 1rem;font-weight:600;">{r['state_code']}</td>
              <td style="font-size:0.83rem;color:{TEXT};padding:0.5rem 1rem;">{r['state_name']}</td>
              <td style="padding:0.5rem 1rem;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <div style="background:{col};height:6px;width:{bar_w}px;border-radius:3px;min-width:4px;"></div>
                  <span style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:{TEXT};">{r['avg_occupancy']:.1f}%</span>
                </div>
              </td>
              <td style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:{TEXT};padding:0.5rem 1rem;">{r['months_above_85']}</td>
              <td style="padding:0.5rem 1rem;"><span class="badge {bc}">{r['risk_tier']}</span></td>
            </tr>"""
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;background:white;border:1px solid {BORDER};border-radius:12px;overflow:hidden;margin-top:1rem;">
          <thead><tr style="background:#f8fafc;">
            <th style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">STATE</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">NAME</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">AVG OCCUPANCY</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">MONTHS &gt;85%</th>
            <th style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:0.08em;color:{TEXT3};text-align:left;padding:0.65rem 1rem;font-weight:500;">RISK</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>""",unsafe_allow_html=True)
        st.download_button("⬇️ Download Alerts CSV",alerts.to_csv(index=False),f"capacity_alerts_{yr}.csv","text/csv",use_container_width=True)