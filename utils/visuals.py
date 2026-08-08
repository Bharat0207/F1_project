import plotly.express as px
import plotly.graph_objects as go


# ===================================================
# TEAM COLORS
# ===================================================

TEAM_COLORS = {
    "Red Bull": "#0600EF",
    "Ferrari": "#DC0000",
    "Mercedes": "#00D2BE",
    "McLaren": "#FF8700",
    "Aston Martin": "#006F62",
    "Alpine": "#0090FF",
    "Williams": "#005AFF",
    "RB": "#2B4562",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#FFFFFF"
}


# ===================================================
# DRIVER STANDINGS
# ===================================================

def plot_driver_points(df):

    df = df.sort_values("Points", ascending=True)

    fig = px.bar(
        df,
        x="Points",
        y="Driver",
        orientation="h",
        color="Team",
        text="Points",
        title="Driver Championship Standings",
        color_discrete_map=TEAM_COLORS
    )

    fig.update_traces(
        textposition="outside",
        marker_line_width=0
    )

    fig.update_layout(
        template="plotly_dark",
        height=650,
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        font=dict(size=14),
        yaxis=dict(title=""),
        xaxis=dict(title="Points"),
        legend_title="Team",
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig


# ===================================================
# CONSTRUCTOR STANDINGS
# ===================================================

def plot_constructor_points(df):

    df = df.sort_values("Points", ascending=False)

    fig = px.bar(
        df,
        x="Team",
        y="Points",
        color="Team",
        text="Points",
        title="Constructor Championship",
        color_discrete_map=TEAM_COLORS
    )

    fig.update_traces(
        textposition="outside",
        marker_line_width=0
    )

    fig.update_layout(
        template="plotly_dark",
        height=550,
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        font=dict(size=14),
        xaxis=dict(title=""),
        yaxis=dict(title="Points"),
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig


# ===================================================
# FASTEST LAPS
# ===================================================

def plot_fastest_laps(df):

    df = df.sort_values("LapTime (s)", ascending=True)

    fig = px.bar(
        df,
        x="Driver",
        y="LapTime (s)",
        color="Driver",
        text="LapTime (s)",
        title="Fastest Lap Comparison"
    )

    fig.update_traces(
        textposition="outside",
        marker_line_width=0
    )

    fig.update_layout(
        template="plotly_dark",
        height=500,
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        xaxis=dict(title="Driver"),
        yaxis=dict(title="Lap Time (seconds)"),
        showlegend=False
    )

    return fig


# ===================================================
# DRIVER COMPARISON
# ===================================================

def plot_driver_comparison(df):

    fig = px.line(
        df,
        x="LapNumber",
        y="LapTime",
        color="Driver",
        line_shape="spline",
        title="Lap Time Comparison"
    )

    fig.update_traces(
        line=dict(width=3)
    )

    fig.update_layout(
        template="plotly_dark",
        height=550,
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        xaxis=dict(title="Lap Number"),
        yaxis=dict(title="Lap Time (seconds)")
    )

    return fig


# ===================================================
# TRACK MAP
# ===================================================

def plot_track(df):

    import plotly.graph_objects as go

    fig = go.Figure()

    drivers = df["Driver"].unique()

    # Draw racing lines
    for drv in drivers:

        drv_df = df[df["Driver"] == drv]

        fig.add_trace(
            go.Scatter(
                x=drv_df["X"],
                y=drv_df["Y"],
                mode="lines",
                name=f"{drv} Racing Line",
                line=dict(width=4),
                opacity=0.4
            )
        )

        # Current position marker
        latest = drv_df.iloc[-1]

        fig.add_trace(
            go.Scatter(
                x=[latest["X"]],
                y=[latest["Y"]],
                mode="markers+text",
                text=[drv],
                textposition="top center",
                name=drv,
                marker=dict(
                    size=14,
                    line=dict(
                        width=2,
                        color="white"
                    )
                )
            )
        )

    fig.update_layout(
        title="Track Map",
        template="plotly_dark",
        height=850,
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",

        xaxis=dict(
            visible=False
        ),

        yaxis=dict(
            visible=False,
            scaleanchor="x",
            scaleratio=1
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig



# ===================================================
# RACE REPLAY
# ===================================================

def plot_replay(df):

    import plotly.graph_objects as go

    drivers = df["Driver"].unique()

    first_frame = df["Frame"].min()

    initial_df = df[df["Frame"] == first_frame]

    fig = go.Figure()

    # -----------------------------------------
    # TRACK OUTLINE
    # -----------------------------------------

    fig.add_trace(

        go.Scatter(
            x=df["X"],
            y=df["Y"],
            mode="lines",
            line=dict(
                color="white",
                width=5
            ),
            opacity=0.25,
            name="Track"
        )
    )

    # -----------------------------------------
    # INITIAL DRIVER POSITIONS
    # -----------------------------------------

    for drv in drivers:

        drv_df = initial_df[
            initial_df["Driver"] == drv
        ]

        if drv_df.empty:
            continue

        fig.add_trace(

            go.Scatter(
                x=drv_df["X"],
                y=drv_df["Y"],

                mode="markers+text",

                text=[drv],

                textposition="top center",

                marker=dict(
                    size=18
                ),

                name=drv
            )
        )

    # -----------------------------------------
    # ANIMATION FRAMES
    # -----------------------------------------

    frames = []

    for frame in sorted(df["Frame"].unique()):

        frame_df = df[df["Frame"] == frame]

        frame_data = [

            go.Scatter(
                x=df["X"],
                y=df["Y"],
                mode="lines",
                line=dict(
                    color="white",
                    width=5
                ),
                opacity=0.25,
                showlegend=False
            )
        ]

        for drv in drivers:

            drv_df = frame_df[
                frame_df["Driver"] == drv
            ]

            if drv_df.empty:
                continue

            frame_data.append(

                go.Scatter(
                    x=drv_df["X"],
                    y=drv_df["Y"],

                    mode="markers+text",

                    text=[drv],

                    textposition="top center",

                    marker=dict(
                        size=20
                    ),

                    name=drv
                )
            )

        frames.append(

            go.Frame(
                data=frame_data,
                name=str(frame)
            )
        )

    fig.frames = frames

    # -----------------------------------------
    # PLAY BUTTON
    # -----------------------------------------

    fig.update_layout(

        template="plotly_dark",

        height=900,

        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",

        title="Live Race Replay",

        xaxis=dict(
            visible=False
        ),

        yaxis=dict(
            visible=False,
            scaleanchor="x",
            scaleratio=1
        ),

        updatemenus=[

            dict(
                type="buttons",

                buttons=[

                    dict(
                        label="Play Replay",

                        method="animate",

                        args=[
                            None,
                            {
                                "frame": {
                                    "duration": 80,
                                    "redraw": True
                                },

                                "fromcurrent": True,

                                "transition": {
                                    "duration": 0
                                }
                            }
                        ]
                    )
                ],

                showactive=False,
                x=0.1,
                y=1.1
            )
        ]
    )

    return fig



# ===================================================
# TYRE STRATEGY V2
# ===================================================

def plot_tyre_strategy(df):

    import plotly.graph_objects as go

    compound_colors = {

        "SOFT": "#FF2D2D",
        "MEDIUM": "#FFD800",
        "HARD": "#EDEDED",
        "INTERMEDIATE": "#39FF14",
        "WET": "#00AEEF"
    }

    # -----------------------------------------
    # SORT DRIVERS
    # -----------------------------------------

    driver_order = list(df["Driver"].cat.categories)

    fig = go.Figure()

    # -----------------------------------------
    # BUILD STINTS
    # -----------------------------------------

    for _, row in df.iterrows():

        compound = row["Compound"]

        color = compound_colors.get(
            compound,
            "#888888"
        )

        fig.add_trace(

            go.Bar(

                x=[row["StintLength"]],

                y=[row["Driver"]],

                base=row["LapStart"],

                orientation="h",

                marker=dict(
                    color=color,
                    line=dict(
                        color="black",
                        width=1
                    )
                ),

                hovertemplate=
                f"""
                Driver: {row['Driver']}<br>
                Compound: {compound}<br>
                Start Lap: {row['LapStart']}<br>
                End Lap: {row['LapEnd']}<br>
                Stint Length: {row['StintLength']} laps
                <extra></extra>
                """,

                showlegend=False
            )
        )

        # -------------------------------------
        # PIT STOP MARKERS
        # -------------------------------------

        fig.add_trace(

            go.Scatter(

                x=[row["LapEnd"]],

                y=[row["Driver"]],

                mode="markers",

                marker=dict(
                    symbol="diamond",
                    size=7,
                    color="white"
                ),

                showlegend=False,

                hoverinfo="skip"
            )
        )

    # -----------------------------------------
    # LAYOUT
    # -----------------------------------------

    fig.update_layout(

        template="plotly_dark",

        title=dict(
            text="Tyre Strategy Analysis",
            x=0.5
        ),

        height=850,

        barmode="overlay",

        plot_bgcolor="#0B0F19",
        paper_bgcolor="#0B0F19",

        font=dict(
            size=14
        ),

        xaxis=dict(
            title="Lap Number",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)"
        ),

        yaxis=dict(
            title="Driver",
            categoryorder="array",
            categoryarray=driver_order
        ),

        margin=dict(
            l=40,
            r=40,
            t=80,
            b=40
        )
    )

    return fig

# ===================================================
# POSITION CHANGES
# ===================================================

def plot_position_changes(df):

    import plotly.express as px

    fig = px.line(

        df,

        x="LapNumber",

        y="Position",

        color="Driver",

        markers=True,

        title="Race Position Changes"
    )

    fig.update_traces(
        line=dict(width=3)
    )

    fig.update_layout(

        template="plotly_dark",

        height=850,

        plot_bgcolor="#0B0F19",
        paper_bgcolor="#0B0F19",

        xaxis=dict(
            title="Lap Number",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)"
        ),

        yaxis=dict(
            title="Race Position",
            autorange="reversed",
            dtick=1
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

# ===================================================
# GAP TO LEADER
# ===================================================

def plot_gap_to_leader(df):

    import plotly.express as px

    fig = px.line(

        df,

        x="LapNumber",

        y="GapToLeader",

        color="Driver",

        line_shape="spline",

        title="Gap To Race Leader"
    )

    fig.update_traces(
        line=dict(width=3)
    )

    fig.update_layout(

        template="plotly_dark",

        height=850,

        plot_bgcolor="#0B0F19",
        paper_bgcolor="#0B0F19",

        xaxis=dict(
            title="Lap Number",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)"
        ),

        yaxis=dict(
            title="Gap To Leader (seconds)"
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

# ===================================================
# TELEMETRY COMPARISON
# ===================================================

def plot_speed_comparison(df1, df2, driver1, driver2):

    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df1["Distance"],
            y=df1["Speed"],
            name=driver1
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df2["Distance"],
            y=df2["Speed"],
            name=driver2
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title="Speed Comparison",
        xaxis_title="Distance (m)",
        yaxis_title="Speed (km/h)",
        height=600
    )

    return fig

def plot_delta_chart(delta_time, ref_tel):

    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=ref_tel["Distance"],

            y=delta_time,

            fill="tozeroy",

            name="Lap Delta"
        )
    )

    fig.update_layout(

        template="plotly_dark",

        title="Lap Delta Analysis",

        xaxis_title="Distance (m)",

        yaxis_title="Delta Time (s)",

        height=600
    )

    return fig

# ===================================================
# THROTTLE COMPARISON
# ===================================================

def plot_throttle_comparison(
    df1,
    df2,
    driver1,
    driver2
):

    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df1["Distance"],
            y=df1["Throttle"],
            name=driver1
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df2["Distance"],
            y=df2["Throttle"],
            name=driver2
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title="Throttle Comparison",
        xaxis_title="Distance (m)",
        yaxis_title="Throttle (%)",
        height=500
    )

    return fig


# ===================================================
# BRAKE COMPARISON
# ===================================================

def plot_brake_comparison(
    df1,
    df2,
    driver1,
    driver2
):

    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df1["Distance"],
            y=df1["Brake"].astype(int),
            name=driver1
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df2["Distance"],
            y=df2["Brake"].astype(int),
            name=driver2
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title="Brake Usage Comparison",
        xaxis_title="Distance (m)",
        yaxis_title="Brake",
        height=500
    )

    return fig