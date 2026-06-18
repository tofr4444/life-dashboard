import re
import uuid
import requests
import dash
from dash import html, dcc, callback, Output, Input, State, ALL, ctx
import dash.exceptions
from data.config_utils import load_config, save_config

dash.register_page(__name__, path="/admin", name="Admin")

INPUT_STYLE = {
    "padding": "7px 10px", "borderRadius": "5px",
    "border": "1px solid #ddd", "fontSize": "0.875rem",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def render_widget_toggles(config):
    options = [{"label": v["label"], "value": k}
               for k, v in config["widgets"].items()]
    value = [k for k, v in config["widgets"].items() if v["enabled"]]
    return dcc.Checklist(
        id="widget-checklist",
        options=options,
        value=value,
        labelStyle={"display": "flex", "gap": "8px", "alignItems": "center",
                    "marginBottom": "10px", "cursor": "pointer"},
    )


def render_weather_list(config):
    locations = config.get("weather_locations", [])
    if not locations:
        return html.Div("No weather locations configured.",
                        style={"color": "#aaa", "fontStyle": "italic"})
    rows = []
    for loc in locations:
        rows.append(html.Div([
            html.Div([
                html.Span(loc["title"], style={"fontWeight": "500"}),
                html.Span(f"  —  {loc['label']}",
                          style={"color": "#888", "fontSize": "0.875rem"}),
            ], style={"flex": "1"}),
            html.Button("Remove",
                        id={"type": "remove-weather", "index": loc["id"]},
                        className="btn btn-danger", n_clicks=0),
        ], style={"display": "flex", "alignItems": "center", "padding": "8px 0",
                  "borderBottom": "1px solid #f0f0f0"}))
    return html.Div(rows)


# ── layout ───────────────────────────────────────────────────────────────────

def layout():
    config = load_config()
    return html.Div([
        html.H2("Admin", style={"margin": "0 0 24px"}),

        # Widget toggles
        html.Div([
            html.H3("Widgets", style={"marginTop": 0}),
            html.P("Check to show on the dashboard, uncheck to hide.",
                   style={"color": "#666", "fontSize": "0.875rem", "margin": "0 0 12px"}),
            render_widget_toggles(config),
            html.Div(id="widget-save-msg",
                     style={"color": "#22c55e", "fontSize": "0.875rem", "marginTop": "4px"}),
        ], className="admin-section"),

        # Weather locations
        html.Div([
            html.H3("Weather Locations", style={"marginTop": 0}),
            html.Div(id="weather-location-list", children=render_weather_list(config)),
            html.Div(id="weather-list-msg",
                     style={"color": "#22c55e", "fontSize": "0.875rem", "margin": "8px 0 0"}),

            html.Hr(style={"margin": "20px 0"}),
            html.H4("Add a Location", style={"margin": "0 0 12px"}),
            html.Div([
                dcc.Input(id="city-search-input", type="text",
                          placeholder="City name or 'City, State'", debounce=False,
                          style={**INPUT_STYLE, "width": "200px", "marginRight": "8px"}),
                html.Button("Search", id="city-search-btn",
                            className="btn btn-primary", n_clicks=0),
            ], style={"marginBottom": "12px"}),
            html.Div(id="city-search-results"),
            dcc.Store(id="geocode-store"),
        ], className="admin-section"),

    ], style={"padding": "24px", "maxWidth": "640px"})


# ── callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("widget-save-msg", "children"),
    Input("widget-checklist", "value"),
    prevent_initial_call=True,
)
def save_widget_states(enabled_list):
    config = load_config()
    for k in config["widgets"]:
        config["widgets"][k]["enabled"] = k in (enabled_list or [])
    save_config(config)
    return "Saved — reload the dashboard to see changes."


@callback(
    Output("weather-location-list", "children"),
    Output("weather-list-msg", "children"),
    Input({"type": "remove-weather", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def remove_weather_location(n_clicks):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate
    loc_id = ctx.triggered_id["index"]
    config = load_config()
    config["weather_locations"] = [
        l for l in config["weather_locations"] if l["id"] != loc_id
    ]
    save_config(config)
    return render_weather_list(config), "Location removed — reload the dashboard to see changes."


@callback(
    Output("city-search-results", "children"),
    Output("geocode-store", "data"),
    Input("city-search-btn", "n_clicks"),
    State("city-search-input", "value"),
    prevent_initial_call=True,
)
def search_city(_, city_name):
    if not city_name or not city_name.strip():
        return html.Div("Please enter a city name.", style={"color": "#f59e0b"}), None

    parts = [p.strip() for p in city_name.strip().split(",")]
    search_term = parts[0]
    hint = parts[1].lower() if len(parts) > 1 else ""

    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": search_term, "count": 10},
            timeout=10,
        )
        results = r.json().get("results", [])
    except Exception as e:
        return html.Div(f"Search error: {e}", style={"color": "red"}), None

    if not results:
        return html.Div("No results found.", style={"color": "#f59e0b"}), None

    # If user gave a hint (state abbrev or name), bubble matching results to the top
    if hint:
        def hint_score(res):
            haystack = " ".join(filter(None, [
                res.get("admin1", ""), res.get("admin2", ""),
                res.get("country", ""), res.get("country_code", ""),
            ])).lower()
            return 0 if hint in haystack else 1
        results = sorted(results, key=hint_score)

    # Keep top 5 after re-ranking
    results = results[:5]

    best = results[0]
    options = [
        {
            "label": ", ".join(filter(None, [
                res.get("name"), res.get("admin1"), res.get("country")
            ])),
            "value": i,
        }
        for i, res in enumerate(results)
    ]
    default_title = f"{best['name']} Weather"

    form = html.Div([
        html.Label(f"{len(results)} result(s) found — select the correct one:",
                   style={"fontSize": "0.875rem", "marginBottom": "4px", "display": "block",
                          "fontWeight": "500"}),
        dcc.Dropdown(id="city-result-dropdown", options=options, value=0,
                     clearable=False, style={"marginBottom": "10px"}),
        html.Label("Widget title:", style={"fontSize": "0.875rem", "marginBottom": "4px",
                                            "display": "block"}),
        dcc.Input(id="city-title-input", type="text", value=default_title,
                  style={**INPUT_STYLE, "width": "260px", "marginBottom": "10px",
                         "display": "block"}),
        html.Button("Add to Dashboard", id="add-city-btn",
                    className="btn btn-success", n_clicks=0),
        html.Div(id="add-city-msg", style={"marginTop": "8px", "fontSize": "0.875rem"}),
    ], style={"background": "#f8fafc", "borderRadius": "6px",
              "padding": "14px", "marginTop": "4px"})

    return form, results


@callback(
    Output("weather-location-list", "children", allow_duplicate=True),
    Output("weather-list-msg", "children", allow_duplicate=True),
    Output("city-search-results", "children", allow_duplicate=True),
    Input("add-city-btn", "n_clicks"),
    State("city-result-dropdown", "value"),
    State("city-title-input", "value"),
    State("geocode-store", "data"),
    prevent_initial_call=True,
)
def add_city(_, selected_idx, title, results):
    if results is None or selected_idx is None:
        raise dash.exceptions.PreventUpdate
    r = results[int(selected_idx)]
    base_id = re.sub(r"[^a-z0-9]+", "_", r["name"].lower()).strip("_")
    loc_id = f"{base_id}_{uuid.uuid4().hex[:6]}"
    loc_label = ", ".join(filter(None, [r.get("name"), r.get("admin1")]))
    new_loc = {
        "id": loc_id,
        "title": (title or f"{r['name']} Weather").strip(),
        "lat": r["latitude"],
        "lon": r["longitude"],
        "label": loc_label,
    }
    config = load_config()
    config["weather_locations"].append(new_loc)
    save_config(config)
    return (
        render_weather_list(config),
        f"Added \"{new_loc['title']}\" — reload the dashboard to see it.",
        "",
    )
