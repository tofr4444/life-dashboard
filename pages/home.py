import dash
from dash import html
from data.config_utils import load_config
from widgets import clock, google_calendar, weather  # noqa: F401 — registers callbacks

dash.register_page(__name__, path="/")


def layout():
    config = load_config()

    non_weather = []
    if config["widgets"]["clock"]["enabled"]:
        non_weather.append(html.Div(clock.layout(), className="widget"))
    if config["widgets"]["google_calendar"]["enabled"]:
        non_weather.append(html.Div(google_calendar.layout(), className="widget"))

    sections = []
    if non_weather:
        sections.append(html.Div(non_weather, className="widget-grid",
                                  style={"paddingBottom": 0}))
    sections.append(weather.layout())

    return html.Div(sections)
