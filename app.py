import streamlit as st
from streamlit_option_menu import option_menu
from pages.race_summary import show_race_summary
from pages.telemetry import show_telemetry
from pages.strategy import show_strategy
from pages.analytics import show_analytics
from pages.replay import show_replay
from pages.season import show_season


from pages.home import show_home
from utils.theme import load_css

st.set_page_config(
    page_title="F1 Live Analytics",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

load_css()

st.markdown("""
<h1 style='text-align:center; color:white; margin-bottom:0;'>
🏎️ F1 LIVE ANALYTICS
</h1>

<p style='text-align:center; color:#9CA3AF; font-size:20px; margin-top:-10px; margin-bottom:30px;'>
Formula 1 Data Analytics & Visualization Platform
</p>
""", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=[
        "Home",
        "Race Summary",
        "Analytics",
        "Strategy",
        "Telemetry",
        "Replay",
        "Season"
    ],
    icons=[
        "house-fill",
        "flag-fill",
        "graph-up",
        "diagram-3-fill",
        "speedometer2",
        "camera-video-fill",
        "calendar-event"
    ],
    menu_icon=None,
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important",
            "background-color": "#111827",
            "border-radius": "12px",
            "margin-bottom": "25px"
        },
        "icon": {
            "color": "#E10600",
            "font-size": "18px"
        },
        "nav-link": {
            "font-size": "17px",
            "font-weight": "600",
            "text-align": "center",
            "margin": "0px",
            "--hover-color": "#1F2937",
        },
        "nav-link-selected": {
            "background-color": "#E10600",
            "color": "white",
        },
    }
)

# Page Router Mapping
page_handlers = {
    "Home": lambda: show_home(),
    "Race Summary": lambda: show_race_summary(),
    "Tyre Strategy": lambda: show_strategy(),
    "Strategy": lambda: show_strategy(),
    "Analytics": lambda: show_analytics(),
    "Telemetry": lambda: show_telemetry(),
    "Replay": lambda: show_replay(),
    "Season": lambda: show_season(),
}

handler = page_handlers.get(selected)
if handler:
    handler()