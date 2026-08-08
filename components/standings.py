import streamlit as st
from components.cards import (
    driver_card,
    small_driver_row
)
from utils.asset_manager import get_driver_image
from utils.image_processing import preprocess_driver


def driver_standings(df):
    st.markdown("## Driver Championship")

    if df.empty:
        st.info("No driver standings data available.")
        return

    # Top 3 Podium Cards
    top3 = df.head(3)
    cols = st.columns(min(3, len(top3)))

    for idx, (_, row) in enumerate(top3.iterrows()):
        with cols[idx]:
            raw_img = get_driver_image(row["Driver"])
            processed_img = preprocess_driver(raw_img) if raw_img else None

            driver_card(
                idx + 1,
                row["Driver"],
                row["Team"],
                row["Points"],
                processed_img
            )

    # All Remaining Positions (P4 onwards)
    rest = df.iloc[3:]

    if not rest.empty:
        st.markdown("### Remaining Standings")

        for idx, (_, row) in enumerate(rest.iterrows(), start=4):
            raw_img = get_driver_image(row["Driver"])
            processed_img = preprocess_driver(raw_img) if raw_img else None

            small_driver_row(
                idx,
                row["Driver"],
                row["Team"],
                row["Points"],
                processed_img
            )