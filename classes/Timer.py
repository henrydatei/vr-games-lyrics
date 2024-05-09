import time
import logging

class Timer:
    def __init__(self, speed: float = 1):
        self.start_time = None
        self.pause_time = None
        self.paused_duration = 0
        self.is_running = False
        self.speed = speed
        
        logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def start(self):
        self.logger.debug("Timer starting")
        if not self.is_running:
            self.logger.debug("Timer is not running, starting it")
            self.start_time = time.time()
            self.is_running = True
            self.logger.debug("Timer started")

    def stop(self):
        self.logger.debug("Timer stopping")
        if self.is_running:
            self.logger.debug("Timer is running, stopping it")
            self.is_running = False
            self.start_time = None
            self.pause_time = None
            self.paused_duration = 0
            self.logger.debug("Timer stopped")

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

    def set_time(self, milliseconds: int):
        if self.is_running:
            self.start_time = time.time() - milliseconds/self.speed / 1000 - self.paused_duration