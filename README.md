# Spotify Automation

This project automates the process of saving tracks from the Spotify Discover Weekly playlist to a custom "Saved Weekly" playlist. It is built using Flask, Spotipy (Spotify API library), and requires user authentication.

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
pip install -r requirements.txt
Spotify Developer Account:

3. **Create a Spotify Developer account at Spotify Developer Dashboard.**
Create a new application to obtain client_id and client_secret.
Configure the App:

4. **Replace placeholders in the script (app.py) with your Spotify application's client_id and client_secret.**
Run the App:
python app.py
Access the App:
Open a web browser and navigate to http://127.0.0.1:5000/ to initiate the Spotify authentication process.
