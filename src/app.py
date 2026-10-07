"""
High School Management System API

A simple FastAPI application that lets students view extracurricular
activities and authenticated teachers manage student registrations.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

logger = logging.getLogger(__name__)
SESSION_COOKIE_NAME = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


class LoginRequest(BaseModel):
    username: str
    password: str


def _teacher_credentials() -> dict[str, str]:
    """Load assigned teacher passwords from deployment configuration."""
    raw_credentials = os.environ.get("TEACHER_CREDENTIALS")
    if not raw_credentials:
        logger.error("Teacher login is unavailable: TEACHER_CREDENTIALS is not set")
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured"
        )

    try:
        credentials = json.loads(raw_credentials)
    except json.JSONDecodeError as error:
        logger.error("Teacher login configuration is not valid JSON: %s", error)
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured"
        ) from error

    if (not isinstance(credentials, dict) or not credentials
            or not all(isinstance(user, str) and user
                       and isinstance(password, str) and password
                       for user, password in credentials.items())):
        logger.error("Teacher login configuration must be a non-empty username/password object")
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured"
        )
    return credentials


def _session_secret() -> bytes:
    secret = os.environ.get("SESSION_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        logger.error("Teacher login is unavailable: SESSION_SECRET must be at least 32 bytes")
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured"
        )
    return secret.encode("utf-8")


def _encode_session(username: str, secret: bytes) -> str:
    payload = json.dumps(
        {"username": username, "expires_at": int(time.time()) + SESSION_TTL_SECONDS},
        separators=(",", ":")
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(secret, encoded_payload, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded_payload.decode('ascii')}.{encoded_signature.decode('ascii')}"


def _decode_session(token: str, secret: bytes) -> str | None:
    try:
        encoded_payload, encoded_signature = token.encode("ascii").split(b".", 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + b"=" * (-len(encoded_signature) % 4)
        )
        expected_signature = hmac.new(secret, encoded_payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload = base64.urlsafe_b64decode(
            encoded_payload + b"=" * (-len(encoded_payload) % 4)
        )
        session = json.loads(payload)
        if not isinstance(session, dict):
            return None
        username = session.get("username")
        expires_at = session.get("expires_at")
        if (not isinstance(username, str) or not isinstance(expires_at, int)
                or expires_at <= int(time.time())):
            return None
        return username
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return None


def current_teacher(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    username = _decode_session(token, _session_secret())
    if username is None:
        return None
    if username not in _teacher_credentials():
        return None
    return username


def require_teacher(username: str | None = Depends(current_teacher)) -> str:
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Teacher login required"
        )
    return username


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(login_request: LoginRequest, request: Request, response: Response):
    credentials = _teacher_credentials()
    secret = _session_secret()
    expected_password = credentials.get(login_request.username)
    if (expected_password is None or not hmac.compare_digest(
            login_request.password.encode("utf-8"),
            expected_password.encode("utf-8")
    )):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=_encode_session(login_request.username, secret),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/"
    )
    return {"username": login_request.username}


@app.get("/auth/session")
def get_session(username: str | None = Depends(current_teacher)):
    return {"authenticated": username is not None, "username": username}


@app.delete("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path="/"
    )
    return {"message": "Logged out"}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _username: str = Depends(require_teacher)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _username: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
