import os
import base64
import streamlit as st

FALLBACK_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


def image_to_base64(path):
    if not path or not os.path.exists(path):
        return FALLBACK_IMAGE

    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        ext = os.path.splitext(path)[1].lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }
        mime = mime_types.get(ext, "image/jpeg")

        return f"data:{mime};base64,{encoded}"
    except Exception as e:
        return FALLBACK_IMAGE


def driver_card(
        position,
        name,
        team,
        points,
        image_path,
        team_color="#333333"
):
    img = image_to_base64(image_path)

    st.markdown(
        f"""
        <div class="driver-card" style="
            border-top: 4px solid {team_color};
            background-color: #111827;
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
            margin-bottom: 20px;
        ">
            <div class="position" style="font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 8px;">P{position}</div>
            <img class="driver-image" src="{img}" alt="{name}" style="height: 220px; object-fit: contain; margin-bottom: 12px;">
            <div class="driver-name" style="font-size: 16px; font-weight: 700; color: #FFFFFF;">{name}</div>
            <div class="driver-team" style="font-size: 13px; color: #9CA3AF; margin-top: 2px;">{team}</div>
            <div class="driver-points" style="font-size: 18px; font-weight: 800; color: #E10600; margin-top: 10px;">{points} pts</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def small_driver_row(
        position,
        name,
        team,
        points,
        image_path
):
    img = image_to_base64(image_path)

    st.markdown(
        f"""
        <div class="small-row" style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: #111827;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="small-pos" style="font-weight: 700; color: #9CA3AF; width: 30px;">P{position}</div>
                <img class="avatar" src="{img}" alt="{name}" style="height: 50px; width: 50px; object-fit: contain; border-radius: 50%;">
                <div class="small-info" style="display: flex; flex-direction: column;">
                    <b style="color: #FFFFFF; font-size: 15px;">{name}</b>
                    <span style="color: #9CA3AF; font-size: 12px;">{team}</span>
                </div>
            </div>
            <div class="small-points" style="font-size: 15px; font-weight: 700; color: #E10600;">{points} pts</div>
        </div>
        """,
        unsafe_allow_html=True
    )