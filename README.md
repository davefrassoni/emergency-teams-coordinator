# ReliefGrid

A low-friction emergency coordination workspace for shared triage, response-team
availability, deployment, and activity tracking.

Production: `https://davefrassoni.com/emergency/`

## What it does

- Anyone can open a private response operation without first creating an account.
- Administrators can expose a public map where anyone can submit a geolocated,
  unverified report without seeing team or reporter details.
- Public users can post itemized supply needs with quantities and units. Other
  users can reserve part or all of the remaining need without over-committing it.
- Anyone can place a missing-person report at the last-seen map position. Public
  viewers see identifying/search details while reporter contact remains private;
  coordinators can verify, prioritize, and assign search-and-rescue teams.
- Contributors receive a private delivery-tracking link for status, ETA, origin,
  notes, and optional live GPS updates; precise positions are public only while
  the contributor explicitly enables sharing.
- Administrators generate one-time, 72-hour invite links for coordinators, viewers,
  or additional administrators.
- Coordinators report emergencies with location, field-assigned triage priority,
  people affected/trapped, hazards, and reporter details.
- Teams publish capability and availability; a team cannot be deployed to two
  emergencies at once.
- Every material action is recorded in the shared operation log.
- Changes arrive through WebSockets; clients automatically switch to 25-second
  long polling if the socket is blocked or disconnected.

Access levels are deliberately separated:

- **Public:** view the public map and submit unverified reports.
- **Viewer:** read the full private operation.
- **Coordinator:** verify and triage incidents, manage resources, and assign teams.
- **Administrator:** all coordinator rights plus invites and public-access control.

Access and invitation secrets are stored as SHA-256 hashes. The usable operation
key stays in the responder's browser local storage. Use HTTPS in every real
deployment because links and browser storage are bearer credentials.

## Local development

Prerequisites: Python 3.12+ and Node.js 20+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Local development uses SQLite and an in-memory
event channel when `DATABASE_URL` and `REDIS_URL` are omitted. Django's development
server runs the ASGI application for both HTTP and WebSocket traffic.

## PostgreSQL deployment

Copy `.env.example` to `.env`, replace the Django and PostgreSQL secrets, set the
public `FRONTEND_URL` and `ALLOWED_HOSTS`, then:

```powershell
docker compose up --build
```

The application is served at `http://localhost:8080` by default. Compose runs
PostgreSQL, Redis, Django Channels/Daphne, and the Vue/Nginx frontend.

The production host checks GitHub `main` every minute using the systemd units in
`deploy/`. A new commit is fast-forwarded and deployed with Docker Compose; failed
or non-fast-forward updates leave the running version untouched.

## Verification

```powershell
cd backend
python manage.py test
python manage.py check

cd ..\frontend
npm run build
```

## Important operational boundary

ReliefGrid records field decisions; it is not a clinical triage system, structural
assessment tool, dispatch authority, or replacement for local incident-command
protocols. A production deployment should add HTTPS, tested backups, monitoring,
an offline/low-connectivity strategy, translations, and an incident data-retention
policy appropriate to the responsible organizations.
