import dataclasses
from typing import List, Optional

from classes.LyricsLine import LyricsLine

@dataclasses.dataclass
class Song:
    lines: List[LyricsLine]
    cover_link: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    
    def __str__(self) -> str:
        return f"Song: {self.title} by {self.artist} \nCoverlink: {self.cover_link} \n" + "\n".join([str(line) for line in self.lines])
    
    def __post_init__(self):
        self.lines.sort(key=lambda x: x.startMs)
        self.durationMs = self.lines[-1].endMs - self.lines[0].startMs