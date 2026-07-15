import re

import recap
from chunker import chunks_through


def explain_term(chunks, term, max_ep=None, max_seconds=None):
    """Who is this character? What is that thing they keep mentioning?
    Explained from only the dialogue you've watched.

    Returns (explanation, passages_found). passages_found == 0 means not seen yet.
    """
    term = term.strip()
    allowed = chunks_through(chunks, max_ep=max_ep, max_seconds=max_seconds)
    pattern = re.compile(r'\b' + re.escape(term.lower()) + r'\b')
    hits = [c for c in allowed if pattern.search(c.text.lower())]

    if not hits:
        return (f"“{term}” hasn't come up yet in what you've watched, so "
                "there's nothing on screen to explain it from. If it's part of the "
                "story, you'll meet it soon."), 0

    context = "\n\n---\n\n".join(f"[{c.label}] {c.text}" for c in hits[:6])[:20000]
    system = ("You explain a character, place, or term for someone watching a show or "
              "film, using ONLY the subtitle dialogue they have watched so far. Say who "
              "or what it is in the context of this story. If it is an invented term, "
              "infer its meaning from how it is used. Never use anything from later in "
              "the show, never use outside knowledge of it, and never hint at what "
              "comes next. Keep it to 2 to 4 sentences.")
    user = (f'The viewer asked about "{term}". Here is the dialogue where it comes up '
            f'in what they have watched:\n\n{context}\n\n'
            f'Explain who or what "{term}" is here.')
    return recap.ask(system, user, temperature=0.3), len(hits)
