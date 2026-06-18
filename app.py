import dash
from dash import html, dcc
from dotenv import load_dotenv

load_dotenv()

app = dash.Dash(
    __name__,
    title="Life Dashboard",
    use_pages=True,
    suppress_callback_exceptions=True,
)
server = app.server

app.layout = html.Div([
    html.Nav([
        dcc.Link("Life Dashboard", href="/", className="nav-title"),
        dcc.Link("Dashboard", href="/"),
        dcc.Link("Admin", href="/admin"),
    ], className="nav"),
    dash.page_container,
])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
