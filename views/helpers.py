"""views/helpers.py — Shared chart builders, theme tokens"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Theme 
BG      = "#f0f4f8"
SURFACE = "#ffffff"
BORDER  = "#e2e8f0"
NAVY    = "#0f2d5e"
BLUE    = "#1a56db"
BLUE_LT = "#ebf0ff"
TEAL    = "#0891b2"
GREEN   = "#059669"
AMBER   = "#d97706"
RED     = "#dc2626"
TEXT    = "#1e293b"
TEXT2   = "#475569"
TEXT3   = "#94a3b8"
GRID    = "#e2e8f0"

CHART_COLORS = [BLUE, TEAL, GREEN, AMBER, RED, "#7c3aed", "#db2777"]

LAYOUT = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "white",
    font          = dict(family="Inter, sans-serif", color=TEXT, size=12),
    margin        = dict(l=8, r=8, t=44, b=8),
    legend        = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=TEXT2)),
    xaxis         = dict(gridcolor=GRID, zerolinecolor=GRID,
                         linecolor=BORDER, tickfont=dict(size=11, color=TEXT2),
                         showgrid=True),
    yaxis         = dict(gridcolor=GRID, zerolinecolor=GRID,
                         linecolor=BORDER, tickfont=dict(size=11, color=TEXT2),
                         showgrid=True),
    title         = dict(font=dict(family="Inter,sans-serif", size=14,
                                   color=NAVY, weight="bold"), x=0, xanchor="left"),
)

US_STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL",
             "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT",
             "NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI",
             "SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"]
STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia",
    "HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
    "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
    "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina",
    "SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont",
    "VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
}


# data 
np.random.seed(42)

def synth_monthly_trend(state_code=None, start_year=2020, end_year=2023):
    rows = []
    for yr in range(start_year, end_year + 1):
        for mo in range(1, 13):
            appts = int(np.random.normal(12000, 2000))
            nsr   = np.random.uniform(15, 35)
            rows.append(dict(
                state_name=STATE_NAMES.get(state_code or "CA", "Nationwide"),
                year=yr, month=mo,
                total_appointments=max(appts, 5000),
                no_shows=int(appts * nsr / 100),
                no_show_rate_pct=round(nsr, 2),
                avg_wait_days=round(np.random.uniform(1, 14), 1),
                period=pd.Timestamp(f"{yr}-{mo:02d}-01"),
            ))
    return pd.DataFrame(rows)

def synth_regional():
    return pd.DataFrame([dict(
        region=r,
        total_appointments=int(np.random.normal(150000, 30000)),
        no_show_rate_pct=round(np.random.uniform(18, 30), 2),
        avg_wait_days=round(np.random.uniform(2, 12), 1),
        sms_effectiveness_pct=round(np.random.uniform(60, 85), 2),
    ) for r in ["Northeast","Midwest","South","West"]])

def synth_age_group():
    return pd.DataFrame([dict(
        age_group=f"{i}-{i+9}",
        total_appointments=int(np.random.normal(15000, 4000)),
        no_show_rate_pct=round(np.random.uniform(10, 40), 2),
    ) for i in range(0, 100, 10)])

def synth_snapshot():
    return {"appointments_this_month":47832,"no_shows_this_month":9124,
            "no_show_rate":19.1,"avg_wait_days":5.3,"sms_sent":31200}

def synth_er_heatmap(year=2022):
    return pd.DataFrame([dict(
        state_code=sc, state_name=STATE_NAMES.get(sc, sc),
        avg_er_wait_minutes=round(np.random.normal(145, 45), 1),
        avg_bed_occupancy=round(np.random.uniform(55, 95), 2),
        total_er_visits=int(np.random.randint(8000, 120000)),
    ) for sc in US_STATES])

def synth_bed_forecast(state_code=None, periods=6):
    dates_hist = pd.date_range("2018-01-01","2023-12-01", freq="MS")
    base  = 72 + 8 * np.sin(np.linspace(0, 6*np.pi, len(dates_hist)))
    noise = np.random.normal(0, 3, len(dates_hist))
    hist_vals = np.clip(base + noise, 45, 99)
    dates_fore = pd.date_range("2024-01-01", periods=periods, freq="MS")
    fore_vals  = np.clip(hist_vals[-6:].mean() + np.random.normal(0,2,periods), 50, 99)
    df_h = pd.DataFrame({"ds":dates_hist,"yhat":hist_vals,"yhat_lower":hist_vals,"yhat_upper":hist_vals,"is_forecast":False})
    df_f = pd.DataFrame({"ds":dates_fore,"yhat":fore_vals,"yhat_lower":np.clip(fore_vals-5,40,99),"yhat_upper":np.clip(fore_vals+5,50,100),"is_forecast":True})
    df = pd.concat([df_h, df_f], ignore_index=True)
    df["alert_level"] = pd.cut(df["yhat"],bins=[0,70,85,95,100],labels=["Normal","Elevated","High","Critical"],right=True)
    return df

def synth_capacity_alerts(year=2023):
    return pd.DataFrame([dict(
        state_code=sc, state_name=STATE_NAMES.get(sc,sc),
        avg_occupancy=round(np.random.uniform(55,98),2),
        months_above_85=int(np.random.randint(0,12)),
        risk_tier=np.random.choice(["Normal","Elevated","High","Critical"],p=[0.35,0.3,0.25,0.1]),
    ) for sc in US_STATES])

def synth_feature_importance():
    feats = ["bed_occupancy_rate","total_er_visits","age","wait_days","month","region","gender","sms_received","season"]
    vals  = sorted(np.random.dirichlet(np.ones(len(feats))), reverse=True)
    return pd.DataFrame({"feature":feats,"importance":vals})

# Chart builders 
def make_layout(**overrides):
    l = dict(LAYOUT)
    l.update(overrides)
    return l

def choropleth(df, state_col, value_col, title="", color_scale=None):
    scale = color_scale or [[0,"#ebf0ff"],[0.5,"#1a56db"],[1.0,"#0f2d5e"]]
    fig = go.Figure(go.Choropleth(
        locations=df[state_col], z=df[value_col], locationmode="USA-states",
        colorscale=scale,
        colorbar=dict(title=dict(text=value_col.replace("_"," ").title(),
                                  font=dict(color=TEXT2,size=10)),
                      tickfont=dict(color=TEXT2,size=10),
                      bgcolor="white", bordercolor=BORDER, borderwidth=1),
        marker_line_color=BORDER, marker_line_width=0.8,
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(family="Inter,sans-serif",size=14,color=NAVY,weight="bold"), x=0, xanchor="left"),
        geo=dict(scope="usa", bgcolor="rgba(0,0,0,0)", lakecolor="#dbeafe",
                 landcolor="#f1f5f9", showlakes=True, showframe=False, coastlinecolor=BORDER),
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=8,r=8,t=44,b=8),
        font=dict(family="Inter,sans-serif",color=TEXT),
    )
    return fig

def gauge_chart(value, title, min_val=0, max_val=300, thresholds=None):
    thr = thresholds or [90, 150, 240]
    steps = [
        dict(range=[min_val, thr[0]], color="#d1fae5"),
        dict(range=[thr[0],  thr[1]], color="#fef3c7"),
        dict(range=[thr[1],  thr[2]], color="#fee2e2"),
        dict(range=[thr[2],  max_val],color="#fca5a5"),
    ]
    needle_color = GREEN if value < thr[0] else AMBER if value < thr[1] else RED
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(family="IBM Plex Mono",size=11,color=TEXT2)),
        number=dict(font=dict(family="Inter",size=32,color=NAVY,weight="bold")),
        gauge=dict(
            axis=dict(range=[min_val,max_val], tickcolor=TEXT3, tickfont=dict(size=9,color=TEXT3)),
            bar=dict(color=needle_color, thickness=0.25),
            steps=steps,
            threshold=dict(line=dict(color=RED,width=2), value=thr[1]),
            bgcolor="white", bordercolor=BORDER,
        ),
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=20,r=20,t=50,b=10),
                      font=dict(family="Inter,sans-serif"))
    return fig

def forecast_chart(df, title="Bed Occupancy Forecast"):
    hist = df[~df["is_forecast"]]
    fore = df[df["is_forecast"]]
    fig  = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist["ds"], y=hist["yhat"], mode="lines", name="Historical",
        line=dict(color=BLUE, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([fore["ds"], fore["ds"].iloc[::-1]]),
        y=pd.concat([fore["yhat_upper"], fore["yhat_lower"].iloc[::-1]]),
        fill="toself", fillcolor="rgba(26,86,219,0.1)",
        line=dict(color="rgba(0,0,0,0)"), name="95% CI",
    ))
    fig.add_trace(go.Scatter(
        x=fore["ds"], y=fore["yhat"], mode="lines+markers", name="Forecast",
        line=dict(color=TEAL, width=2.5, dash="dot"),
        marker=dict(size=7, color=TEAL, line=dict(color="white",width=1.5)),
    ))
    fig.add_hline(y=85, line_dash="dash", line_color=AMBER, opacity=0.8,
                  annotation_text="High Risk (85%)",
                  annotation_font_color=AMBER, annotation_font_size=10)
    fig.update_layout(**make_layout(title=dict(text=title,font=dict(family="Inter,sans-serif",size=14,color=NAVY,weight="bold"),x=0,xanchor="left")))
    fig.update_yaxes(title_text="Occupancy Rate (%)", range=[30, 108])
    return fig