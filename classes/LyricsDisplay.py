import tkinter as tk
from tkinter import ttk
import threading
import logging

from classes.Song import Song
from classes.Timer import Timer

class LyricsDisplay(ttk.Frame):
    def __init__(self, container, song: Song, color: str, speed: float, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        s = ttk.Style()
        s.configure('TFrame', background = 'green')
        s.configure('Frame1.TFrame', background = color)
        self.canvas = tk.Canvas(self, background = color)
        self.scrollbar = ttk.Scrollbar(self, orient = "vertical", command = self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style = 'Frame1.TFrame')
        
        self.button = tk.Button(self.canvas, text = "Pause", command = self.pause_lyrics)
        self.button.pack(anchor = "e", padx = 10, pady = 40)
        
        self.song = song
        self.color = color
        self.speed = speed if speed != 0 else 1
        
        self.timer = Timer(speed = self.speed) # this timer should be in sync with the timer in the game. So when the level starts, this timer should start too.
        self.lines = []
        self.current_line = -1
        self.main_thread = threading.Thread(target = self.main_loop)
        self.main_thread.start()

        # Ability to scroll through the lyrics
        # from https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion = self.canvas.bbox("all")
            )
        )
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux_up)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux_down)
        self.canvas.create_window((0, 0), window = self.scrollable_frame, anchor = "nw")
        self.canvas.configure(yscrollcommand = self.scrollbar.set)
        self.canvas.pack(side = "left", fill = "both", expand = True)
        self.scrollbar.pack(side = "right", fill = "y")
        
        # Display the lyrics
        for line in self.song.lines:
            lineLabel = tk.Label(self.scrollable_frame, text = line.text, font = ("Roboto", 42), background = color, fg = "black")
            self.lines.append(lineLabel)
            lineLabel.pack(anchor = "w", padx = 10, expand = True)
            
        logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def start_lyrics(self) -> None:
        """Starts the timer and the lyrics will start scrolling.
        """
        self.timer.start()
        self.logger.info("Lyrics started")
        
    def stop_lyrics(self) -> None:
        """Stops the timer and the lyrics will stop scrolling.
        """
        self.timer.stop()
        self.logger.info("Lyrics stopped")
        
    def pause_lyrics(self) -> None:
        """Pauses the timer and the lyrics will pause scrolling. When the lyrics are paused, the button text will change to "Unpause". When the lyrics are unpaused, the button text will change to "Pause".
        """
        if self.timer.is_running:
            self.timer.pause()
            self.button.config(text = "Unpause")
            self.logger.info("Lyrics paused")
        else:
            self.timer.unpause()
            self.button.config(text = "Pause")
            self.logger.info("Lyrics unpaused")
    
    def on_mousewheel(self, event: tk.Event) -> None:
        """Handles the mousewheel event on Windows and MacOS.
        """
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def on_mousewheel_linux_up(self, event: tk.Event) -> None:
        """Handles the mousewheel event on Linux."""
        self.canvas.yview_scroll(-1, "units")
    
    def on_mousewheel_linux_down(self, event: tk.Event) -> None:
        """Handles the mousewheel event on Linux."""
        self.canvas.yview_scroll(1, "units")
        
    def show_ith_line(self, i: int) -> None:
        """Shows the ith line of the lyrics in white and scrolls to the ith line.

        Args:
            i (int): The line number to show. Starts from 0 and goes up to len(self.lines) - 1.
        """
        if i < 0 or i >= len(self.lines):
            self.logger.error("Invalid line number")
        else:
            # Make all lines black
            for j in range(len(self.lines)):
                self.lines[j].config(fg = "black")
            # Make ith line white
            self.lines[i].config(fg = "white")
            # Scroll to ith line
            self.canvas.yview_moveto(i/len(self.lines))
        
    def main_loop(self) -> None:
        """Main loop of the lyrics display. This loop will run in a separate thread and will keep track of the current time and show the ith line of the lyrics when the time comes.
        """
        while True:
            if self.timer.is_running:
                current_time = self.timer.get_time()
                i = 0
                while i < len(self.song.lines) and self.song.lines[i].startMs < current_time:
                    i += 1
                if i != self.current_line:
                    self.current_line = i
                    self.show_ith_line(i)
                if i == len(self.song.lines):
                    self.logger.info("Lyrics ended")
                    self.stop_lyrics()
                    break
                        
    def jump_to_time(self, time_in_ms: int) -> None:
        """Jumps to the specified time in milliseconds."""
        self.timer.set_time(time_in_ms)
        self.logger.info(f"Jumped to time {time_in_ms} ms")