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

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SynthRidersLyricsApp:
    def __init__(self):
        """Initalises the Synth Riders Lyrics application."""
        self.root = tk.Tk()
        self.is_running = True
        self.ws = None
        self.ws_thread = None
        self.lyrics_frame = None
        self.is_song_active = False
        self.is_game_paused = False
        
        secrets_path = os.path.join(os.path.dirname(__file__), "secrets.json")
        secrets = json.load(open(secrets_path))
        self.lyrics_manager = LyricsManager(secrets['spotify_client_id'], secrets['spotify_client_secret'], secrets['spotify_dc_cookie'])

        self._setup_gui()

    def _setup_gui(self):
        """Konfiguriert das Hauptfenster der GUI."""
        self.root.title("Synth Riders Lyrics")
        self.root.attributes('-alpha', 0.5)
        self.root.attributes('-topmost', 1)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _find_and_position_window(self):
        """Searches for the Synth Riders window and positions the overlay."""
        try:
            hwnd = win32gui.FindWindow(None, "SynthRiders")
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
                tk_x, tk_y, tk_w, tk_h = x, y + int(0.67 * h), w, int(0.33 * h)
                self.root.geometry(f'{tk_w}x{tk_h}+{tk_x}+{tk_y}')
                return True
            return False
        except Exception:
            return False

    def _manage_websocket_connection(self):
        """Manages the WebSocket connection for Synth Riders."""
        while self.is_running:
            try:
                logger.info("Connecting to Synth Riders WebSocket...")
                # Default port for Synth Riders is 9000
                self.ws = websocket.WebSocketApp("ws://localhost:9000/",
                                                 on_open=lambda ws: logger.info("Synth Riders WebSocket connected."),
                                                 on_message=self._on_message,
                                                 on_error=lambda ws, err: logger.error(f"SR-WebSocket error: {err}"),
                                                 on_close=lambda ws, code, msg: logger.warning("SR-WebSocket connection closed."))
                self.ws.run_forever()
                if self.is_running:
                    logger.info("Connection lost. Reconnecting in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Error in WebSocket management: {e}")
                if self.is_running:
                    time.sleep(5)

    def _on_message(self, ws, message):
        """Processes messages from the Synth Riders WebSocket."""
        try:
            msg_data = json.loads(message)
            event_type = msg_data.get("eventType")
            data = msg_data.get("data", {})

            if event_type == "SongStart" and not self.is_song_active:
                self.is_song_active = True
                self.is_game_paused = False
                song_title = data.get("song")
                song_author = data.get("author")
                logger.info(f"SongStart detected: '{song_title}' by '{song_author}'")
                self.root.after(0, self.display_lyrics, song_title, song_author)

            elif event_type == "PlayTime" and self.lyrics_frame:
                play_time_ms = int(data.get("playTimeMS", 0))
                # Continuous synchronization is possible, but often not necessary.
                # We can simply update the time.
                # self.lyrics_frame.jump_to_time(play_time_ms) # Optional: for hard resyncs

            # song quit, failed, or finished
            elif (event_type == "ReturnToMenu" or (event_type == "SceneChange" and data.get("sceneName", None) == "3.GameEnd") or event_type == "SongEnd") and self.is_song_active:
                self.is_song_active = False
                logger.info("Returning to menu, song ended. Clearing lyrics display.")
                self.root.after(0, self.clear_lyrics_display)

        except json.JSONDecodeError:
            logger.error(f"Could not decode JSON from Synth Riders: {message}")
        except Exception as e:
            logger.error(f"Error processing Synth Riders message: {e}")

    def display_lyrics(self, song_name, song_author):
        """Searches for and displays the lyrics for a song."""
        self.clear_lyrics_display()

        logger.info(f"Searching for lyrics for '{song_name}' by '{song_author}'...")
        lyrics = self.lyrics_manager.search_on_spotify_with_syncedlyrics_provider(song_name, song_author)

        if lyrics:
            self.lyrics_manager.save_song_to_database(lyrics, song_name, song_author)
            logger.info("Lyrics found. Creating display.")
            self.lyrics_frame = LyricsDisplay(container=self.root, song=lyrics, color="purple", speed=1)
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
        logger.info("Waiting for Synth Riders to start...")
        while not self._find_and_position_window() and self.is_running:
            time.sleep(2)
        
        if not self.is_running: return

        logger.info("Synth Riders found. Starting WebSocket thread.")
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
    app = SynthRidersLyricsApp()
    app.run()