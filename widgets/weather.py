import datetime
from zoneinfo import ZoneInfo
import requests
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go
from data.config_utils import load_config

WMO_CODES = {
    0: ("Clear", "☀️"), 1: ("Mostly Clear", "🌤️"), 2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Foggy", "🌫️"), 48: ("Icy Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy Drizzle", "🌧️"),
    61: ("Light Rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Heavy Rain", "🌧️"),
    71: ("Light Snow", "🌨️"), 73: ("Snow", "❄️"), 75: ("Heavy Snow", "❄️"),
    80: ("Rain Showers", "🌦️"), 81: ("Showers", "🌧️"), 82: ("Heavy Showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm+Hail", "⛈️"), 99: ("Severe Storm", "⛈️"),
}


def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,apparent_temperature,precipitation_probability,"
        "precipitation,weathercode,windspeed_10m,relativehumidity_2m"
        "&daily=temperature_2m_max,temperature_2m_min,weathercode,sunrise,sunset"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
        "&timezone=auto&forecast_days=1"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def hourly_chart(data):
    hourly = data["hourly"]
    tz = ZoneInfo(data["timezone"])
    now = datetime.datetime.now(tz)

    times, temps, feels, precip_prob = [], [], [], []
    for i, t in enumerate(hourly["time"]):
        dt = datetime.datetime.fromisoformat(t).replace(tzinfo=tz)
        if dt.date() == now.date():
            times.append(dt.strftime("%I %p").lstrip("0"))
            temps.append(hourly["temperature_2m"][i])
            feels.append(hourly["apparent_temperature"][i])
            precip_prob.append(hourly["precipitation_probability"][i])

    now_label = now.strftime("%I %p").lstrip("0")
    now_idx = times.index(now_label) if now_label in times else None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=temps, name="Temp °F", mode="lines+markers",
        line=dict(color="#f97316", width=2), marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=times, y=feels, name="Feels Like", mode="lines",
        line=dict(color="#fb923c", width=1.5, dash="dot"),
    ))
    fig.add_trace(go.Bar(
        x=times, y=precip_prob, name="Rain %", yaxis="y2",
        marker_color="rgba(59,130,246,0.25)",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=220,
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=11)),
        yaxis=dict(title="°F", tickfont=dict(size=11), gridcolor="#f0f0f0"),
        yaxis2=dict(title="Rain %", overlaying="y", side="right",
                    range=[0, 100], tickfont=dict(size=11), showgrid=False),
        xaxis=dict(tickfont=dict(size=11)),
        font=dict(family="sans-serif"),
    )
    if now_idx is not None:
        fig.update_layout(
            shapes=[dict(
                type="line", xref="x", yref="paper",
                x0=now_idx, x1=now_idx, y0=0, y1=1,
                line=dict(color="#6366f1", width=2, dash="dash"),
            )],
            annotations=[dict(
                xref="x", yref="paper",
                x=now_idx, y=1.02,
                text="Now", showarrow=False,
                font=dict(color="#6366f1", size=11),
            )],
        )
    return fig


def render_location_panel(loc, data):
    tz = ZoneInfo(data["timezone"])
    now_hour = datetime.datetime.now(tz).hour
    hourly = data["hourly"]
    daily = data["daily"]

    code = daily["weathercode"][0]
    desc, icon = WMO_CODES.get(code, ("Unknown", "🌡️"))
    hi = daily["temperature_2m_max"][0]
    lo = daily["temperature_2m_min"][0]
    sunrise = daily["sunrise"][0][11:]
    sunset = daily["sunset"][0][11:]

    current_temp = hourly["temperature_2m"][now_hour]
    current_feels = hourly["apparent_temperature"][now_hour]
    current_humid = hourly["relativehumidity_2m"][now_hour]
    current_wind = hourly["windspeed_10m"][now_hour]

    summary = html.Div([
        html.Span(f"{icon} {desc}  ", style={"fontSize": "1.1rem"}),
        html.Span(f"{current_temp:.0f}°F", style={"fontSize": "1.8rem", "fontWeight": "bold"}),
        html.Span(f"  feels {current_feels:.0f}°F", style={"color": "#888"}),
        html.Div(f"H: {hi:.0f}°  L: {lo:.0f}°  |  {loc['label']}",
                 style={"color": "#666", "fontSize": "0.85rem"}),
    ])
    details = (f"Humidity: {current_humid}%  |  Wind: {current_wind:.0f} mph  |  "
               f"Sunrise: {sunrise}  |  Sunset: {sunset}")

    return html.Div([
        html.H3(loc["title"], style={"marginTop": 0}),
        html.Div(summary, style={"marginBottom": "10px"}),
        dcc.Graph(id=f"weather-chart-{loc['id']}", figure=hourly_chart(data),
                  config={"displayModeBar": False}),
        html.Div(details, style={"fontSize": "0.8rem", "color": "#666", "marginTop": "8px"}),
    ], className="widget")


def layout():
    return html.Div([
        html.Div(id="weather-panels", className="widget-grid",
                 style={"paddingTop": 0}),
        dcc.Interval(id="weather-interval", interval=30 * 60 * 1000, n_intervals=0),
    ])


@callback(Output("weather-panels", "children"), Input("weather-interval", "n_intervals"))
def update_all_weather(_):
    config = load_config()
    locations = config.get("weather_locations", [])
    if not locations:
        return html.Div("No weather locations configured. Add some in Admin.",
                        style={"color": "#aaa", "padding": "20px"})
    panels = []
    for loc in locations:
        try:
            data = fetch_weather(loc["lat"], loc["lon"])
            panels.append(render_location_panel(loc, data))
        except Exception as e:
            panels.append(html.Div([
                html.H3(loc["title"], style={"marginTop": 0}),
                html.Div(f"Error: {e}", style={"color": "red"}),
            ], className="widget"))
    return panels
