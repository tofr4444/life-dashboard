import datetime
import requests
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go

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
    now = datetime.datetime.now()

    times, temps, feels, precip_prob = [], [], [], []
    for i, t in enumerate(hourly["time"]):
        dt = datetime.datetime.fromisoformat(t)
        if dt.date() == now.date():
            times.append(dt.strftime("%I %p").lstrip("0"))
            temps.append(hourly["temperature_2m"][i])
            feels.append(hourly["apparent_temperature"][i])
            precip_prob.append(hourly["precipitation_probability"][i])

    now_label = now.strftime("%I %p").lstrip("0")

    fig = go.Figure()
    fig.add_vline(
        x=now_label,
        line=dict(color="#6366f1", width=2, dash="dash"),
        annotation_text="Now",
        annotation_position="top",
        annotation_font=dict(color="#6366f1", size=11),
    )
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
    return fig


def build_layout(widget_id, title="Weather"):
    return html.Div([
        html.H3(title, style={"marginTop": 0}),
        html.Div(id=f"{widget_id}-summary", style={"marginBottom": "10px"}),
        dcc.Graph(id=f"{widget_id}-chart", config={"displayModeBar": False}),
        html.Div(id=f"{widget_id}-details", style={"fontSize": "0.8rem", "color": "#666", "marginTop": "8px"}),
        dcc.Interval(id=f"{widget_id}-interval", interval=30 * 60 * 1000, n_intervals=0),
    ])


def build_callback(widget_id, lat, lon, label):
    @callback(
        Output(f"{widget_id}-summary", "children"),
        Output(f"{widget_id}-chart", "figure"),
        Output(f"{widget_id}-details", "children"),
        Input(f"{widget_id}-interval", "n_intervals"),
    )
    def update(_):
        try:
            data = fetch_weather(lat, lon)
        except Exception as e:
            return f"Error: {e}", go.Figure(), ""

        daily = data["daily"]
        code = daily["weathercode"][0]
        desc, icon = WMO_CODES.get(code, ("Unknown", "🌡️"))
        hi = daily["temperature_2m_max"][0]
        lo = daily["temperature_2m_min"][0]
        sunrise = daily["sunrise"][0][11:]
        sunset = daily["sunset"][0][11:]

        now_hour = datetime.datetime.now().hour
        hourly = data["hourly"]
        current_temp = hourly["temperature_2m"][now_hour]
        current_feels = hourly["apparent_temperature"][now_hour]
        current_humid = hourly["relativehumidity_2m"][now_hour]
        current_wind = hourly["windspeed_10m"][now_hour]

        summary = html.Div([
            html.Span(f"{icon} {desc}  ", style={"fontSize": "1.1rem"}),
            html.Span(f"{current_temp:.0f}°F", style={"fontSize": "1.8rem", "fontWeight": "bold"}),
            html.Span(f"  feels {current_feels:.0f}°F", style={"color": "#888"}),
            html.Div(f"H: {hi:.0f}°  L: {lo:.0f}°  |  {label}", style={"color": "#666", "fontSize": "0.85rem"}),
        ])
        details = f"Humidity: {current_humid}%  |  Wind: {current_wind:.0f} mph  |  Sunrise: {sunrise}  |  Sunset: {sunset}"
        return summary, hourly_chart(data), details

    return update


# Marietta, GA — 1255 Lake Colony Drive
LAT, LON, LABEL = 33.9787, -84.4063, "Marietta, GA"
WIDGET_ID = "weather-marietta"

build_callback(WIDGET_ID, LAT, LON, LABEL)


def layout():
    return build_layout(WIDGET_ID, title="Home Weather")
