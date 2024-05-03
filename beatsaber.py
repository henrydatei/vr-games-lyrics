import websocket
import threading
import tkinter as tk
import os
import json
import logging

from classes.LyricsManager import LyricsManager
from classes.LyricsDisplay import LyricsDisplay

logger = logging.getLogger(__name__)
logging.basicConfig(level = logging.DEBUG, format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def on_error(ws, error):
    logger.error(f"Error occured in websocket: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.info(f"Closed connection with status code {close_status_code} and message {close_msg}")

def on_open(ws):
    logger.info("Connection opened")
    
def on_message(ws, message):
    logger.debug(f"Received message: {message}")
    global first_message
    global previous_message
    global lyricsmanager
    global window
    data = json.loads(message)
    
    # check if message is first message and contains to much information, then ignore it
    if first_message and data["SongName"] != "" and data["SongAuthor"] != "":
        logger.warn("First message contains too much information for a first message, ignoring it")
        first_message = False
        return
    
    # calc difference between previous message and current message
    updated_keys = []
    for key in previous_message:
        if key in data and previous_message[key] != data[key]:
            updated_keys.append(key)
    previous_message = data
    logger.debug(f"Updated keys: {updated_keys}")
    
    if "SongName" in updated_keys and data["SongName"] != "" and "SongAuthor" in updated_keys and data["SongAuthor"] != "":
        logger.info(f"Song started because it changed to {data['SongName']} by {data['SongAuthor']}")
        # empty window
        for child in window.winfo_children():
            child.destroy()
        # get lyrics
        lyrics = lyricsmanager.search_on_netease(data["SongName"], data["SongAuthor"])
        if lyrics is None:
            lyrics = lyricsmanager.search_on_spotify(data["SongName"], data["SongAuthor"])
        if lyrics is None:
            logger.error("Could not find lyrics for this song")
            return
        # display lyrics
        lyricsFrame = LyricsDisplay(container=window, song=lyrics, color="green", speed=1)
        lyricsFrame.pack(fill = "both", expand = True)
        lyricsFrame.start_lyrics()
    elif data["LevelFinished"] or data["LevelQuit"] or data["LevelFailed"]:
        logger.info("Song ended, failed or quit, removing lyrics display")
        # empty window
        for child in window.winfo_children():
            child.destroy()
    
    # check if modifiers changed, if so update speed, need to sync lyrics because it takes a lot of time to get this information
    if "Modifiers" in updated_keys:
        if data["Modifiers"]["SuperFastSong"]:
            logger.info("super fast song")
            lyricsFrame.speed = 1.5
        if data["Modifiers"]["FasterSong"]:
            logger.info("faster song")
            lyricsFrame.speed = 1.2
        if data["Modifiers"]["SlowerSong"]:
            logger.info("slower song")
            lyricsFrame.speed = 0.85
            
    # check if practise mode enabled, if so update speed
    if ("PracticeMode" in updated_keys) and data["PracticeMode"]:
        logger.info(f"practise mode enabled, speed is {data['PracticeModeModifiers']['SongSpeedMul']} and start time is {data['PracticeModeModifiers']['SongStartTime'] * 1000} ms")
        lyricsFrame.speed = data['PracticeModeModifiers']['SongSpeedMul']
        lyricsFrame.jump_to_time(data['PracticeModeModifiers']['SongStartTime'] * 1000)
    
def connection():
    global ws
    ws = websocket.WebSocketApp("ws://localhost:2946/BSDataPuller/MapData",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

def main():
    global lyricsmanager
    global window
    
    secrets = json.load(open(os.path.dirname(__file__) + "/secrets.json"))
        
    first_message = True
    previous_message = {
        'GameVersion': None, 
        'PluginVersion': None, 
        'InLevel': None, 
        'LevelPaused': None, 
        'LevelFinished': None, 
        'LevelFailed': None, 
        'LevelQuit': None, 
        'Hash': None, 
        'SongName': '', 
        'SongSubName': '', 
        'SongAuthor': '', 
        'Mapper': '', 
        'BSRKey': None, 
        'CoverImage': None, 
        'Duration': 0, 
        'MapType': '', 
        'Environment': '', 
        'Difficulty': '', 
        'CustomDifficultyLabel': None, 
        'BPM': 0, 
        'NJS': 0.0, 
        'Modifiers': None, 
        'ModifiersMultiplier': 1.0, 
        'PracticeMode': None, 
        'PracticeModeModifiers': None,
        'PP': None, 
        'Star': None, 
        'IsMultiplayer': None, 
        'MultiplayerLobbyMaxSize': None, 
        'MultiplayerLobbyCurrentSize': None, 
        'PreviousRecord': None, 
        'PreviousBSR': None, 
        'UnixTimestamp': None
    }

    lyricsmanager = LyricsManager(secrets['spotify_client_id'], secrets['spotify_client_secret'], secrets['spotify_dc_cookie'])    

    # init GUI
    window = tk.Tk()
    window.state("zoomed")
    window.attributes('-alpha',0.5)

    # thread for receiving events from Beatsaber
    t = threading.Thread(target = connection)
    t.start()

    # start GUI
    window.mainloop()

    # if here then window.mainloop() was exited -> close websocket
    global ws
    ws.close()
    
if __name__ == "__main__":
    main()