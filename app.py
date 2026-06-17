import dash
from dash import html, dcc
import importlib
from dotenv import load_dotenv
load_dotenv()
import os

app = dash.Dash(__name__, title="Life Dashboard")
server = app.server


def load_widgets():
    """Discover and load all widget modules from the widgets/ directory."""
    layouts = []
    widget_dir = os.path.join(os.path.dirname(__file__), "widgets")
    for fname in sorted(os.listdir(widget_dir)):
        if fname.endswith(".py") and not fname.startswith("_"):
            module_name = f"widgets.{fname[:-3]}"
            mod = importlib.import_module(module_name)
            if hasattr(mod, "layout"):
                layouts.append(
                    html.Div(mod.layout(), className="widget")
                )
    return layouts


app.layout = html.Div(
    [
        html.H1("Life Dashboard", style={"textAlign": "center", "marginBottom": "24px"}),
        html.Div(load_widgets(), id="widget-grid", className="widget-grid"),
    ],
    style={"fontFamily": "sans-serif", "padding": "24px", "background": "#f5f5f5", "minHeight": "100vh"},
)

app.index_string = app.index_string.replace(
    "</head>",
    """<style>
.widget-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
.widget { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
</style></head>""",
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
