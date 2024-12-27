import os
import re
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates a Spotify playlist from a ranking file."

    def handle(self, *args, **kwargs):
        # Load Spotify API Credentials from environment variables
        CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
        CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
        REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

        if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
            self.stderr.write("Spotify API credentials are not set in environment variables.")
            return

        # Set up Spotipy with OAuth
        scope = "playlist-modify-private playlist-modify-public"
        sp = Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=scope
        ))

        # Step 1: Read songs from ranking_list.txt
        ranking_file = "ranking_list.txt"

        if not os.path.exists(ranking_file):
            raise FileNotFoundError(f"The file '{ranking_file}' does not exist.")

        songs = []
        with open(ranking_file, "r") as file:
            for line in file:
                if line.strip() and not line.startswith("Rank"):  # Skip header or empty lines
                    rank, song = line.split("\t", 1)  # Split by tab
                    songs.append(song.strip())

        # Define the playlist name and description
        playlist_name = "Taylor Swift Ranking"
        playlist_description = "Taylor Swift songs ranked by Mollie."

        # Step 2: Get current user's ID
        current_user = sp.me()
        user_id = current_user["id"]
        self.stdout.write(f"Logged in as: {current_user['display_name']} | User ID: {user_id}")

        # Step 3: Create a new playlist
        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description=playlist_description
        )
        self.stdout.write(f"Playlist '{playlist_name}' created with ID: {playlist['id']}")

        # Function to clean song titles
        def clean_song_title(song_title):
            song_title = re.sub(r"\b(feat\.?|ft\.?|featuring)\b", "", song_title, flags=re.IGNORECASE).strip()
            return re.sub(r"\s+", " ", song_title)

        # Step 4: Search for each song
        track_uris = []
        for song in songs:
            try:
                cleaned_song = clean_song_title(song)
                result = sp.search(q=f"track:{cleaned_song} artist:Taylor Swift", type="track", limit=10)

                if result["tracks"]["items"]:
                    track_uris.append(result["tracks"]["items"][0]["uri"])
                    self.stdout.write(f"Added: {cleaned_song}")
                else:
                    self.stderr.write(f"Song not found: {song}")

            except Exception as e:
                self.stderr.write(f"Error searching for {song}: {e}")

        # Step 5: Add tracks to the playlist
        def add_tracks_in_batches(playlist_id, track_uris, batch_size=100):
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                try:
                    sp.playlist_add_items(playlist_id=playlist_id, items=batch)
                    self.stdout.write(f"Added batch {i // batch_size + 1}")
                except Exception as e:
                    self.stderr.write(f"Error adding batch: {e}")

        if track_uris:
            add_tracks_in_batches(playlist["id"], track_uris)
            self.stdout.write(f"Added {len(track_uris)} tracks to playlist '{playlist_name}'.")
        else:
            self.stderr.write("No tracks were added to the playlist.")
