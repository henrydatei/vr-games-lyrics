import time

class Timer:
    def __init__(self, speed=1):
        self.start_time = None
        self.pause_time = None
        self.paused_duration = 0
        self.is_running = False
        self.speed = speed

    def start(self):
        if not self.is_running:
            self.start_time = time.time()
            self.is_running = True

    def stop(self):
        if self.is_running:
            self.is_running = False
            self.start_time = None
            self.pause_time = None
            self.paused_duration = 0

    def pause(self):
        if self.is_running and self.pause_time is None:
            self.pause_time = time.time()
            self.is_running = False

    def unpause(self):
        if not self.is_running and self.pause_time is not None:
            self.paused_duration += time.time() - self.pause_time
            self.pause_time = None
            self.is_running = True

    def get_time(self):
        if self.is_running:
            elapsed_time = (time.time() - self.start_time) * self.speed
            paused_time = self.paused_duration * self.speed
            return int((elapsed_time - paused_time) * 1000)
