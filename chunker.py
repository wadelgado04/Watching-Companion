from dataclasses import dataclass
from pathlib import Path

from srt_loader import load_subtitles, find_episode_files


@dataclass
class Chunk:
    id: int                 # order across the whole show, 0 = the very start
    text: str
    ep: int                 # global episode number in watch order, 1 = pilot
    season: int | None      # from the filename; None if it didn't say
    episode: int | None
    label: str              # "S1E2", or the title for a movie
    t_start: float          # seconds into the episode where this chunk begins
    t_end: float            # where it ends
    pct: float              # how far into the episode it starts (0.0-1.0)


_SCENE_GAP = 30.0    # seconds of silence that we treat as a scene break


def _chunk_cues(cues, target_chars=1200):
    """Group consecutive cues into passages of about `target_chars`, also
    breaking at any long silence (a scene change). That keeps each chunk's
    time-span tight, so the movie boundary ('I paused at minute 40') doesn't
    seal off dialogue from long before the pause just because its chunk
    happened to end after it.

    A chunk never crosses an episode line (each episode is chunked separately),
    so a chunk tagged 'episode 3' can never secretly carry episode 4 dialogue
    that the spoiler filter would leak.
    """
    duration = max((c.end for c in cues), default=0.0) or 1.0
    groups = []
    buf, start, end, length = [], None, 0.0, 0

    def flush():
        nonlocal buf, start, length
        if buf:
            groups.append((' '.join(buf), start, end, round(start / duration, 4)))
        buf, start, length = [], None, 0

    for c in cues:
        if buf and c.start - end > _SCENE_GAP:
            flush()
        if start is None:
            start = c.start
        buf.append(c.text)
        end = c.end
        length += len(c.text)
        if length >= target_chars:
            flush()
    flush()
    return groups


def load_show(path, target_chars=1200) -> list[Chunk]:
    """Subtitles → ordered, episode-tagged chunks.

    Point it at a folder of episode files for a series, or a single .srt/.vtt
    for a movie (which is treated as a one-episode series — the boundary then
    works by timestamp instead of episode).
    """
    path = Path(path)
    if path.is_dir():
        episodes = find_episode_files(path)
        if not episodes:
            raise SystemExit(f"No .srt or .vtt files found in '{path}'.")
        sources = [(s, e, f"S{s}E{e}" if s is not None else f.stem, f)
                   for s, e, f in episodes]
    else:
        sources = [(None, None, path.stem, path)]

    chunks, cid = [], 0
    for ep_num, (season, episode, label, file) in enumerate(sources, start=1):
        cues = load_subtitles(file)
        for text, t0, t1, pct in _chunk_cues(cues, target_chars):
            chunks.append(Chunk(id=cid, text=text, ep=ep_num, season=season,
                                episode=episode, label=label,
                                t_start=t0, t_end=t1, pct=pct))
            cid += 1
    return chunks


def chunks_through(chunks, max_ep=None, max_seconds=None):
    """
    The spoiler boundary: keep only the chunks at or before the viewer's spot.
    Everything past it stays invisible.

    For a series, pass max_ep (they've finished that episode). For a movie,
    pass max_seconds (how far into it they are); a chunk must END by then, so
    a passage straddling the boundary can't smuggle in the next scene.
    """
    out = chunks
    if max_ep is not None:
        out = [c for c in out if c.ep <= max_ep]
    if max_seconds is not None:
        out = [c for c in out if c.ep < (max_ep or 1) or c.t_end <= max_seconds]
    return out


def fmt_time(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
