import base64
from datetime import datetime
import io
from pathlib import Path
import textwrap
import unicodedata
from PIL import Image
import requests
import streamlit as st

from utils.image_processing import preprocess_driver


def normalize_string(text: str) -> str:
    """Strips special diacritics and accents (e.g., 'Pérez' -> 'perez')."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower().strip()


def clean_team_key(team_name: str) -> str:
    """Robust keyword-based team identifier matching any API naming format."""
    if not team_name:
        return "default"

    name = normalize_string(team_name)

    if "red bull" in name or "redbull" in name:
        return "redbull"
    if "ferrari" in name:
        return "ferrari"
    if "mercedes" in name:
        return "mercedes"
    if "mclaren" in name:
        return "mclaren"
    if "aston" in name:
        return "astonmartin"
    if "alpine" in name:
        return "alpine"
    if "renault" in name:
        return "renault"
    if any(k in name for k in ["racing bulls", "vcarb", "alphatauri", "toro rosso"]) or name == "rb":
        return "rb"
    if "haas" in name:
        return "haas"
    if "williams" in name:
        return "williams"
    if any(k in name for k in ["sauber", "alfa romeo"]):
        return "sauber"
    if "audi" in name:
        return "audi"
    if "cadillac" in name:
        return "cadillac"
    if "racing point" in name:
        return "racingpoint"
    if "force india" in name:
        return "forceindia"
    if "lotus" in name:
        return "lotus"

    return name.replace(" ", "").replace("-", "").replace("_", "")


def resolve_asset_path(category: str, key_name: str) -> str | None:
    """Locates matching image files inside assets/<category>."""
    if not key_name:
        return None

    target_dirs = [Path("assets") / category, Path(category)]

    if category in ["cars", "teams"]:
        clean_key = clean_team_key(key_name)
        for target_dir in target_dirs:
            if not target_dir.exists():
                continue
            for img_path in target_dir.glob("*"):
                if normalize_string(img_path.stem) == clean_key:
                    return str(img_path)
    else:
        norm_name = normalize_string(key_name)
        parts = norm_name.split()
        last_name = parts[-1] if parts else norm_name

        for target_dir in target_dirs:
            if not target_dir.exists():
                continue
            for img_path in target_dir.glob("*"):
                stem = normalize_string(img_path.stem)
                if stem == last_name or stem in norm_name or any(p in stem for p in parts if len(p) > 2):
                    return str(img_path)

    return None


def get_team_color(team_name: str) -> str:
    """Provides header card background accent color."""
    colors = {
        "mclaren": "#ff8000",
        "redbull": "#183768",
        "ferrari": "#dc0000",
        "mercedes": "#00d2be",
        "astonmartin": "#229971",
        "alpine": "#0093cc",
        "rb": "#1f3b8a",
        "haas": "#5e6266",
        "williams": "#004080",
        "sauber": "#228b22",
        "audi": "#8a0010",
        "cadillac": "#d4af37",
        "renault": "#fff000",
        "racingpoint": "#f596c8",
    }
    return colors.get(clean_team_key(team_name), "#222233")


def load_raw_image_base64(image_path: str | None) -> str:
    """Encodes PNG assets directly to Base64 data URIs without pixel manipulation."""
    if not image_path or not Path(image_path).exists():
        return ""
    try:
        path = Path(image_path)
        ext = path.suffix.lower().replace(".", "")
        if ext == "jpg":
            ext = "jpeg"
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f"data:image/{ext};base64,{encoded}"
    except Exception:
        return ""


def process_driver_cutout(image_path: str | None) -> str:
    """Processes driver portrait cutouts through preprocess_driver pipeline."""
    if not image_path or not Path(image_path).exists():
        return ""
    try:
        img_obj = preprocess_driver(image_path)
        if img_obj is None:
            img_obj = Image.open(image_path)
        elif isinstance(img_obj, (str, Path)):
            img_obj = Image.open(img_obj)

        buffered = io.BytesIO()
        img_obj.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except Exception:
        return load_raw_image_base64(image_path)


def format_position(pos_raw: str | int) -> str:
    """Formats standing position safely, converting 'N/A' to 'N/A' instead of 'PN/A'."""
    pos_str = str(pos_raw).strip()
    return f"P{pos_str}" if pos_str.isdigit() else "N/A"


@st.cache_data(ttl=3600)
def fetch_season_teams_and_drivers(year: int) -> dict:
    """Dynamically fetches constructor standings and driver lineups from Ergast/Jolpica API."""
    teams_data = {}

    # 1. Constructor Standings
    c_url = f"https://api.jolpi.ca/ergast/f1/{year}/constructorStandings.json"
    try:
        res = requests.get(c_url, timeout=6)
        if res.status_code == 200:
            lists = res.json()["MRData"]["StandingsTable"]["StandingsLists"]
            if lists and "ConstructorStandings" in lists[0]:
                for item in lists[0]["ConstructorStandings"]:
                    t_name = item["Constructor"]["name"]
                    teams_data[t_name] = {
                        "position": item.get("position", "N/A"),
                        "points": item.get("points", "0"),
                        "wins": item.get("wins", "0"),
                        "drivers": []
                    }
    except Exception:
        pass

    # 2. Driver Standings
    d_url = f"https://api.jolpi.ca/ergast/f1/{year}/driverStandings.json"
    try:
        res = requests.get(d_url, timeout=6)
        if res.status_code == 200:
            lists = res.json()["MRData"]["StandingsTable"]["StandingsLists"]
            if lists and "DriverStandings" in lists[0]:
                for item in lists[0]["DriverStandings"]:
                    d_info = item["Driver"]
                    constructors = item.get("Constructors", [])
                    t_name = constructors[0]["name"] if constructors else "Independent"

                    d_obj = {
                        "first": d_info.get("givenName", ""),
                        "last": d_info.get("familyName", "").upper(),
                        "full_name": f"{d_info.get('givenName', '')} {d_info.get('familyName', '')}",
                        "number": d_info.get("permanentNumber") or item.get("position", ""),
                        "nationality": d_info.get("nationality", ""),
                        "points": item.get("points", "0"),
                        "position": item.get("position", "N/A")
                    }

                    if t_name not in teams_data:
                        teams_data[t_name] = {
                            "position": "N/A",
                            "points": "0",
                            "wins": "0",
                            "drivers": []
                        }

                    teams_data[t_name]["drivers"].append(d_obj)
    except Exception:
        pass

    return teams_data


def show_season():
    current_year = datetime.now().year

    if "selected_team" not in st.session_state:
        st.session_state.selected_team = None

    st.markdown("""
        <style>
        .stApp { background-color: #0f1015; color: #ffffff; }
        .f1-title { font-size: 38px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 5px; }
        .f1-subtitle { color: #a0a0b0; font-size: 16px; margin-bottom: 25px; }
        
        /* Minimal Main Grid Card */
        .team-card-minimal {
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: 120px;
        }
        .team-card-title { font-size: 28px; font-weight: 800; color: #ffffff; margin: 0; }
        .team-standing-label { font-size: 11px; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }
        .team-standing-val { font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 2px; }
        
        .team-logo-badge { width: 48px; height: 48px; border-radius: 50%; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; }
        .team-logo-badge img { width: 30px; height: 30px; object-fit: contain; }
        
        /* Detail Page Hero Banner */
        .hero-banner { border-radius: 16px; padding: 40px 20px 20px 20px; text-align: center; position: relative; margin-bottom: 30px; }
        .hero-car-img { width: 100%; max-width: 680px; height: auto; max-height: 240px; object-fit: contain; }
        .hero-title { font-size: 48px; font-weight: 900; letter-spacing: 4px; text-transform: uppercase; color: #ffffff; margin: 15px 0 5px 0; }
        
        /* Championship Podium Style Driver Card */
        .driver-card-podium {
            background-color: #161b26;
            border-radius: 16px;
            padding: 28px 20px 24px 20px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .driver-card-podium:hover {
            transform: translateY(-4px);
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.6);
        }
        .driver-podium-img {
            height: 230px;
            width: 100%;
            object-fit: contain;
            margin-bottom: 15px;
            filter: drop-shadow(0px 8px 12px rgba(0,0,0,0.5));
        }
        .driver-podium-name {
            font-size: 20px;
            font-weight: 800;
            color: #ffffff;
            margin-top: 6px;
            letter-spacing: 0.5px;
        }
        .driver-podium-team {
            font-size: 14px;
            color: #8c8c9e;
            margin-top: 2px;
            margin-bottom: 12px;
        }
        .driver-podium-number {
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 1px;
        }
        
        .stat-section-title { font-size: 28px; font-weight: 900; letter-spacing: 1.5px; text-transform: uppercase; margin: 35px 0 18px 0; }
        .stat-grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 10px 0; }
        .stat-item { border-bottom: 1px solid #282836; padding-bottom: 8px; }
        .stat-label { font-size: 11px; color: #8c8c9e; text-transform: uppercase; }
        .stat-value { font-size: 22px; font-weight: 800; color: #ffffff; }
        .summary-box { background-color: #1a1a24; border-radius: 16px; padding: 24px; }
        .summary-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #2a2a3a; }
        .summary-label { color: #8c8c9e; font-size: 14px; }
        .summary-val { color: #ffffff; font-weight: 800; font-size: 16px; }
        </style>
    """, unsafe_allow_html=True)

    col_title, col_year = st.columns([3, 1])
    with col_year:
        selected_year = st.selectbox("Select Season:", options=list(range(current_year, 2011, -1)), index=0)

    with st.spinner(f"Loading {selected_year} Grid Data..."):
        teams_data = fetch_season_teams_and_drivers(selected_year)

    if not teams_data:
        st.info(f"No grid data available for the {selected_year} season.")
        return

    # 1. MINIMAL GRID VIEW
    if st.session_state.selected_team is None:
        with col_title:
            st.markdown(f"<div class='f1-title'>F1 TEAMS {selected_year}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='f1-subtitle'>Find the current Formula 1 teams for the {selected_year} season</div>", unsafe_allow_html=True)

        team_keys = list(teams_data.keys())

        for i in range(0, len(team_keys), 2):
            col1, col2 = st.columns(2)
            cols = [col1, col2]

            for j in range(2):
                if i + j < len(team_keys):
                    team_name = team_keys[i + j]
                    t_data = teams_data[team_name]

                    color = get_team_color(team_name)
                    gradient = f"linear-gradient(135deg, {color} 0%, #0c0d12 100%)"

                    pos_val = format_position(t_data['position'])
                    pts_val = f"{t_data['points']} PTS"

                    logo_path = resolve_asset_path("teams", team_name)
                    logo_b64 = load_raw_image_base64(logo_path)
                    logo_tag = f"<img src='{logo_b64}'/>" if logo_b64 else ""

                    card_html = textwrap.dedent(f"""
                        <div class='team-card-minimal' style='background: {gradient};'>
                            <div>
                                <div class='team-card-title'>{team_name}</div>
                                <div class='team-standing-label'>Constructor Standing</div>
                                <div class='team-standing-val'>{pos_val} <span style='font-size: 14px; opacity: 0.8; font-weight: 500;'>({pts_val})</span></div>
                            </div>
                            <div class='team-logo-badge'>{logo_tag}</div>
                        </div>
                    """).strip()

                    with cols[j]:
                        st.markdown(card_html, unsafe_allow_html=True)
                        if st.button(f"View {team_name} Details", key=f"btn_{team_name}_{selected_year}", use_container_width=True):
                            st.session_state.selected_team = team_name
                            st.rerun()

    # 2. FULL TEAM DETAIL VIEW
    else:
        team_name = st.session_state.selected_team
        t_data = teams_data.get(team_name, {"position": "N/A", "points": "0", "wins": "0", "drivers": []})

        if st.button("← Back to All Teams"):
            st.session_state.selected_team = None
            st.rerun()

        color = get_team_color(team_name)
        gradient = f"linear-gradient(135deg, {color} 0%, #0c0d12 100%)"

        car_path = resolve_asset_path("cars", team_name)
        logo_path = resolve_asset_path("teams", team_name)

        car_b64 = load_raw_image_base64(car_path)
        logo_b64 = load_raw_image_base64(logo_path)
        logo_tag = f"<img src='{logo_b64}' style='width: 30px;'/>" if logo_b64 else ""

        pos_val = format_position(t_data['position'])
        drivers_names = " | ".join([d["full_name"] for d in t_data["drivers"]]) if t_data["drivers"] else team_name

        hero_html = textwrap.dedent(f"""
            <div class='hero-banner' style='background: {gradient};'>
                <img src='{car_b64}' class='hero-car-img'/>
                <div class='hero-title'>{team_name}</div>
                <div style='color: #ffffff; font-size: 18px; font-weight: 700; margin-top: 5px;'>Championship Position: {pos_val} ({t_data['points']} PTS)</div>
                <div style='color: rgba(255,255,255,0.8); font-size: 15px; margin-top: 5px;'>{drivers_names}</div>
                <div style='margin-top: 12px;'>{logo_tag}</div>
            </div>
        """).strip()

        st.markdown(hero_html, unsafe_allow_html=True)

        st.markdown("<div class='stat-section-title'>DRIVERS</div>", unsafe_allow_html=True)
        if t_data["drivers"]:
            d_cols = st.columns(len(t_data["drivers"]))
            for idx, d in enumerate(t_data["drivers"]):
                d_img_path = resolve_asset_path("drivers", d["full_name"])
                d_cutout_b64 = process_driver_cutout(d_img_path)

                d_card_html = textwrap.dedent(f"""
                    <div class='driver-card-podium'>
                        <img src='{d_cutout_b64}' class='driver-podium-img'/>
                        <div class='driver-podium-name'>{d['full_name']}</div>
                        <div class='driver-podium-team'>{team_name} • {d['nationality']}</div>
                        <div class='driver-podium-number' style='color: {color};'>#{d['number']}</div>
                    </div>
                """).strip()

                with d_cols[idx]:
                    st.markdown(d_card_html, unsafe_allow_html=True)

        st.markdown("<div class='stat-section-title'>STATISTICS</div>", unsafe_allow_html=True)
        s_col1, s_col2 = st.columns([1.2, 1])

        with s_col1:
            st.markdown(f"<h3 style='font-weight: 900; text-transform: uppercase;'>{selected_year} SEASON</h3>", unsafe_allow_html=True)

            stats_grid_html = textwrap.dedent(f"""
                <div class='stat-grid-container'>
                    <div class='stat-item'><div class='stat-label'>Season Position</div><div class='stat-value'>{pos_val}</div></div>
                    <div class='stat-item'><div class='stat-label'>Season Points</div><div class='stat-value'>{t_data['points']} PTS</div></div>
                    <div class='stat-item'><div class='stat-label'>Race Wins</div><div class='stat-value'>{t_data['wins']}</div></div>
                    <div class='stat-item'><div class='stat-label'>Active Lineup</div><div class='stat-value'>{len(t_data['drivers'])} Drivers</div></div>
                </div>
            """).strip()
            st.markdown(stats_grid_html, unsafe_allow_html=True)

        with s_col2:
            summary_box_html = textwrap.dedent(f"""
                <div class='summary-box'>
                    <h3 style='font-weight: 900; text-transform: uppercase; margin-top: 0;'>TEAM SUMMARY</h3>
                    <div class='summary-row'><span class='summary-label'>Constructor</span><span class='summary-val'>{team_name}</span></div>
                    <div class='summary-row'><span class='summary-label'>Championship Rank</span><span class='summary-val'>{pos_val}</span></div>
                    <div class='summary-row'><span class='summary-label'>Total Points</span><span class='summary-val'>{t_data['points']}</span></div>
                    <div class='summary-row'><span class='summary-label'>Race Wins</span><span class='summary-val'>{t_data['wins']}</span></div>
                </div>
            """).strip()
            st.markdown(summary_box_html, unsafe_allow_html=True)