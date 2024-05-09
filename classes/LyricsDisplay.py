import tkinter as tk
from tkinter import ttk
import threading
import logging

from classes.Song import Song
from classes.Timer import Timer

class LyricsDisplay(ttk.Frame):
    def __init__(self, container, song: Song, color: str, speed: float, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.logger.debug("Creating LyricsDisplay")
        s = ttk.Style()
        s.configure('TFrame', background = 'green')
        s.configure('Frame1.TFrame', background = color)
        self.canvas = tk.Canvas(self, background = color)
        self.canvas.pack(fill = "both", expand = True)
        # self.canvas = ttk.Frame(self, style = 'Frame1.TFrame')
        # self.scrollbar = ttk.Scrollbar(self, orient = "vertical", command = self.canvas.yview)
        # self.scrollable_frame = ttk.Frame(self.canvas, style = 'Frame1.TFrame')
        
        # self.logger.debug("Creating button")
        # self.button = tk.Button(self.canvas, text = "Pause", command = self.pause_lyrics)
        # self.button.pack(anchor = "e", padx = 10, pady = 40)
        
        self.logger.debug("Setting up variables")
        self.song = song
        self.color = color
        self.speed = speed if speed != 0 else 1
        
        self.logger.debug("Creating timer")
        self.timer = Timer(speed = self.speed) # this timer should be in sync with the timer in the game. So when the level starts, this timer should start too.
        
        self.logger.debug("Setting up the lyrics lines variables")
        self.preview_lines = []
        self.current_line = -1
        self.lines_to_show = 4
        
        self.logger.debug("Starting main loop")
        self.run_main_loop = True
        self.main_thread = threading.Thread(target = self.main_loop)
        self.main_thread.start()

        self.logger.debug("Setting up the canvas and scrollbar")
        # Ability to scroll through the lyrics
        # from https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
        # self.scrollable_frame.bind(
        #     "<Configure>",
        #     lambda e: self.canvas.configure(
        #         scrollregion = self.canvas.bbox("all")
        #     )
        # )
        # self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        # self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux_up)
        # self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux_down)
        # self.canvas.create_window((0, 0), window = self.scrollable_frame, anchor = "nw")
        # self.canvas.configure(yscrollcommand = self.scrollbar.set)
        # self.canvas.pack(side = "left", fill = "both", expand = True)
        # self.scrollbar.pack(side = "right", fill = "y")
        
        self.logger.debug("Displaying the preview lyrics")            
        for i in range(self.lines_to_show):
            line = tk.Label(self.canvas, text = self.song.lines[i].text, font = ("Roboto", 42), background = color, fg = "black")
            self.preview_lines.append(line)
            line.pack(anchor = "n", padx = 10, expand = True)
        
    def start_lyrics(self) -> None:
        """Starts the timer and the lyrics will start scrolling.
        """
        self.logger.debug("Lyrics starting")
        self.timer.start()
        self.logger.info("Lyrics started")
        
    def stop_lyrics(self) -> None:
        """Stops the timer and the lyrics will stop scrolling.
        """
        self.logger.debug("Lyrics stopping")
        self.timer.stop()
        self.run_main_loop = False
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
        if i < 0 or i >= len(self.song.lines):
            self.logger.error(f"Invalid line number, i = {i}, len(self.lines) = {len(self.song.lines)}")
        else:
            # Erase the text of all the preview lines
            for line in self.preview_lines:
                line.config(text = "")
            # Show the ith line in white in the first preview line
            self.preview_lines[0].config(text = self.song.lines[i].text, fg = "white")
            # Show the next lines in black in the next preview lines
            for j in range(1, self.lines_to_show):
                if i + j < len(self.song.lines):
                    self.preview_lines[j].config(text = self.song.lines[i + j].text, fg = "black")
        
    def main_loop(self) -> None:
        """Main loop of the lyrics display. This loop will run in a separate thread and will keep track of the current time and show the ith line of the lyrics when the time comes.
        """
        while self.run_main_loop:
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