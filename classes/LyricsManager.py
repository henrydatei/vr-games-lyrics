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
        
    def get_spotify_token(self) -> None:
        """To access the lyrics which are not in the official API, we need to get a token from Spotify. This function gets the token and saves it to ../token.json.
        """
        self.logger.info("get_spotify_token: getting new token")
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36', 
            'App-platform': 'WebPlayer', 
            'content-type': 'text/html; charset=utf-8'
        }
        cookies = {
            'sp_dc': self.spotify_dc_cookie
        }
        r = requests.get("https://open.spotify.com/get_access_token?reason=transport&productType=web_player", headers = headers, cookies = cookies)
        r.raise_for_status()
        with open(os.path.dirname(__file__) + "/../token.json", "w") as f:
            json.dump(r.json(), f)
        
    def check_spotify_token(self) -> None:
        """The token from Spotify expires after a certain time. This function checks if the token is still valid and gets a new one if it is expired.
        """
        self.logger.info("check_spotify_token: checking token")
        try:
            with open(os.path.dirname(__file__) + "/../token.json", "r") as f:
                token = json.load(f)
        except FileNotFoundError:
            self.get_spotify_token()
            return
        if token["accessTokenExpirationTimestampMs"] < int(time.time() * 1000):
            self.logger.warn("check_spotify_token: token expired")
            self.get_spotify_token()
            
    def get_lyrics_from_spotify(self, track_id: str) -> List[LyricsLine]|None:
        """Get lyrics from Spotify for a given track_id. Inspired by https://github.com/akashrchandran/spotify-lyrics-api

        Args:
            track_id (str): The track_id of the song.

        Returns:
            List[LyricsLine]|None: A list of LyricsLine objects or None if the lyrics could not be found.
        """
        self.logger.info(f"get_lyrics_from_spotify: search lyrics for {track_id}")
        self.check_spotify_token()
        access_token = json.load(open(os.path.dirname(__file__) + "/../token.json"))["accessToken"]
        
        params = {
            "format":"json", 
            "market":"from_token"
        }
        headers = {
            "App-platform": "WebPlayer", 
            "authorization": f"Bearer {access_token}", 
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36"
        } 
        r = requests.get(f"https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}", params = params, headers = headers)
        if r.status_code != 200:
            self.logger.error(f"get_lyrics_from_spotify: failed to get lyrics for {track_id}, status code: {r.status_code}")
            self.logger.error(f"additional information: {r.text}")
            return None
        
        lines = r.json()['lyrics']['lines']
        lyrics_lines = []
        for idx, line in enumerate(lines[:-1]):
            duration = int(lines[idx + 1]["startTimeMs"]) - int(line["startTimeMs"])
            lyrics_line = LyricsLine(
                text = line["words"], 
                startMs = int(line["startTimeMs"]), 
                endMs = int(lines[idx + 1]["startTimeMs"]), 
                durationMs = duration
            )
            lyrics_lines.append(lyrics_line)
        return lyrics_lines
    
    def search_on_spotify(self, title: str, main_artist: str) -> Song|None:
        """Search for a song on Spotify and get the song with lyrics, cover link, title and artist. The best match is selected based on popularity from the 3 best matches.

        Args:
            title (str): The title of the song.
            main_artist (str): The main artist of the song (or any other artist from the song).
            
        Returns:
            Song|None: A Song object or None if the song could not be found.
        """
        query = title + " " + main_artist
        self.logger.info(f"search_on_spotify: searching for {query}")
        try:
            result = self.spotify.search(query, limit = 3, type = "track")
            if len(result["tracks"]["items"]) == 0:
                self.logger.error(f"search_on_spotify: failed to find {query}")
                return None
            # sort result by popularity - best match has highest popularity
            result["tracks"]["items"].sort(key = lambda x: x["popularity"], reverse = True)
            title = result["tracks"]["items"][0]["name"].split("(")[0].split(" - ")[0]
            artists = [artist["name"] for artist in result["tracks"]["items"][0]["artists"]]
            coverLink = result["tracks"]["items"][0]["album"]["images"][0]["url"]
            track_id = result["tracks"]["items"][0]["id"]
            lyrics_lines = self.get_lyrics_from_spotify(track_id)
            self.logger.info(f"search_on_spotify: track_id is: {track_id}")
            return Song(
                lines = lyrics_lines, 
                cover_link = coverLink, 
                title = title, 
                artist = ", ".join(artists)
            )
        except Exception as e:
            self.logger.error(f"search_on_spotify: failed to search for {query}, error: {e}")
            return None
        
    def get_lyrics_from_netease(self, song_id: str, song_length_in_ms: int) -> List[LyricsLine]|None:
        """Get lyrics from Netease for a given song_id. The song_length_in_ms is needed to calculate the duration of the last line in the lyrics.

        Args:
            song_id (str): The song_id of the song.
            song_length_in_ms (int): The length of the song in milliseconds.

        Returns:
            List[LyricsLine]|None: A list of LyricsLine objects or None if the lyrics could not be found.
        """
        self.logger.info(f"get_lyrics_from_netease: search lyrics for {song_id}")
        
        params = {
            "id": song_id
        }
        r = requests.get("https://music.xianqiao.wang/neteaseapiv2/lyric", params = params, timeout=5)
        if r.status_code != 200:
            self.logger.error(f"get_lyrics_from_netease: failed to get lyrics for {song_id}, status code: {r.status_code}")
            self.logger.error(f"additional information: {r.text}")
            return None
        
        lines = r.json()["lrc"]["lyric"].split('\n')[1:-1] # skip first and last line
        lyrics_lines = []
        current_time = 0
        for line in lines:
            if re.match(r'\[\d+:\d+\.\d+\]', line): # check if line is a timestamp
                timestamp = re.search(r'\[(\d+):(\d+\.\d+)\]', line)
                minutes, seconds = map(float, timestamp.groups())
                current_time = int((minutes * 60 + seconds) * 1000) # convert to ms
                text = re.sub(r'\[\d+:\d+\.\d+\]', '', line).strip() # extract text
                
                lyrics_line = LyricsLine(
                    text = text, 
                    startMs = current_time, 
                    endMs = 0, # endMs will be calculated later
                    durationMs = 0 # durationMs will be calculated later
                )
                lyrics_lines.append(lyrics_line)
        
        # calculate duration and endMs
        for idx, line in enumerate(lyrics_lines[:-1]):
            line.durationMs = lyrics_lines[idx + 1].startMs - line.startMs
            line.endMs = lyrics_lines[idx + 1].startMs
            
        # duration and endMs last line
        lyrics_lines[-1].durationMs = song_length_in_ms - lyrics_lines[-1].startMs
        lyrics_lines[-1].endMs = song_length_in_ms
        
        return lyrics_lines
    
    def search_on_netease(self, title: str, main_artist: str) -> Song|None:
        """Search for a song on Netease and get the song with lyrics, title and artist. The best match is selected based on title and main_artist from the 10 best matches because the search on Netease is worse than Spotify's search.

        Args:
            title (str): The title of the song.
            main_artist (str): The main artist of the song (or any other artist from the song).

        Returns:
            Song|None: A Song object or None if the song could not be found.
        """
        q = title + " " + main_artist
        self.logger.info(f"search_on_netease: searching for {q}")
        try:
            params = {
                "limit": 10,
                "type": 1, 
                "keywords": q
            }
            r = requests.get("https://music.xianqiao.wang/neteaseapiv2/search", params = params, timeout=5)
            r.raise_for_status()
            for song in r.json()["result"]["songs"]:
                if song["name"].lower() == title.lower() and main_artist.lower() in [artist["name"].lower() for artist in song["artists"]]:
                    song_id = song["id"]
                    song_duration = song["duration"]
                    lyrics = self.get_lyrics_from_netease(song_id, song_duration)
                    return Song(
                        lines = lyrics, 
                        title = song["name"], 
                        artist = ", ".join([artist["name"] for artist in song["artists"]])
                    )
            self.logger.error(f"search_on_netease: failed to find {q}")
            return None
        except Exception as e:
            self.logger.error(f"search_on_netease: failed to search for {q}, error: {e}")
            return None
        
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
    
    def search_on_spotify_with_syncedlyrics_provider(self, title: str, main_artist: str) -> Song|None:
        """Search for a song on Spotify and get the song with lyrics, cover link, title and artist. The best match is selected based on popularity from the 3 best matches. The lyrics comes from the syncedlyrics package.

        Args:
            title (str): The title of the song.
            main_artist (str): The main artist of the song (or any other artist from the song).

        Returns:
            Song|None: A Song object or None if the song could not be found.
        """
        query = title + " " + main_artist
        self.logger.info(f"search_on_spotify_with_syncedlyrics_provider: searching for {query}")
        try:
            result = self.spotify.search(query, limit = 3, type = "track")
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