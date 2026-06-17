import os
import datetime
from dash import html, dcc, callback, Output, Input

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TOKEN_FILE = os.path.join(DATA_DIR, "token.json")
CREDS_FILE = os.path.join(DATA_DIR, "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not os.path.exists(TOKEN_FILE):
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("calendar", "v3", credentials=creds)


def _fetch_events():
    service = _get_service()
    if service is None:
        return None

    now = datetime.datetime.utcnow()
    end = now + datetime.timedelta(days=7)

    result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat() + "Z",
        timeMax=end.isoformat() + "Z",
        maxResults=10,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return result.get("items", [])


def _format_event(event):
    start = event["start"].get("dateTime", event["start"].get("date", ""))
    try:
        dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
        dt_local = dt.astimezone()
        label = dt_local.strftime("%a %b %d  %I:%M %p")
    except Exception:
        label = start

    return html.Div(
        [
            html.Span(label, style={"color": "#888", "fontSize": "0.75rem", "display": "block"}),
            html.Span(event.get("summary", "(no title)"), style={"fontWeight": "500"}),
        ],
        style={"padding": "6px 0", "borderBottom": "1px solid #f0f0f0"},
    )


def layout():
    return html.Div([
        html.H3("Google Calendar", style={"marginTop": 0}),
        html.Div(id="gcal-content"),
        dcc.Interval(id="gcal-interval", interval=5 * 60 * 1000, n_intervals=0),
    ])


@callback(Output("gcal-content", "children"), Input("gcal-interval", "n_intervals"))
def update_calendar(_):
    if not os.path.exists(TOKEN_FILE):
        return html.Div(
            "Not connected. Run: .venv\\Scripts\\python data\\gcal_auth.py",
            style={"color": "#aaa", "fontStyle": "italic"},
        )

    try:
        events = _fetch_events()
    except Exception as e:
        return html.Div(f"Error: {e}", style={"color": "red"})

    if not events:
        return html.Div("No upcoming events in the next 7 days.", style={"color": "#aaa"})

    return html.Div([_format_event(e) for e in events])
