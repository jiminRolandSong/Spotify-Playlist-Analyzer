# Playlist Analyzer

This project analyzes Spotify playlists: it extracts track and artist data using the Spotify API, transforms it, loads it into a PostgreSQL database, and displays key insights through a Django dashboard. For dashboard queries and local storage, it uses SQLite.

## Features

- Extracts detailed playlist data from Spotify
- Cleans and transforms raw API data
- Loads track and metadata into PostgreSQL
- Uses SQLite for dashboard queries and local storage
- Displays playlist metadata, top artists, top genres, and a full track table
- Easy-to-use web interface

## Project Structure

```
playlist_analyzer/
├── manage.py
├── playlist_analyzer/
│   ├── settings.py
│   ├── urls.py
├── dashboard/
│   ├── views.py
│   ├── templates/dashboard/dashboard.html
├── scripts/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
├── webData/
├── requirements.txt
├── .env
```

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://your-repo-url.git
   cd playlist_analyzer
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file**

   Add your database and Spotify API credentials:

   ```
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your_db_name

   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://localhost:8000/callback
   ```

5. **Run database migrations (if needed)**
   ```bash
   python manage.py migrate
   ```

6. **Start the Django development server**
   ```bash
   python manage.py runserver
   ```

7. **Open in your browser**
   Go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

   - Enter a Spotify playlist URL
   - Click "Analyze"
   - View the dashboard with insights and full track data

## Requirements

Key packages included in `requirements.txt`:

- Django
- pandas
- psycopg2-binary
- SQLAlchemy
- python-dotenv
- spotipy

## Notes

- Make sure PostgreSQL is running and accessible for data loading.
- SQLite is used for dashboard queries and local storage (`webData/playlist_data.db`).
- The `web_playlist_tracks` table will be created or replaced each time a new playlist is analyzed.
- This project is for educational and demonstration purposes.