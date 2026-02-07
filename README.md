# Spotify Automation

This project automates the process of saving tracks from the Spotify Discover Weekly playlist to a custom "Saved Weekly" playlist. It is built using Flask, Spotipy (Spotify API library), and requires user authentication.

---

## Backend (FastAPI) – Configuration

The backend uses **Pydantic Settings** and requires these environment variables. The app **fails fast on startup** if any required variable is missing.

| Variable | Required | Description |
|----------|----------|-------------|
| `SPOTIFY_CLIENT_ID` | Yes | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | Spotify app client secret |
| `APP_SECRET` | Yes | Min 16 chars; used for session/CSRF signing |
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `BASE_URL` | Yes | Public base URL of this app (e.g. `http://localhost:8000`) for OAuth redirects |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins (default: `http://localhost:3000`) |
| `LOG_LEVEL` | No | Log level (default: `INFO`) |
| `JSON_LOGS` | No | Set to `true` for JSON log lines |

**Setup:** Copy `backend/.env.example` to `backend/.env` and fill in values. Never commit `.env`. Logging redacts tokens and secrets; do not log credentials in application code.

## Features

- **Automatic Playlist Update:** Tracks from the Discover Weekly playlist are automatically added to a designated "Saved Weekly" playlist.
- **User Authentication:** Utilizes Spotify OAuth for user authentication and token management.
- **Playlist Management:** Handles the creation of the "Saved Weekly" playlist if not found.

## Getting Started

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/spotify-automation.git
   cd spotify-automation
   
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt

3. **Create a Spotify Developer account at Spotify Developer Dashboard.**
Create a new application to obtain client_id and client_secret.
Configure the App:

4. **Replace placeholders in the script (app.py) with your Spotify application's client_id and client_secret.**
Run the App:
```bash
python app.py
Access the App:
Open a web browser and navigate to http://127.0.0.1:5000/ to initiate the Spotify authentication process.
