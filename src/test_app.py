import json
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

import app


class TeacherAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "TEACHER_CREDENTIALS": json.dumps(
                    {"teacher": "correct horse battery staple"}
                ),
                "SESSION_SECRET": "test-session-secret-with-at-least-32-bytes",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @staticmethod
    def make_request(cookie: str | None = None, scheme: str = "http") -> Request:
        headers = []
        if cookie:
            headers.append(
                (b"cookie", f"{app.SESSION_COOKIE_NAME}={cookie}".encode("ascii"))
            )
        return Request(
            {
                "type": "http",
                "method": "GET",
                "scheme": scheme,
                "path": "/",
                "query_string": b"",
                "headers": headers,
                "server": ("testserver", 80),
                "client": ("testclient", 50000),
            }
        )

    def test_login_sets_httponly_session_and_authenticates_teacher(self):
        response = Response()
        app.login(
            app.LoginRequest(
                username="teacher",
                password="correct horse battery staple",
            ),
            self.make_request(scheme="https"),
            response,
        )

        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        token = cookie.split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(app.current_teacher(self.make_request(token)), "teacher")

    def test_invalid_password_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            app.login(
                app.LoginRequest(username="teacher", password="wrong"),
                self.make_request(),
                Response(),
            )
        self.assertEqual(error.exception.status_code, 401)

    def test_unknown_teacher_cannot_login_with_empty_password(self):
        with self.assertRaises(HTTPException) as error:
            app.login(
                app.LoginRequest(username="unknown", password=""),
                self.make_request(),
                Response(),
            )
        self.assertEqual(error.exception.status_code, 401)

    def test_modified_and_expired_sessions_are_rejected(self):
        secret = app._session_secret()
        token = app._encode_session("teacher", secret)
        payload, signature = token.split(".", 1)
        modified_token = f"{payload}.{('A' if signature[0] != 'A' else 'B')}{signature[1:]}"
        self.assertIsNone(app._decode_session(modified_token, secret))

        with patch("app.time.time", return_value=100):
            expiring_token = app._encode_session("teacher", secret)
        with patch(
            "app.time.time",
            return_value=100 + app.SESSION_TTL_SECONDS,
        ):
            self.assertIsNone(app._decode_session(expiring_token, secret))

    def test_registration_routes_require_teacher_dependency(self):
        protected_paths = {
            "/activities/{activity_name}/signup",
            "/activities/{activity_name}/unregister",
        }
        routes = {
            route.path: route
            for route in app.app.routes
            if getattr(route, "path", None) in protected_paths
        }

        self.assertEqual(set(routes), protected_paths)
        for route in routes.values():
            dependency_calls = {
                dependency.call for dependency in route.dependant.dependencies
            }
            self.assertIn(app.require_teacher, dependency_calls)

    def test_student_activity_listing_remains_public(self):
        activities_route = next(
            route for route in app.app.routes
            if getattr(route, "path", None) == "/activities"
        )
        dependency_calls = {
            dependency.call for dependency in activities_route.dependant.dependencies
        }
        self.assertNotIn(app.require_teacher, dependency_calls)


if __name__ == "__main__":
    unittest.main()
