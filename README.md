# vr-games-lyrics
Display the lyrics of the song you are currently playing in Beatsaber/AudioTrip/Synthriders in real-time

## Quick Start
Clone the repository, install the dependencies (`pip install -r requirements.txt`) and fill out the `secrets.json` file with your Spotify credentials (if this file does not exist, create it):
```json
{
    "spotify_client_id": "your_client_id",
    "spotify_client_secret": "your_client_secret",
    "spotify_dc_cookie": "your_sp_dc_cookie"
}
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

Run the application:
```bash
python3 beatsaber.py
```

AudioTrip and Synthriders are not supported yet, but it will be in the future.

## How it works under the hood
To achive the goal of presenting the lyrics of the song you are currently playing in Beatsaber/AudioTrip/Synthriders in real-time, this project uses the following technologies:
- A class `LyricsManager` that is responsible for getting the lyrics of the song. Currently it can search on Spotify and Netease.
- A class `LyricsDisplay` that is responsible for displaying the lyrics in real-time on the screen.

This two classes need to be connected, the information of the song being played in Beatsaber/AudioTrip/Synthriders comes from a websocket connection. Have a look at the `beatsaber.py` file to see how it works. It is not that complicated, but it lacks some features like detecting when the game is paused or do an accurate timing of the lyrics. Problem with the timing are the level loading times of beatsaber: The websocket says that the song has started, but it takes some time until the song is actually loaded and played. 