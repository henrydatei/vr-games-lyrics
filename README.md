# vr-games-lyrics
Display the lyrics of the song you are currently playing in Beatsaber/AudioTrip in real-time

To achive the goal of presenting the lyrics of the song you are currently playing in Beatsaber/AudioTrip in real-time, this project uses the following technologies:
- A class `LyricsManager` that is responsible for getting the lyrics of the song. Currently it can search on Spotify and Netease.
- A class `LyricsDisplay` that is responsible for displaying the lyrics in real-time on the screen.

This two classes need to be connected, the information of the song being played in Beatsaber/AudioTrip comes from a websocket connection.

You can use the components individually, for example use the `LyricsManager` to get the lyrics of a song:
```python
from classes.LyricsManager import LyricsManager

lyricsmanager = LyricsManager("my_spotify_client_id", "my_spotify_client_secret", "my_spotify_dc_cookie")
print(lyricsmanager.search_on_netease("we own it", "2 Chainz"))
print(lyricsmanager.search_on_spotify("we own it 2 Chainz"))
```

How to get Spotify Client ID and Client Secret:
- Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
- Create a new app, fill out the info, set redirect URI to `http://localhost:8080/`
- Copy the Client ID and Client Secret from Settings > Client ID and Secret

How to get Spotify DC Cookie:
- Open [Spotify](https://www.spotify.com/) in your browser and login
- Open https://open.spotify.com/get_access_token?reason=transport&productType=web_player in your browser
- Open the developer tools (F12)
- Go to the Application tab
- On the left, go to Cookies > https://open.spotify.com
- Copy the value of the `sp_dc` cookie