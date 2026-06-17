"""
Run this script once to authorize Google Calendar access.
It will open a browser, ask you to log in, then save a token to data/token.json.

Usage:
    .\.venv\Scripts\python data\gcal_auth.py
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(DATA_DIR, "credentials.json")
TOKEN_FILE = os.path.join(DATA_DIR, "token.json")


def authorize():
    if not os.path.exists(CREDS_FILE):
        print(f"ERROR: credentials.json not found at {CREDS_FILE}")
        print("Download it from Google Cloud Console and place it there.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"✓ Token saved to {TOKEN_FILE}")
    print("You can now run the dashboard: python app.py")


if __name__ == "__main__":
    authorize()
