# Mergington High School Activities API

A simple FastAPI application that lets students view extracurricular activities and authenticated teachers manage student registrations.

## Features

- View all available extracurricular activities
- View registered students without signing in
- Let authenticated teachers register and unregister students

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Configure teacher accounts and a strong session-signing secret in the server environment. `TEACHER_CREDENTIALS` is a JSON object mapping usernames to assigned passwords:

   ```
   export TEACHER_CREDENTIALS='{"teacher":"replace-with-an-assigned-password"}'
   export SESSION_SECRET='replace-with-a-long-random-secret'
   ```

   Keep both values out of source control and logs. Do not use the example values in a deployment. Teacher accounts are provisioned by the administrator; there is no account-management page.

3. Run the application:

   ```
   uvicorn app:app --app-dir src --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                            |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| POST   | `/auth/login`                                                     | Sign in as a teacher and start a secure browser session                |
| GET    | `/auth/session`                                                   | Check whether the current browser session belongs to a teacher        |
| DELETE | `/auth/logout`                                                    | End the current browser session                                        |
| GET    | `/activities`                                                     | Publicly view activities and their registered students                |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher session required)                          |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher session required)                     |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data is stored in memory, which means registrations will be reset when the server restarts. Teacher passwords are supplied through deployment configuration, not stored in a checked-in JSON file. Teacher sessions are signed by `SESSION_SECRET`, expire after eight hours, and use an HttpOnly, SameSite cookie.
