import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import json
import os
import logging
import time
from typing import List
import re

from classes.Song import Song
from classes.LyricsLine import LyricsLine

class LyricsManager:
    def __init__(self, spotify_client_id: str, spotify_client_secret: str, spotify_dc_cookie: str):
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.spotify_dc_cookie = spotify_dc_cookie
        self.spotify = spotipy.Spotify(auth_manager = SpotifyOAuth(client_id=self.spotify_client_id,
                                                                   client_secret=self.spotify_client_secret,
                                                                   redirect_uri="http://localhost:8080",
                                                                   scope="user-library-read")
                                       )
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__) 
        
    def get_spotify_token(self) -> None:
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
        r = requests.get(f"https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}", params = params, headers = headers) # https://github.com/akashrchandran/spotify-lyrics-api
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
    
    def search_on_spotify(self, query: str) -> Song|None:
        self.logger.info(f"search_on_spotify: searching for {query}")
        try:
            result = self.spotify.search(query, limit = 3, type = "track")
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
        self.logger.info(f"get_lyrics_from_netease: search lyrics for {song_id}")
        
        params = {
            "id": song_id
        }
        r = requests.get("https://music.xianqiao.wang/neteaseapiv2/lyric", params = params)
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
        q = title + " " + main_artist
        self.logger.info(f"search_on_netease: searching for {q}")
        try:
            params = {
                "limit": 10,
                "type": 1, 
                "keywords": q
            }
            r = requests.get("https://music.xianqiao.wang/neteaseapiv2/search", params = params)
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
            self.logger.error(f"additional information: {r.text}")
            return None