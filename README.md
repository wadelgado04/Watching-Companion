# Spoiler-Safe Watching Companion

A watch-party assistant that catches you up on a show or movie, explains its characters and lore, relives its scenes, and discusses its plot without ever revealing a single second past where you are.

You set one thing: the episode you just finished (or, for a movie, the minute you paused). Every feature respects that boundary. The language model is never shown the episodes you haven't watched, so it physically *can't* spoil them.

*Powered by Claude*

## Features

- **Catch me up**: a spoiler-free "previously on" recap of everything so far.
- **Who? What?**: explains a character, place, or invented term using only the scenes you've watched. (Forgot who someone is three seasons in? This remembers — but only as far as you've gotten.)
- **Set the scene**: paints a character or moment in vivid words, exactly as the show has played them *up to your spot*. A betrayal that comes later won't color the portrait until you've seen it.
- **Discuss**: a watch-party chat partner that analyzes characters, motives, and theories, grounded in what you've watched, with no spoilers and a memory of the conversation.

Plus a built-in **leak test**: an evaluation that scans a recap for any name introduced after your current episode, and proves the guard works by catching the leaks in a recap that *was* allowed to watch ahead.

## The trick: shows don't have text — except they do

A show's plot lives in its dialogue, and its dialogue lives in **subtitle files**. An `.srt` file is timestamped line by line, which makes it *better* than a book for this: every sentence knows exactly when it was spoken.

1. **Extract** each episode's dialogue from its subtitle file, in order (`srt_loader.py`), cleaning out sound effects, music notes, and formatting.
2. **Chunk** it into ordered passages, each tagged with its episode and timestamps (`chunker.py`). Episode order comes from the filenames (`S01E02`, `1x02`, etc.).
3. **Bound**: `chunks_through(chunks, max_ep=N)` returns only what's been watched — or `max_seconds` for a movie you paused partway. Every feature draws from this.
4. **Layer features on top** — the recap summarizes the allowed dialogue; who/what and set-the-scene pull the relevant allowed scenes; discuss runs semantic search over a vector index (`show_index.py`) bounded to the allowed episodes.

Because the recap is built only from episodes 1–N, it can't contain a spoiler — and the leak test proves it by checking for names that first appear later.

## Setup

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/).

```
python -m pip install -r requirements.txt
```

Create a `.env` file (copy `.env.example`) with your key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Make a `subs/` folder and put one subtitle file per episode in it, named so the order is clear (`MyShow.S01E01.srt`, `MyShow.S01E02.srt`, …). For a movie, point at the single file instead. Set the path in `recap.py`:

```python
SHOW = "subs"            # or "mymovie.srt" for a film
```

Run the app:

```
python -m streamlit run app.py
```

Each piece also runs on its own, e.g. `python recap.py` or `python leak_test.py`.

> Semantic search for the Discuss tab uses Chroma's built-in local embedding model (the Claude API doesn't do embeddings). It downloads once on first use and needs no key.

## Files

| File            | What it does                                                                 |
| --------------- | ---------------------------------------------------------------------------- |
| `app.py`        | The Streamlit app that ties everything together                              |
| `srt_loader.py` | Subtitle files → clean, timestamped dialogue                                 |
| `chunker.py`    | Splits the show into episode-tagged chunks; defines the spoiler boundary     |
| `show_index.py` | Vector index + spoiler-bounded semantic search                               |
| `recap.py`      | The spoiler-free recap, and the shared Claude client every feature calls     |
| `leak_test.py`  | The evaluation that proves recaps don't leak                                 |
| `vocab.py`      | Explain a character, place, or term in context                               |
| `visualize.py`  | Paint a character or scene in words                                          |
| `discuss.py`    | The discussion chat                                                          |

## A note on subtitles

This tool works on subtitles *you* provide. It includes none — bring your own `.srt`/`.vtt` files for shows and movies you own (many players and tools can extract the subtitle track from your own media files).

## Publishing your own copy

To own and run this yourself:

1. Create a new GitHub repository under your account and push this code to it.
2. Put your name in `LICENSE`.
3. To host it, connect the repo to [Streamlit Community Cloud](https://share.streamlit.io) (free) and add `ANTHROPIC_API_KEY` under the app's **Secrets** — never commit your `.env`.

## Built with

Python · Streamlit · Claude (Anthropic API) · Chroma

---

## License

MIT — see [LICENSE](LICENSE).
