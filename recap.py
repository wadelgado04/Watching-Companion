import os
from anthropic import Anthropic
from dotenv import load_dotenv

from chunker import load_show, chunks_through

# ---- swap shows here ----
SHOW = "The.Super.Mario.Galaxy.Movie.DEMO.srt"
CURRENT_EPISODE = 3           # the episode you just finished (in watch order)
CURRENT_MINUTE = None         # for a movie: how many minutes in you paused (else None)
MODEL = "claude-sonnet-4-5"   # swap for "claude-haiku-4-5" to run cheaper
MAX_TOKENS = 1200
MAX_CHARS = 350_000           # safety cap so a huge season can't overflow the model

load_dotenv()
client = Anthropic()          # reads ANTHROPIC_API_KEY from .env / environment

SYSTEM = (
    "You help a viewer remember what has happened in a show or film so far. You "
    "are given the dialogue (from subtitles) UP TO the viewer's current point "
    "and nothing beyond it. Summarize only what is in that dialogue. Never "
    "invent, infer, or hint at anything that is not explicitly there, and never "
    "foreshadow what might happen next."
)


def ask(system, messages, temperature=0.3, max_tokens=MAX_TOKENS):
    """One place every feature calls Claude through. `messages` is a string or
    a [{'role','content'}, ...] list."""
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    r = client.messages.create(model=MODEL, max_tokens=max_tokens,
                               temperature=temperature, system=system,
                               messages=messages)
    return r.content[0].text


def _spot(max_ep, max_minute):
    return (f"{max_minute} minutes into it" if max_minute is not None
            else f"episode {max_ep}")


def build_recap_context(show_path, max_ep=None, max_minute=None):
    """Everything the viewer has watched, up to their spot, as one string."""
    chunks = load_show(show_path)
    allowed = chunks_through(chunks, max_ep=max_ep,
                             max_seconds=max_minute * 60 if max_minute is not None else None)
    if not allowed:
        raise SystemExit(
            f"No dialogue found up to {_spot(max_ep, max_minute)}. "
            f"Check the episode number and that '{show_path}' has subtitle files."
        )
    text = "\n\n".join(f"[{c.label}] {c.text}" for c in allowed)
    trimmed = len(text) > MAX_CHARS
    if trimmed:
        text = text[-MAX_CHARS:]          # keep the most recent context if huge
    return text, allowed, trimmed


def make_recap(show_path=SHOW, max_ep=CURRENT_EPISODE, max_minute=CURRENT_MINUTE):
    context, allowed, trimmed = build_recap_context(show_path, max_ep, max_minute)
    note = " (trimmed to recent events)" if trimmed else ""
    print(f"Recapping {show_path} up to {_spot(max_ep, max_minute)}: "
          f"{len(allowed)} chunks, {len(context):,} chars{note}\n")

    user = (
        f"Here is the dialogue for everything I've watched so far, up to "
        f"{_spot(max_ep, max_minute)}:\n\n{context}\n\n"
        "Give me a spoiler-free 'previously on' recap so I can pick up where I "
        "left off. Cover the main plot, the key characters, and where things "
        "stand right now. Keep it to a few short paragraphs."
    )
    return ask(SYSTEM, user, temperature=0.3)


if __name__ == "__main__":
    print(make_recap())
