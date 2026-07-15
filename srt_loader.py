import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    start: float    # seconds into the episode
    end: float
    text: str


# 00:01:23,456 or 00:01:23.456
_TIME = re.compile(r'(\d+):(\d{2}):(\d{2})[,.](\d{1,3})')

_TAG = re.compile(r'<[^>]+>|\{[^}]+\}')                       # <i>...</i>, {\an8}
_BRACKETED = re.compile(r"\[[^\]]*\]|\([A-Z][A-Z\s'.-]*\)")   # [door slams], (SIGHS)
_SPEAKER = re.compile(r"^[A-Z][A-Z .'-]{1,20}:\s*")           # "MULDER: " labels


def _secs(m):
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, '0')) / 1000


def _clean(lines):
    """Strip formatting tags, sound-effect brackets, music notes, and dialogue dashes."""
    out = []
    for ln in lines:
        ln = _TAG.sub('', ln)
        ln = _BRACKETED.sub('', ln)
        if '♪' in ln or '♫' in ln:                  # song lyrics, not dialogue
            continue
        ln = re.sub(r'^-+\s*', '', ln).strip()
        if ln:
            out.append(ln)
    return ' '.join(out).strip()


def load_subtitles(path) -> list[Cue]:
    """Parse a .srt or .vtt file into ordered, cleaned cues.

    Both formats are blocks separated by blank lines, with one timing line
    containing '-->'. We key on that line instead of trusting block numbers,
    which survives the messy files subtitle tools actually produce.
    """
    raw = Path(path).read_text(encoding='utf-8-sig', errors='ignore')
    cues = []
    for block in re.split(r'\n\s*\n', raw):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        timing_i = next((i for i, ln in enumerate(lines) if '-->' in ln), None)
        if timing_i is None:
            continue                       # WEBVTT header, NOTE blocks, bare numbers
        stamps = list(_TIME.finditer(lines[timing_i]))
        if len(stamps) < 2:
            continue
        text = _clean(_SPEAKER.sub('', ln) for ln in lines[timing_i + 1:])
        if text:
            cues.append(Cue(start=_secs(stamps[0]), end=_secs(stamps[1]), text=text))
    cues.sort(key=lambda c: c.start)
    return cues


# S01E02, s1.e2, 1x02, Season 1 Episode 2 — the ways people name episode files
_EP_PATTERNS = [
    re.compile(r'[sS](\d{1,2})[\s._-]*[eE](\d{1,3})'),
    re.compile(r'\b(\d{1,2})x(\d{1,3})\b'),
    re.compile(r'[sS]eason[\s._-]*(\d{1,2}).*?[eE]pisode[\s._-]*(\d{1,3})'),
]


def find_episode_files(folder):
    """All subtitle files in a folder as (season, episode, path), in watch order.

    Season/episode come from the filename. If any file doesn't say, we fall back
    to alphabetical order for everything, which is how people number files anyway.
    """
    files = sorted(p for p in Path(folder).iterdir()
                   if p.suffix.lower() in ('.srt', '.vtt'))
    parsed = []
    for p in files:
        for pat in _EP_PATTERNS:
            m = pat.search(p.stem)
            if m:
                parsed.append((int(m.group(1)), int(m.group(2)), p))
                break
        else:
            parsed.append((None, None, p))
    if parsed and all(s is not None for s, _, _ in parsed):
        parsed.sort(key=lambda t: (t[0], t[1]))
    return parsed
