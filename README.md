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

Known issues:
- no pause detection yet, so the lyrics will continue to scroll when you pause the game
- the timing of the lyrics is not accurate, because the websocket says that the song has started, but it takes some time until the song is actually loaded and played. Even some live data from the game is not accurate enough, since it does not support sub-second precision. At the current state, the search time for the lyrics and the loading times are sort of balancing each other out.

### AudioTrip

AudioTrip is not supported yet, but it will be in the future.

### Synthriders

Start Synthriders and run the application:
```bash
python3 synthriders.py
```

To access the websocket from Synthriders, you need to install the Mod [SynthRiders Websockets Mod](https://github.com/bookdude13/SynthRiders-Websockets-Mod). For that you need [MelonLoader](https://github.com/LavaGang/MelonLoader). Technically [NoodleManagerX](https://github.com/tommaier123/NoodleManagerX) should also work, they have a different websocket mod, but the same messages. But I was not able to get it to work with NoodleManagerX, so I recommend installing it manually.

Known issues:
- no pause detection yet, so the lyrics will continue to scroll when you pause the game. The websocket mod does not have a message for that, so it is not possible to detect it.
- timing issues are the same as with Beatsaber, see above. But I might be able to use the live data from the game to improve the timing in the future.