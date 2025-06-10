import tkinter as tk
from tkinter import ttk
import threading
import logging
import time

from classes.Song import Song
from classes.Timer import Timer

class LyricsDisplay(ttk.Frame):
    def __init__(self, container, song: Song, color: str, speed: float, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.logger = logging.getLogger(__name__)
        
        s = ttk.Style()
        s.configure('TFrame', background='green')
        s.configure('Frame1.TFrame', background=color)
        self.canvas = tk.Canvas(self, background=color)
        self.canvas.pack(fill="both", expand=True)
        
        self.song = song
        self.speed = speed if speed != 0 else 1
        
        self.timer = Timer(speed=self.speed)
        
        self.preview_lines = []
        self.current_song_line_index = -1
        self.lines_to_show = 4
        # The index of the active line in the preview
        self.active_line_index_in_preview = 1

        self.run_main_loop = True
        self.main_thread = threading.Thread(target=self.main_loop)

        # Create the labels for the preview
        for _ in range(self.lines_to_show):
            line = tk.Label(self.canvas, text="", font=("Roboto", 42), background=color, fg="black")
            line.pack(anchor="n", padx=10, expand=True)
            self.preview_lines.append(line)

        # Show the initial state
        self.show_ith_line(0)
        self.main_thread.start()

    def start_lyrics(self) -> None:
        """Starts the timer, and the lyrics will start scrolling."""
        self.logger.debug("Lyrics starting")
        self.timer.start()
        self.logger.info("Lyrics started")
        
    def stop_lyrics(self) -> None:
        """Stops the timer, and the lyrics will stop scrolling."""
        self.logger.debug("Lyrics stopping")
        self.run_main_loop = False
        self.timer.stop()
        self.logger.info("Lyrics stopped")
        
    def pause_lyrics(self) -> None:
        """Pauses or unpauses the timer."""
        if self.timer.is_running:
            self.timer.pause()
            self.logger.info("Lyrics paused")
        elif self.timer.start_time is not None: # only unpause if it was started before
            self.timer.unpause()
            self.logger.info("Lyrics unpaused")

    def show_ith_line(self, i: int) -> None:
        """
        Shows the ith line of the lyrics, centered on the active preview line.
        'i' is the index of the line in the original song lyrics.
        """
        if i < 0 or i >= len(self.song.lines):
            self.logger.error(f"Invalid line number: i={i}")
            return

        for j in range(self.lines_to_show):
            # Calculate the index of the song line to display
            song_line_to_display_index = i + (j - self.active_line_index_in_preview)
            
            preview_label = self.preview_lines[j]
            
            if 0 <= song_line_to_display_index < len(self.song.lines):
                # The line is valid
                line_text = self.song.lines[song_line_to_display_index].text
                preview_label.config(text=line_text)

                # Highlight the active line in white
                if j == self.active_line_index_in_preview:
                    preview_label.config(fg="white")
                else:
                    preview_label.config(fg="black")
            else:
                # Outside the song text -> empty label
                preview_label.config(text="")
                        
    def main_loop(self) -> None:
        """Main loop of the lyrics display."""
        while self.run_main_loop:
            if self.timer.is_running:
                current_time = self.timer.get_time()

                # Find the next line whose start time has not been reached
                i = 0
                while i < len(self.song.lines) and self.song.lines[i].startMs <= current_time:
                    i += 1

                # The current line is the one before
                current_index = i - 1
                
                if current_index != self.current_song_line_index:
                    self.current_song_line_index = current_index
                    if current_index >= 0:
                        self.show_ith_line(current_index)
                
                if i == len(self.song.lines) and current_time >= self.song.durationMs:
                    self.logger.info("Lyrics ended")
                    self.stop_lyrics()

            time.sleep(0.05) # Reduce CPU load

    def jump_to_time(self, time_in_ms: int) -> None:
        """Jumps to the specified time in milliseconds."""
        self.timer.set_time(time_in_ms)
        self.logger.info(f"Jumped to time {time_in_ms} ms")