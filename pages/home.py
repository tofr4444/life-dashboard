import dash
import dash_draggable
from dash import html, dcc, callback, Output, Input, State, no_update
from data.config_utils import load_config, save_config
from widgets import clock, google_calendar, weather  # noqa: F401 — registers callbacks
from widgets.weather import WEATHER_PREFIX

dash.register_page(__name__, path="/")

ROW_HEIGHT = 80
DEFAULT_W = 4
DEFAULT_H = 6


def build_grid_child(widget_id, layout_item):
    """Wrap each widget in DashboardItem so the grid tracks it by widget_id, not array index."""
    x = layout_item.get("x", 0)
    y = layout_item.get("y", 0)
    w = layout_item.get("w", DEFAULT_W)
    h = layout_item.get("h", DEFAULT_H)

    if widget_id == "clock":
        content = html.Div(
            clock.layout(), id="clock", className="widget",
            style={"height": "100%", "overflow": "auto", "boxSizing": "border-box"},
        )
    elif widget_id == "google_calendar":
        content = html.Div(
            google_calendar.layout(), id="google_calendar", className="widget",
            style={"height": "100%", "overflow": "auto", "boxSizing": "border-box"},
        )
    elif widget_id.startswith(WEATHER_PREFIX):
        loc_id = widget_id[len(WEATHER_PREFIX):]
        content = html.Div(
            id={"type": "weather-panel", "id": loc_id},
            className="widget",
            style={"height": "100%", "overflow": "auto", "boxSizing": "border-box"},
        )
    else:
        return None

    return dash_draggable.DashboardItem(
        i=widget_id,
        x=x, y=y, w=w, h=h,
        children=content,
    )


def ensure_layout(page):
    """Add default entries for new widgets; drop entries for removed widgets."""
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


def fix_layout_i_values(layouts, widget_ids):
    """
    dash-draggable returns numeric 'i' values ('0','1',...) when DashboardItem
    is not used or the grid loses track. Map them back to widget_ids by index.
    If 'i' is already a widget_id (not purely numeric), leave it alone.
    """
    fixed = {}
    for bp, items in layouts.items():
        fixed_items = []
        for item in items:
            i_val = str(item.get("i", ""))
            if i_val.isdigit():
                idx = int(i_val)
                i_val = widget_ids[idx] if idx < len(widget_ids) else i_val
            fixed_items.append({**item, "i": i_val})
        fixed[bp] = fixed_items
    return fixed


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
        dcc.Store(id="current-widget-ids-store"),
        dcc.Interval(id="weather-interval", interval=30 * 60 * 1000, n_intervals=0),
    ])


@callback(
    Output("page-content", "children"),
    Output("page-widgets-store", "data"),
    Output("current-widget-ids-store", "data"),
    Input("page-tabs", "value"),
)
def render_page(page_id):
    config = load_config()
    page = next((p for p in config["pages"] if p["id"] == page_id), None)
    if not page:
        return html.Div("Page not found."), {}, []

    page = ensure_layout(page)
    layout_map = {item["i"]: item for item in page["layout"]["lg"]}

    children = []
    for wid in page["widget_ids"]:
        child = build_grid_child(wid, layout_map.get(wid, {}))
        if child is not None:
            children.append(child)

    if not children:
        return (
            html.Div("No widgets on this page. Add some in Admin.",
                     style={"padding": "40px", "textAlign": "center", "color": "#aaa"}),
            {}, [],
        )

    grid = dash_draggable.ResponsiveGridLayout(
        id="draggable-grid",
        children=children,
        save=False,
        height=ROW_HEIGHT,
        gridCols={"lg": 12, "md": 12, "sm": 6, "xs": 4, "xxs": 2},
        style={"padding": "16px"},
    )
    store_data = {"page_id": page_id, "widget_ids": page["widget_ids"]}
    return grid, store_data, page["widget_ids"]


@callback(
    Output("current-widget-ids-store", "data", allow_duplicate=True),
    Input("draggable-grid", "layouts"),
    State("page-tabs", "value"),
    State("current-widget-ids-store", "data"),
    prevent_initial_call=True,
)
def save_layout(layouts, page_id, widget_ids):
    if not layouts or not widget_ids:
        return no_update

    fixed = fix_layout_i_values(layouts, widget_ids)

    config = load_config()
    for page in config["pages"]:
        if page["id"] == page_id:
            page["layout"] = fixed
            break
    save_config(config)
    return no_update
