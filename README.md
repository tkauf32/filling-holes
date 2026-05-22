# FillingHoles.com

FillingHoles.com is a mobile-first FastAPI prototype where Chicago pedestrians can report potholes with photos and a pinned location, admins can approve or reject those submissions, and the public can simulate crowdfunding each repair.

The product tone is civic utility with a light satirical edge: report a hole, fund a fix, claim the glory.

## Stack

- Python 3.11+
- FastAPI
- Jinja2 templates
- HTMX
- Alpine.js
- TailwindCSS via CDN
- SQLite
- SQLAlchemy ORM
- Leaflet.js + OpenStreetMap
- Pillow
- python-dotenv
- Uvicorn

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 6969
```

Open `http://localhost:6969`

Admin panel: `http://localhost:6969/admin`

## Environment Setup

Copy `.env.example` to `.env` and update at least:

- `ADMIN_PASSWORD`
- `SECRET_KEY`

Default database path:

- `data/fillingholes.db`

Default upload path:

- `app/static/uploads`

If SMTP settings are not present, admin notifications fall back to console logging.

## Database Initialization

Initialize tables with:

```bash
python scripts/init_db.py
```

This creates the SQLite schema and ensures the upload directory exists.

## Admin Login

- Visit `http://localhost:6969/admin`
- Enter the shared password from `.env`
- No username is required in V1

## Demo Flow

### Submit a pothole

1. Open `/submit`
2. Upload 1 to 3 images
3. Use current location or drop a map pin inside Chicago
4. Pick severity and optionally add description and address hint
5. Submit for review

The pothole is stored as `awaiting_confirmation` and stays private until an admin confirms it.

### Approve a pothole

1. Log into `/admin`
2. Open an awaiting submission
3. Click `Confirm and calculate estimate`

Confirmation makes the pothole public, sets status to `pending_funding`, generates a fake estimate, and creates a funding goal equal to that estimate.

### Simulate a contribution

1. Open a public pothole detail page at `/p/{public_id}`
2. Submit any fake contribution amount
3. Optionally add a display name and a naming-rights suggestion

When the raised amount meets or exceeds the funding goal, the pothole auto-transitions to `funded`.

## Features Included In V1

- Public landing page, submit form, public map, and pothole detail pages
- Shared-password admin login with session cookies
- SQLite-backed potholes, images, contributions, comments, and status events
- Chicago-only bounding box validation
- Nearby duplicate warning within 50 meters
- Image resize, compression, and EXIF stripping
- Public comments with admin hide/unhide moderation
- Manual admin status overrides, reject flow, and duplicate marking

## Ubuntu Deployment Notes

Use a Linux VM with Python 3.11+, a virtualenv, and a reverse proxy such as Nginx or Caddy in front of Uvicorn.

Example `systemd` unit:

```ini
[Unit]
Description=FillingHoles FastAPI App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/fillingholes
EnvironmentFile=/opt/fillingholes/.env
ExecStart=/opt/fillingholes/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 6969
Restart=always

[Install]
WantedBy=multi-user.target
```

Production should use Nginx or Caddy as the HTTPS reverse proxy.

## Future Production TODOs

- Replace shared admin password with proper authentication and audit logging
- Add CSRF protection and rate limiting
- Add server-side validation for abusive comment/content patterns
- Move uploads to object storage
- Add real geocoding and stronger duplicate detection
- Replace fake contributions with a real payments flow
- Add database migrations
