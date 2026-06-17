from dash import html, dcc, callback, Output, Input
import datetime

WIDGET_NAME = "Clock"


def layout():
    return html.Div([
        html.H3("Date & Time", style={"marginTop": 0}),
        html.Div(id="clock-display", style={"fontSize": "2rem", "fontWeight": "bold"}),
        html.Div(id="date-display", style={"color": "#666"}),
        dcc.Interval(id="clock-interval", interval=1000, n_intervals=0),
    ])


@callback(
    Output("clock-display", "children"),
    Output("date-display", "children"),
    Input("clock-interval", "n_intervals"),
)
def update_clock(_):
    now = datetime.datetime.now()
    return now.strftime("%H:%M:%S"), now.strftime("%A, %B %d %Y")
