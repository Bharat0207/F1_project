def get_driver_telemetry(session, driver):

    lap = (
        session.laps
        .pick_drivers(driver)
        .pick_fastest()
    )

    telemetry = lap.get_car_data().add_distance()

    return telemetry

import fastf1.utils


def get_lap_delta(session, driver1, driver2):

    lap1 = (
        session.laps
        .pick_drivers(driver1)
        .pick_fastest()
    )

    lap2 = (
        session.laps
        .pick_drivers(driver2)
        .pick_fastest()
    )

    delta_time, ref_tel, compare_tel = fastf1.utils.delta_time(
        lap1,
        lap2
    )

    return delta_time, ref_tel, compare_tel