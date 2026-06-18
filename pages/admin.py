import re
import uuid
import requests
import dash
from dash import html, dcc, callback, Output, Input, State, ALL, MATCH, ctx, no_update
import dash.exceptions
from data.config_utils import load_config, save_config
from widgets.weather import WEATHER_PREFIX

dash.register_page(__name__, path="/admin", name="Admin")

INPUT_STYLE = {
    "padding": "7px 10px", "borderRadius": "5px",
    "border": "1px solid #ddd", "fontSize": "0.875rem",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def all_widget_options(config):
    """Return all available widgets as dropdown/checklist options."""
    opts = []
    for wid, info in config["widgets"].items():
        opts.append({"value": wid, "label": info["label"]})
    for loc in config["weather_locations"]:
        opts.append({"value": f"{WEATHER_PREFIX}{loc['id']}", "label": loc["title"]})
    return opts


def render_pages_section(config):
    opts = all_widget_options(config)
    sections = []
    for page in config["pages"]:
        sections.append(html.Div([
            html.Div([
                html.H4(page["name"], style={"margin": 0, "flex": "1"}),
                html.Button("Delete Page",
                            id={"type": "delete-page", "index": page["id"]},
                            className="btn btn-danger", n_clicks=0),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
            html.P("Widgets on this page:", style={"margin": "0 0 6px", "fontSize": "0.875rem",
                                                    "color": "#555"}),
            dcc.Checklist(
                id={"type": "page-widgets", "index": page["id"]},
                options=opts,
                value=page.get("widget_ids", []),
                labelStyle={"display": "flex", "gap": "8px", "alignItems": "center",
                            "marginBottom": "6px", "cursor": "pointer"},
            ),
            html.Div(id={"type": "page-save-status", "index": page["id"]},
                     style={"color": "#22c55e", "fontSize": "0.875rem", "marginTop": "4px"}),
        ], style={"marginBottom": "24px", "paddingBottom": "20px",
                  "borderBottom": "1px solid #f0f0f0"}))

    sections.append(html.Div([
        html.P("Create a new page:", style={"margin": "0 0 8px", "fontWeight": "500"}),
        html.Div([
            dcc.Input(id="new-page-name", type="text", placeholder="Page name…",
                      style={**INPUT_STYLE, "width": "180px", "marginRight": "8px"}),
            html.Button("Create Page", id="create-page-btn",
                        className="btn btn-primary", n_clicks=0),
        ]),
        html.Div(id="create-page-msg",
                 style={"color": "#22c55e", "fontSize": "0.875rem", "marginTop": "8px"}),
    ]))

    return html.Div(sections, id="pages-section")


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


# ── layout ────────────────────────────────────────────────────────────────────

def layout():
    config = load_config()
    return html.Div([
        html.H2("Admin", style={"margin": "0 0 24px"}),

        # Pages management
        html.Div([
            html.H3("Pages & Widgets", style={"marginTop": 0}),
            html.P("Each page appears as a tab on the dashboard. "
                   "Check the widgets you want on each page. "
                   "Drag and resize widgets directly on the dashboard.",
                   style={"color": "#666", "fontSize": "0.875rem", "margin": "0 0 16px"}),
            render_pages_section(config),
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
                          style={**INPUT_STYLE, "width": "220px", "marginRight": "8px"}),
                html.Button("Search", id="city-search-btn",
                            className="btn btn-primary", n_clicks=0),
            ], style={"marginBottom": "12px"}),
            html.Div(id="city-search-results"),
            dcc.Store(id="geocode-store"),
        ], className="admin-section"),

    ], style={"padding": "24px", "maxWidth": "680px"})


# ── page management callbacks ─────────────────────────────────────────────────

@callback(
    Output({"type": "page-save-status", "index": MATCH}, "children"),
    Input({"type": "page-widgets", "index": MATCH}, "value"),
    State({"type": "page-widgets", "index": MATCH}, "id"),
    prevent_initial_call=True,
)
def save_page_widgets(widget_ids, component_id):
    page_id = component_id["index"]
    widget_ids = widget_ids or []
    config = load_config()
    for page in config["pages"]:
        if page["id"] == page_id:
            page["widget_ids"] = widget_ids
            # Drop layout entries for removed widgets
            if "layout" in page:
                page["layout"]["lg"] = [
                    item for item in page["layout"].get("lg", [])
                    if item["i"] in widget_ids
                ]
            break
    save_config(config)
    return "Saved — reload the dashboard to apply."


@callback(
    Output("pages-section", "children"),
    Output("create-page-msg", "children"),
    Input("create-page-btn", "n_clicks"),
    State("new-page-name", "value"),
    prevent_initial_call=True,
)
def create_page(_, name):
    if not name or not name.strip():
        return no_update, "Please enter a page name."
    config = load_config()
    base_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    page_id = base_id
    if any(p["id"] == page_id for p in config["pages"]):
        page_id = f"{base_id}_{uuid.uuid4().hex[:4]}"
    config["pages"].append({
        "id": page_id,
        "name": name.strip(),
        "widget_ids": [],
        "layout": {"lg": []},
    })
    save_config(config)
    return render_pages_section(config), f'Page "{name.strip()}" created.'


@callback(
    Output("pages-section", "children", allow_duplicate=True),
    Output("create-page-msg", "children", allow_duplicate=True),
    Input({"type": "delete-page", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def delete_page(n_clicks):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate
    page_id = ctx.triggered_id["index"]
    config = load_config()
    config["pages"] = [p for p in config["pages"] if p["id"] != page_id]
    save_config(config)
    return render_pages_section(config), "Page deleted."


# ── weather location callbacks ────────────────────────────────────────────────

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
    wid = f"{WEATHER_PREFIX}{loc_id}"
    config = load_config()
    config["weather_locations"] = [
        l for l in config["weather_locations"] if l["id"] != loc_id
    ]
    # Also remove from all pages
    for page in config["pages"]:
        page["widget_ids"] = [w for w in page.get("widget_ids", []) if w != wid]
        if "layout" in page:
            page["layout"]["lg"] = [
                item for item in page["layout"].get("lg", []) if item["i"] != wid
            ]
    save_config(config)
    return render_weather_list(config), "Location removed — reload the dashboard."


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
    if hint:
        def hint_score(res):
            haystack = " ".join(filter(None, [
                res.get("admin1", ""), res.get("admin2", ""),
                res.get("country", ""), res.get("country_code", ""),
            ])).lower()
            return 0 if hint in haystack else 1
        results = sorted(results, key=hint_score)
    results = results[:5]
    best = results[0]
    options = [
        {"label": ", ".join(filter(None, [r.get("name"), r.get("admin1"), r.get("country")])),
         "value": i}
        for i, r in enumerate(results)
    ]
    form = html.Div([
        html.Label(f"{len(results)} result(s) — select the correct one:",
                   style={"fontSize": "0.875rem", "fontWeight": "500",
                          "marginBottom": "4px", "display": "block"}),
        dcc.Dropdown(id="city-result-dropdown", options=options, value=0,
                     clearable=False, style={"marginBottom": "10px"}),
        html.Label("Widget title:", style={"fontSize": "0.875rem",
                                            "marginBottom": "4px", "display": "block"}),
        dcc.Input(id="city-title-input", type="text",
                  value=f"{best['name']} Weather",
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
    Output("pages-section", "children", allow_duplicate=True),
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
        f'Added "{new_loc["title"]}" — assign it to a page below, then reload the dashboard.',
        "",
        render_pages_section(config),
    )
