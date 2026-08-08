import streamlit as st


def hero(
    race,
    circuit_image,
    car_image,
    countdown
):
    days = countdown.days
    hours = countdown.seconds // 3600

    left, right = st.columns([1.2, 1])

    with left:
        if circuit_image:
            st.image(
                circuit_image,
                use_container_width=True
            )

    with right:
        if car_image:
            st.image(
                car_image,
                use_container_width=True
            )

        event_name = race.get('EventName', 'Upcoming Race')
        location = race.get('Location', '')
        round_num = int(race.get('RoundNumber', 0))
        
        session_date = race.get('Session5Date')
        date_str = session_date.strftime('%d %B %Y') if session_date else "TBD"

        st.markdown(
            f"""
## {event_name}

### {location}

Round {round_num}

{date_str}
"""
        )

        st.markdown("---")

        c1, c2 = st.columns(2)

        c1.metric("Days", days)
        c2.metric("Hours", hours)