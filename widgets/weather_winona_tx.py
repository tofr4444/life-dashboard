from widgets.weather import build_layout, build_callback

LAT, LON, LABEL = 32.4896, -95.1672, "Winona, TX"
WIDGET_ID = "weather-winona-tx"

build_callback(WIDGET_ID, LAT, LON, LABEL)


def layout():
    return build_layout(WIDGET_ID)
