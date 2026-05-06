"""
app.py — Smart Hospital Resource & Patient Flow Analytics System
"""

import streamlit as st

st.set_page_config(
    page_title="HospitalIQ",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state for active page
if "page" not in st.session_state:
    st.session_state.page = "Overview"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg:       #f0f4f8;
    --surface:  #ffffff;
    --border:   #e2e8f0;
    --border2:  #cbd5e1;
    --navy:     #0f2d5e;
    --blue:     #1a56db;
    --teal:     #0891b2;
    --green:    #059669;
    --green-lt: #d1fae5;
    --amber:    #d97706;
    --amber-lt: #fef3c7;
    --red:      #dc2626;
    --red-lt:   #fee2e2;
    --text:     #1e293b;
    --text2:    #475569;
    --text3:    #94a3b8;
    --mono:     'IBM Plex Mono', monospace;
    --sans:     'Inter', sans-serif;
}

html, body, [class*="css"] { font-family: var(--sans) !important; color: var(--text); }
.stApp { background: var(--bg) !important; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1400px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: var(--navy) !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12) !important; }

/* Nav buttons — full reset then restyle */
[data-testid="stSidebar"] .stButton { width: 100% !important; margin: 1px 0 !important; }
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 0.6rem 0.9rem !important;
    cursor: pointer !important;
    transition: background 0.15s, color 0.15s !important;
    box-shadow: none !important;
    letter-spacing: 0 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    color: #e2e8f0 !important;
    box-shadow: none !important;
    transform: none !important;
}
/* Active nav button class */
[data-testid="stSidebar"] .stButton > button[data-active="true"],
[data-testid="stSidebar"] .nav-active > button {
    background: rgba(26,86,219,0.3) !important;
    color: #ffffff !important;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: 12px !important; padding: 1.25rem 1.5rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
[data-testid="metric-container"] label {
    color: var(--text2) !important; font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--navy) !important; font-size: 1.9rem !important; font-weight: 700 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: 10px !important; padding: 4px !important; gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important; font-size: 0.83rem !important; font-weight: 500 !important;
    color: var(--text2) !important; padding: 0.45rem 1.1rem !important; background: transparent !important;
}
.stTabs [aria-selected="true"] { background: var(--blue) !important; color: #ffffff !important; }

/* Main buttons */
.stButton > button {
    background: var(--blue) !important; color: white !important; border: none !important;
    border-radius: 8px !important; font-size: 0.875rem !important; font-weight: 600 !important;
    padding: 0.55rem 1.5rem !important; transition: background 0.15s !important;
}
.stButton > button:hover { background: #1648c0 !important; }

/* Inputs */
.stSelectbox > div > div {
    background: var(--surface) !important; border-color: var(--border2) !important;
    border-radius: 8px !important; color: var(--text) !important; font-size: 0.875rem !important;
}
.streamlit-expanderHeader {
    background: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; font-size: 0.85rem !important; font-weight: 600 !important;
    color: var(--text) !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important; border-radius: 10px !important;
    overflow: hidden !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

/* Typography helpers */
.hiq-page-title { font-size:1.65rem; font-weight:700; color:var(--navy); letter-spacing:-0.02em; line-height:1.2; }
.hiq-page-sub   { font-family:var(--mono); font-size:0.68rem; color:var(--text3); letter-spacing:0.1em; text-transform:uppercase; margin-top:0.2rem; }
.hiq-section    { font-size:1rem; font-weight:600; color:var(--navy); margin:1.5rem 0 0.75rem 0; }

/* Cards */
.hiq-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.25rem 1.4rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.hiq-card-blue  { border-left: 4px solid var(--blue);  }
.hiq-card-teal  { border-left: 4px solid var(--teal);  }
.hiq-card-green { border-left: 4px solid var(--green); }
.hiq-card-amber { border-left: 4px solid var(--amber); }
.hiq-card-red   { border-left: 4px solid var(--red);   }

.hiq-label { font-family:var(--mono); font-size:0.65rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text3); margin-bottom:0.25rem; }
.hiq-value { font-size:1.6rem; font-weight:700; color:var(--navy); line-height:1.2; }
.hiq-sub   { font-size:0.78rem; color:var(--text2); margin-top:0.2rem; }

/* Badges */
.badge { display:inline-flex; align-items:center; padding:3px 10px; border-radius:99px; font-family:var(--mono); font-size:0.68rem; font-weight:500; letter-spacing:0.04em; }
.badge-normal   { background:var(--green-lt); color:var(--green); }
.badge-elevated { background:var(--amber-lt); color:var(--amber); }
.badge-high     { background:var(--red-lt);   color:var(--red);   }
.badge-critical { background:#450a0a;          color:#fca5a5;      }

#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Nav items 
NAV = [
    ("Overview",              "", "System overview & KPIs"),
    ("Patient Flow Monitor",  "", "Appointment trends"),
    ("ER Wait Predictor",     "", "ML wait-time forecast"),
    ("Bed Occupancy Forecast","", "Capacity planning"),
]

# Sidebar 
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="padding:1.6rem 0.6rem 1.2rem 0.6rem;">
        <div style="font-family:'Inter',sans-serif;font-size:1.4rem;font-weight:700;
                    color:#ffffff;letter-spacing:-0.02em;">
            🏥 Hospital<span style="color:#60a5fa;">IQ</span>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.62rem;
                    color:#475569;letter-spacing:0.1em;margin-top:4px;">
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;color:#475569;
                letter-spacing:0.12em;text-transform:uppercase;padding:0 0.4rem 0.6rem 0.4rem;">
        Navigation
    </div>
    """, unsafe_allow_html=True)

    # Custom nav buttons
    for page_name, icon, subtitle in NAV:
        is_active = st.session_state.page == page_name
        # Active state: highlighted card; inactive: ghost
        if is_active:
            st.markdown(f"""
            <div style="background:rgba(26,86,219,0.25);border-radius:10px;
                        padding:0.65rem 0.9rem;margin:2px 0;cursor:default;
                        border-left:3px solid #60a5fa;">
                <div style="font-family:'Inter',sans-serif;font-size:0.875rem;
                            font-weight:600;color:#ffffff;">
                    {icon}&nbsp;&nbsp;{page_name}
                </div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:0.62rem;
                            color:#93c5fd;margin-top:1px;padding-left:1.4rem;">
                    {subtitle}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button(f"{icon}  {page_name}", key=f"nav_{page_name}",
                         use_container_width=True):
                st.session_state.page = page_name
                st.rerun()

    st.divider()

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;color:#475569;
                letter-spacing:0.12em;text-transform:uppercase;padding:0 0.4rem 0.4rem 0.4rem;">
        Data Sources
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;
                color:#475569;line-height:2.1;padding:0 0.4rem;">
        · Kaggle No-Show Appts<br>
        · CMS HCAHPS<br>
        · AHRQ HCUP<br>
        · CDC Chronic Indicators<br>
        · US Mortality (Kaggle)
    </div>
    """, unsafe_allow_html=True)

# Route 
page = st.session_state.page

if page == "Overview":
    from views.overview import render
elif page == "Patient Flow Monitor":
    from views.patient_flow import render
elif page == "ER Wait Predictor":
    from views.er_wait import render
else:
    from views.bed_occupancy import render

render()