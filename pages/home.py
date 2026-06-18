import dash
import dash_draggable
from dash import html, dcc, callback, Output, Input, no_update
from data.config_utils import load_config, save_config
from widgets import clock, google_calendar, weather  # noqa: F401 — registers callbacks
from widgets.weather import WEATHER_PREFIX, weather_grid_child

dash.register_page(__name__, path="/")

ROW_HEIGHT = 80
DEFAULT_W = 4
DEFAULT_H = 6


def get_widget_label(widget_id, config):
    if widget_id in config["widgets"]:
        return config["widgets"][widget_id]["label"]
    if widget_id.startswith(WEATHER_PREFIX):
        loc_id = widget_id[len(WEATHER_PREFIX):]
        loc = next((l for l in config["weather_locations"] if l["id"] == loc_id), None)
        if loc:
            return loc["title"]
    return widget_id


def build_grid_child(widget_id):
    if widget_id == "clock":
        return html.Div(clock.layout(), id="clock", className="widget",
                        style={"height": "100%", "overflow": "auto", "boxSizing": "border-box"})
    if widget_id == "google_calendar":
        return html.Div(google_calendar.layout(), id="google_calendar", className="widget",
                        style={"height": "100%", "overflow": "auto", "boxSizing": "border-box"})
    if widget_id.startswith(WEATHER_PREFIX):
        return weather_grid_child(widget_id[len(WEATHER_PREFIX):])
    return None


def ensure_layout(page):
    """Add default layout entries for any widget without one, drop entries for removed widgets."""
    lg = page.get("layout", {}).get("lg", [])
    existing = {item["i"] for item in lg}
    y_max = max((item["y"] + item["h"] for item in lg), default=0)
    x = 0
    for wid in page["widget_ids"]:
        if wid not in existing:
            lg.append({"i": wid, "x": x % 12, "y": y_max, "w": DEFAULT_W, "h": DEFAULT_H})
            x += DEFAULT_W
    lg = [item for item in lg if item["i"] in page["widget_ids"]]
    page["layout"] = {"lg": lg}
    return page


def layout():
    config = load_config()
    pages = config.get("pages", [])
    if not pages:
        return html.Div("No pages configured. Go to Admin to create one.",
                        style={"padding": "40px", "textAlign": "center", "color": "#aaa"})

    first_id = pages[0]["id"]
    return html.Div([
        dcc.Tabs(
            [dcc.Tab(label=p["name"], value=p["id"]) for p in pages],
            id="page-tabs",
            value=first_id,
            style={"background": "white", "paddingLeft": "16px",
                   "borderBottom": "1px solid #e2e8f0"},
        ),
        html.Div(id="page-content"),
        dcc.Store(id="page-widgets-store"),
        dcc.Interval(id="weather-interval", interval=30 * 60 * 1000, n_intervals=0),
    ])


@callback(
    Output("page-content", "children"),
    Output("page-widgets-store", "data"),
    Input("page-tabs", "value"),
)
def render_page(page_id):
    config = load_config()
    page = next((p for p in config["pages"] if p["id"] == page_id), None)
    if not page:
        return html.Div("Page not found."), {}

    page = ensure_layout(page)
    children = [build_grid_child(wid) for wid in page["widget_ids"]]
    children = [c for c in children if c is not None]

    if not children:
        return html.Div("No widgets on this page. Add some in Admin.",
                        style={"padding": "40px", "textAlign": "center", "color": "#aaa"}), {}

    grid = dash_draggable.ResponsiveGridLayout(
        id="draggable-grid",
        children=children,
        layouts=page["layout"],
        save=False,
        height=ROW_HEIGHT,
        gridCols={"lg": 12, "md": 12, "sm": 6, "xs": 4, "xxs": 2},
        style={"padding": "16px"},
    )
    return grid, {"page_id": page_id, "widget_ids": page["widget_ids"]}


@callback(
    Output("page-widgets-store", "data", allow_duplicate=True),
    Input("draggable-grid", "layouts"),
    Input("page-tabs", "value"),
    prevent_initial_call=True,
)
def save_layout(layouts, page_id):
    if not layouts:
        return no_update
    config = load_config()
    for page in config["pages"]:
        if page["id"] == page_id:
            page["layout"] = layouts
            break
    save_config(config)
    return no_update
