import websocket
import threading
import tkinter as tk
import os
import json
import logging
import win32gui
import time

from classes.LyricsManager import LyricsManager
from classes.LyricsDisplay import LyricsDisplay

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BeatSaberLyricsApp:
    def __init__(self):
        """Initalises the Beat Saber Lyrics application."""
        self.root = tk.Tk()
        self.ws_thread = None
        self.ws = None
        self.is_running = True

        # Zustand der Anwendung
        self.lyrics_frame = None
        self.current_song_hash = None
        
        # Lade Geheimnisse und initialisiere den LyricsManager
        secrets_path = os.path.join(os.path.dirname(__file__), "secrets.json")
        secrets = json.load(open(secrets_path))
        self.lyrics_manager = LyricsManager(secrets['spotify_client_id'], secrets['spotify_client_secret'], secrets['spotify_dc_cookie'])

        self._setup_gui()

    def _setup_gui(self):
        """Sets up the main GUI window."""
        self.root.title("Beat Saber Lyrics")
        self.root.attributes('-alpha', 0.5)
        self.root.attributes('-topmost', 1)
        self.root.overrideredirect(True) # Enable for borderless window

        # Set a callback for closing the window
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _find_and_position_window(self):
        """Finds the Beat Saber window and positions the overlay underneath it."""
        try:
            hwnd = win32gui.FindWindow(None, "Beat Saber")
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                x = rect[0]
                y = rect[1]
                w = rect[2] - x
                h = rect[3] - y

                # Position the overlay in the bottom third
                tk_x = x
                tk_y = y + int(0.67 * h)
                tk_w = w
                tk_h = int(0.33 * h)
                
                self.root.geometry(f'{tk_w}x{tk_h}+{tk_x}+{tk_y}')
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error positioning window: {e}")
            return False

    def _manage_websocket_connection(self):
        """Manages the WebSocket connection and reconnects if necessary."""
        while self.is_running:
            try:
                logger.info("Attempting to establish WebSocket connection...")
                self.ws = websocket.WebSocketApp("ws://localhost:2946/BSDataPuller/MapData",
                                                 on_open=self._on_open,
                                                 on_message=self._on_message,
                                                 on_error=self._on_error,
                                                 on_close=self._on_close)
                self.ws.run_forever()
                # If run_forever() ends, it means the connection was closed.
                # We wait briefly before attempting to start a new one.
                if self.is_running:
                    logger.info("WebSocket connection closed. Attempting to reconnect in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Error managing WebSocket connection: {e}")
                if self.is_running:
                    time.sleep(5)

    def _on_open(self, ws):
        logger.info("WebSocket connection opened successfully.")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket connection closed. Status: {close_status_code}, Message: {close_msg}")

    def _on_message(self, ws, message):
        """Processes incoming messages from the WebSocket."""
        data = json.loads(message)
        
        song_hash = data.get("Hash")
        in_level = data.get("InLevel", False)

        # Scenario 1: A new song starts
        if in_level and song_hash and song_hash != self.current_song_hash:
            self.current_song_hash = song_hash
            song_name = data.get("SongName")
            song_author = data.get("SongAuthor")
            logger.info(f"New song detected: '{song_name}' by '{song_author}'")
            self.root.after(0, self.display_lyrics, song_name, song_author)

        # Scenario 2: The song ends (finished, failed, or quit)
        elif not in_level and self.current_song_hash is not None:
            is_finished = data.get("LevelFinished", False)
            is_failed = data.get("LevelFailed", False)
            is_quit = data.get("LevelQuit", False)
            if is_finished or is_failed or is_quit:
                logger.info("Song ended. Clearing lyrics display.")
                self.current_song_hash = None
                self.root.after(0, self.clear_lyrics_display)

    def display_lyrics(self, song_name, song_author):
        """Searches and displays the lyrics for a song."""
        self.clear_lyrics_display()

        logger.info(f"Searching lyrics for '{song_name}' by '{song_author}'")
        lyrics = self.lyrics_manager.search_on_spotify_with_syncedlyrics_provider(song_name, song_author)

        if lyrics:
            logger.info("Lyrics found. Creating display.")
            self.lyrics_manager.save_song_to_database(lyrics, song_name, song_author)
            self.lyrics_frame = LyricsDisplay(container=self.root, song=lyrics, color="green", speed=1)
            self.lyrics_frame.pack(fill="both", expand=True)
            self.lyrics_frame.start_lyrics()
        else:
            logger.error(f"No lyrics found for '{song_name}'.")

    def clear_lyrics_display(self):
        """Removes the current lyrics frame."""
        if self.lyrics_frame:
            self.lyrics_frame.stop_lyrics()
            self.lyrics_frame.destroy()
            self.lyrics_frame = None

    def run(self):
        """Starts the main application."""
        logger.info("Waiting for Beat Saber to start...")
        while not self._find_and_position_window() and self.is_running:
            time.sleep(2)

        if not self.is_running: return # Stop if closed in the meantime

        logger.info("Beat Saber found. Starting WebSocket thread.")
        self.ws_thread = threading.Thread(target=self._manage_websocket_connection, daemon=True)
        self.ws_thread.start()

        self.root.mainloop()

    def shutdown(self):
        """Shuts down the application cleanly."""
        logger.info("Shutting down application...")
        self.is_running = False
        if self.lyrics_frame:
            self.lyrics_frame.stop_lyrics()
        if self.ws:
            self.ws.close()
        self.root.destroy()
        logger.info("Application closed.")

if __name__ == "__main__":
    app = BeatSaberLyricsApp()
    app.run()