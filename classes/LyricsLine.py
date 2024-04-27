import dataclasses

@dataclasses.dataclass
class LyricsLine:
    text: str
    startMs: int
    endMs: int
    durationMs: int
    
    def convert_ms_to_human_readable(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}.{(ms % 1000):03d}"
    
    def __str__(self) -> str:
        return f"[{self.convert_ms_to_human_readable(self.startMs)}-{self.convert_ms_to_human_readable(self.endMs)}]: {self.text} [{self.durationMs} ms]"