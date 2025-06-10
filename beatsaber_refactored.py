import websocket
import threading
import tkinter as tk
import os
import json
import logging
import win32gui
import time
import sys

from classes.LyricsManager import LyricsManager
from classes.LyricsDisplay import LyricsDisplay

# Logging-Konfiguration am Anfang
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BeatSaberLyricsApp:
    def __init__(self):
        """Initialisiert die Hauptanwendung."""
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
        """Konfiguriert das Hauptfenster der GUI."""
        self.root.title("Beat Saber Lyrics")
        self.root.attributes('-alpha', 0.5)
        self.root.attributes('-topmost', 1)
        # self.root.overrideredirect(True) # Aktivieren für rahmenloses Fenster

        close_button = tk.Button(self.root, text="X", command=self.shutdown)
        close_button.pack(anchor="ne", padx=5, pady=5)
        
        # Setzt einen Callback für das Schließen des Fensters
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _find_and_position_window(self):
        """Sucht das Beat Saber Fenster und positioniert das Overlay darunter."""
        try:
            hwnd = win32gui.FindWindow(None, "Beat Saber")
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                x = rect[0]
                y = rect[1]
                w = rect[2] - x
                h = rect[3] - y
                
                # Positioniere das Overlay im unteren Drittel
                tk_x = x
                tk_y = y + int(0.67 * h)
                tk_w = w
                tk_h = int(0.33 * h)
                
                self.root.geometry(f'{tk_w}x{tk_h}+{tk_x}+{tk_y}')
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Fehler beim Positionieren des Fensters: {e}")
            return False

    def _manage_websocket_connection(self):
        """Verwaltet die WebSocket-Verbindung und stellt sie bei Bedarf wieder her."""
        while self.is_running:
            try:
                logger.info("Versuche, eine WebSocket-Verbindung herzustellen...")
                self.ws = websocket.WebSocketApp("ws://localhost:2946/BSDataPuller/MapData",
                                                 on_open=self._on_open,
                                                 on_message=self._on_message,
                                                 on_error=self._on_error,
                                                 on_close=self._on_close)
                self.ws.run_forever()
                # Wenn run_forever() endet, bedeutet das, die Verbindung wurde geschlossen.
                # Wir warten kurz, bevor wir einen neuen Versuch starten.
                if self.is_running:
                    logger.info("WebSocket-Verbindung geschlossen. Versuche in 5 Sekunden erneut...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Fehler in der WebSocket-Verwaltung: {e}")
                if self.is_running:
                    time.sleep(5)

    def _on_open(self, ws):
        logger.info("WebSocket-Verbindung erfolgreich geöffnet.")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket-Fehler: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket-Verbindung geschlossen. Status: {close_status_code}, Nachricht: {close_msg}")

    def _on_message(self, ws, message):
        """Verarbeitet eingehende Nachrichten vom WebSocket."""
        data = json.loads(message)
        
        song_hash = data.get("Hash")
        in_level = data.get("InLevel", False)

        # Szenario 1: Ein neues Lied startet
        if in_level and song_hash and song_hash != self.current_song_hash:
            self.current_song_hash = song_hash
            song_name = data.get("SongName")
            song_author = data.get("SongAuthor")
            logger.info(f"Neues Lied erkannt: '{song_name}' von '{song_author}'")
            self.root.after(0, self.display_lyrics, song_name, song_author)

        # Szenario 2: Das Lied endet (abgeschlossen, fehlgeschlagen oder verlassen)
        elif not in_level and self.current_song_hash is not None:
            is_finished = data.get("LevelFinished", False)
            is_failed = data.get("LevelFailed", False)
            is_quit = data.get("LevelQuit", False)
            if is_finished or is_failed or is_quit:
                logger.info("Lied beendet. Lyrics werden entfernt.")
                self.current_song_hash = None
                self.root.after(0, self.clear_lyrics_display)
        
        # Szenario 3: Modifikatoren oder Übungsmodus ändern sich während des Spiels
        # if in_level and self.lyrics_frame:
        #     # Geschwindigkeitsänderungen durch Modifikatoren
        #     modifiers = data.get("Modifiers", {})
        #     speed = 1.0
        #     if modifiers.get("SuperFastSong"): speed = 1.5
        #     elif modifiers.get("FasterSong"): speed = 1.2
        #     elif modifiers.get("SlowerSong"): speed = 0.85
            
        #     # Übungsmodus
        #     if data.get("PracticeMode"):
        #         practice_mods = data.get("PracticeModeModifiers", {})
        #         speed = practice_mods.get("SongSpeedMul", speed)
        #         start_time_ms = practice_mods.get("SongStartTime", 0) * 1000
        #         if self.lyrics_frame.speed != speed:
        #             self.lyrics_frame.speed = speed
        #         # jump_to_time ist hier eventuell nicht ideal, da es bei jeder Nachricht getriggert wird.
        #         # Besser wäre es, den Startzeitpunkt nur einmal zu setzen.
        #         # Für den Moment lassen wir es einfacher.

        #     self.lyrics_frame.speed = speed

    def display_lyrics(self, song_name, song_author):
        """Sucht und zeigt die Lyrics für einen Song an."""
        self.clear_lyrics_display()

        logger.info(f"Suche Lyrics für '{song_name}' von '{song_author}'")
        # Suchreihenfolge definieren
        # lyrics = self.lyrics_manager.search_in_database(song_name, song_author)
        lyrics = self.lyrics_manager.search_on_spotify_with_syncedlyrics_provider(song_name, song_author)
        # if not lyrics:
        #     lyrics = self.lyrics_manager.search_on_spotify_with_syncedlyrics_provider(song_name, song_author)
        # if not lyrics:
        #     lyrics = self.lyrics_manager.search_on_spotify(song_name, song_author)
        # if not lyrics:
        #     lyrics = self.lyrics_manager.search_on_netease(song_name, song_author)

        if lyrics:
            logger.info("Lyrics gefunden. Anzeige wird erstellt.")
            self.lyrics_manager.save_song_to_database(lyrics, song_name, song_author)
            self.lyrics_frame = LyricsDisplay(container=self.root, song=lyrics, color="green", speed=1)
            self.lyrics_frame.pack(fill="both", expand=True)
            self.lyrics_frame.start_lyrics()
        else:
            logger.error(f"Keine Lyrics für '{song_name}' gefunden.")

    def clear_lyrics_display(self):
        """Entfernt das aktuelle Lyrics-Frame."""
        if self.lyrics_frame:
            self.lyrics_frame.stop_lyrics()
            self.lyrics_frame.destroy()
            self.lyrics_frame = None

    def run(self):
        """Startet die Hauptanwendung."""
        logger.info("Warte auf Start von Beat Saber...")
        while not self._find_and_position_window() and self.is_running:
            time.sleep(2)
        
        if not self.is_running: return # Beenden, wenn in der Zwischenzeit geschlossen wurde

        logger.info("Beat Saber gefunden. Starte WebSocket-Thread.")
        self.ws_thread = threading.Thread(target=self._manage_websocket_connection, daemon=True)
        self.ws_thread.start()

        self.root.mainloop()

    def shutdown(self):
        """Fährt die Anwendung sauber herunter."""
        logger.info("Anwendung wird heruntergefahren...")
        self.is_running = False
        if self.lyrics_frame:
            self.lyrics_frame.stop_lyrics()
        if self.ws:
            self.ws.close()
        self.root.destroy()
        logger.info("Anwendung beendet.")

if __name__ == "__main__":
    app = BeatSaberLyricsApp()
    app.run()