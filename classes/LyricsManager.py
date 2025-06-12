import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import json
import os
import logging
import time
from typing import List
import re
import sqlite3
import syncedlyrics

from classes.Song import Song
from classes.LyricsLine import LyricsLine

class LyricsManager:
    """LyricsManager class to manage lyrics from Spotify and Netease. Call search_on_spotify() or search_on_netease() to get lyrics for a song.
    """
    def __init__(self, spotify_client_id: str, spotify_client_secret: str, spotify_dc_cookie: str):
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.spotify_dc_cookie = spotify_dc_cookie
        self.spotify = spotipy.Spotify(auth_manager = SpotifyOAuth(client_id = self.spotify_client_id,
                                                                   client_secret = self.spotify_client_secret,
                                                                   redirect_uri = "http://localhost:8080",
                                                                   scope = "user-library-read")
                                       )
        self.db_path = os.path.join(os.path.dirname(__file__), "../lyrics.db")
        self._initialize_database()
        logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__) 
        
    def _initialize_database(self):
        """Create SQLite database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                artist TEXT,
                cover_link TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lyrics_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id INTEGER,
                text TEXT,
                startMs INTEGER,
                endMs INTEGER,
                durationMs INTEGER,
                FOREIGN KEY(song_id) REFERENCES songs(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS querys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_title TEXT,
                query_main_artist TEXT,
                song_id INTEGER,
                FOREIGN KEY(song_id) REFERENCES songs(id)
            )
        ''')
        conn.commit()
        conn.close()
        
    def save_song_to_database(self, song: Song, query_title: str, query_main_artist: str) -> None:
        """Save a song and its lyrics to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # check if song is already in database
        cursor.execute('''
            SELECT * FROM querys
            WHERE query_title = ? AND query_main_artist = ?
        ''', (query_title, query_main_artist))
        result = cursor.fetchone()
        if result:
            self.logger.info(f"save_song_to_database: {query_title} - {query_main_artist} already in database")
        else:
            self.logger.info(f"save_song_to_database: saving {query_title} - {query_main_artist} to database")
            cursor.execute('''
                INSERT INTO songs (title, artist, cover_link)
                VALUES (?, ?, ?)
            ''', (song.title, song.artist, song.cover_link))
            song_id = cursor.lastrowid
            for line in song.lines:
                cursor.execute('''
                    INSERT INTO lyrics_lines (song_id, text, startMs, endMs, durationMs)
                    VALUES (?, ?, ?, ?, ?)
                ''', (song_id, line.text, line.startMs, line.endMs, line.durationMs))
            cursor.execute('''
                INSERT INTO querys (query_title, query_main_artist, song_id)
                VALUES (?, ?, ?)
            ''', (query_title, query_main_artist, song_id))
            conn.commit()
        self.logger.debug("save_song_to_database, closing connection to database")
        conn.close()
        self.logger.info(f"save_song_to_database: closed connection to database")
        
    def search_in_database(self, title: str, main_artist: str) -> Song:
        """Search for a song in the SQLite database and return it if found."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM querys
            WHERE query_title = ? AND query_main_artist = ?
        ''', (title, main_artist))
        result = cursor.fetchone()
        if not result:
            self.logger.error(f"search_in_database: failed to find {title} - {main_artist} when searching in query table")
            return None
        querys_id, query_title, query_main_artist, song_id = result
        self.logger.info(f"search_in_database: found {title} - {main_artist} in query table with song_id {song_id}")
        cursor.execute('''
            SELECT * FROM songs
            WHERE id = ?
        ''', (song_id,))
        result = cursor.fetchone()
        if not result:
            self.logger.error(f"search_in_database: failed to find {title} - {main_artist} when searching in songs table with song_id {song_id}")
            return None
        song_id, title, artist, cover_link = result
        self.logger.info(f"search_in_database: found {title} - {artist} in songs table with song_id {song_id}")
        cursor.execute('''
            SELECT * FROM lyrics_lines
            WHERE song_id = ?
            ORDER BY startMs ASC
        ''', (song_id,))
        lyrics_lines = []
        for line_data in cursor.fetchall():
            lyrics_lines.append(LyricsLine(
                text=line_data[2],
                startMs=line_data[3],
                endMs=line_data[4],
                durationMs=line_data[5]
            ))
        conn.close()
        return Song(title=title, artist=artist, cover_link=cover_link if cover_link != 'None' else None, lines=lyrics_lines)
    
    def get_lyrics_from_syncedlyrics(self, title: str, main_artist: str, song_length_in_ms: int) -> List[LyricsLine]|None:
        """Search for lyrics with Python package syncedlyrics (https://github.com/moehmeni/syncedlyrics) and return them as a list of LyricsLine objects."""
        query = title + " " + main_artist
        lyrics_text = syncedlyrics.search(query, allow_plain_format=False)
        if lyrics_text is None:
            return None
        
        pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2})\] (.+)')
        matches = pattern.findall(lyrics_text)
        lyrics_lines = []

        def timestamp_to_ms(minutes: int, seconds: int, milliseconds: int) -> int:
            """Convert timestamp to milliseconds."""
            return (minutes * 60 * 1000) + (seconds * 1000) + milliseconds * 10

        for i, match in enumerate(matches):
            minutes, seconds, centiseconds, text = match
            start_ms = timestamp_to_ms(int(minutes), int(seconds), int(centiseconds))
            
            # Determine end time or use a default for the last line
            if i + 1 < len(matches):
                next_minutes, next_seconds, next_centiseconds, _ = matches[i + 1]
                end_ms = timestamp_to_ms(int(next_minutes), int(next_seconds), int(next_centiseconds))
            else:
                end_ms = song_length_in_ms
            
            duration_ms = end_ms - start_ms
            lyrics_lines.append(LyricsLine(text=text, startMs=start_ms, endMs=end_ms, durationMs=duration_ms))
        
        return lyrics_lines

    def search_on_spotify_with_syncedlyrics_provider(self, title: str, main_artist: str, limit: int = 1) -> Song|None:
        """Search for a song on Spotify and get the song with lyrics, cover link, title and artist. The best match is selected based on popularity from the <limit> best matches. The lyrics comes from the syncedlyrics package.

        Args:
            title (str): The title of the song.
            main_artist (str): The main artist of the song (or any other artist from the song).

        Returns:
            Song|None: A Song object or None if the song could not be found.
        """
        query = title + " " + main_artist
        self.logger.info(f"search_on_spotify_with_syncedlyrics_provider: searching for {query}")
        try:
            result = self.spotify.search(query, limit = limit, type = "track")
            if len(result["tracks"]["items"]) == 0:
                self.logger.error(f"search_on_spotify_with_syncedlyrics_provider: failed to find {query}")
                return None
            # sort result by popularity - best match has highest popularity
            result["tracks"]["items"].sort(key = lambda x: x["popularity"], reverse = True)
            title = result["tracks"]["items"][0]["name"].split("(")[0].split(" - ")[0]
            artists = [artist["name"] for artist in result["tracks"]["items"][0]["artists"]]
            coverLink = result["tracks"]["items"][0]["album"]["images"][0]["url"]
            self.logger.info(f"search_on_spotify_with_syncedlyrics_provider: found {title} by {artists[0]} with cover link {coverLink}")
            lyrics_lines = self.get_lyrics_from_syncedlyrics(title, artists[0], result["tracks"]["items"][0]["duration_ms"])
            if not lyrics_lines:
                self.logger.error(f"search_on_spotify_with_syncedlyrics_provider: failed to get lyrics for {query}")
                return None
            return Song(
                lines = lyrics_lines, 
                cover_link = coverLink, 
                title = title, 
                artist = ", ".join(artists)
            )
        except Exception as e:
            self.logger.error(f"search_on_spotify_with_syncedlyrics_provider: failed to search for {query}, error: {e}")
            return None