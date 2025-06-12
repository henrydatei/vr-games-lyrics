# vr-games-lyrics
Display the lyrics of the song you are currently playing in Beatsaber/AudioTrip/Synthriders in real-time

## Quick Start
Clone the repository, install the dependencies (`pip install -r requirements.txt`) and fill out the `secrets.json` file with your Spotify credentials (if this file does not exist, create it):
```json
{
    "spotify_client_id": "your_client_id",
    "spotify_client_secret": "your_client_secret"
}
```

How to get Spotify Client ID and Client Secret:
- Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
- Create a new app, fill out the info, set redirect URI to `http://localhost:8080/`
- Copy the Client ID and Client Secret from Settings > Client ID and Secret

### Beatsaber
Start Beatsaber and run the application:
```bash
python3 beatsaber.py
```
To access the websocket from Beatsaber, you need to install the Mod [Data Puller](https://github.com/ReadieFur/BSDataPuller). I reccommend [BS Manager](https://github.com/Zagrios/bs-manager) to manage mods, maps and versions of Beatsaber.

### AudioTrip

AudioTrip is not supported yet, but it will be in the future.

### Synthriders

Start Synthriders and run the application:
```bash
python3 synthriders.py
```

To access the websocket from Synthriders, you need to install the Mod [SynthRiders Websockets Mod](https://github.com/bookdude13/SynthRiders-Websockets-Mod). For that you need [MelonLoader](https://github.com/LavaGang/MelonLoader). Technically [NoodleManagerX](https://github.com/tommaier123/NoodleManagerX) should also work, they have a different websocket mod, but the same messages. But I was not able to get it to work with NoodleManagerX, so I recommend installing it manually.

## How it works under the hood
To achive the goal of presenting the lyrics of the song you are currently playing in Beatsaber/AudioTrip/Synthriders in real-time, this project uses the following technologies:
- A class `LyricsManager` that is responsible for getting the lyrics of the song. Currently it can search on Spotify and Netease.
- A class `LyricsDisplay` that is responsible for displaying the lyrics in real-time on the screen.

This two classes need to be connected, the information of the song being played in Beatsaber/AudioTrip/Synthriders comes from a websocket connection. Have a look at the `beatsaber.py` file to see how it works. It is not that complicated, but it lacks some features like detecting when the game is paused or do an accurate timing of the lyrics. Problem with the timing are the level loading times of beatsaber: The websocket says that the song has started, but it takes some time until the song is actually loaded and played. 