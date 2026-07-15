import re

import recap
from chunker import chunks_through

_STOP = {"the", "a", "an", "of", "and", "in", "on", "at", "to", "with", "her", "his"}

_STYLES = {
    "cinematic": ("a lush, cinematic scene: camera angles, lighting, atmosphere, "
                  "the feel of a key frame from the show itself"),
    "novelistic": ("a passage of vivid literary prose, as if a novelist were "
                   "adapting this moment of the show to the page"),
}


def set_scene(chunks, subject, max_ep=None, max_seconds=None, style="cinematic"):
    """Paint a character or moment in words, from only what's been watched.

    (The book version generated an image; the Claude API doesn't do images, so
    this renders the scene as writing instead — same spoiler boundary.)

    Returns (scene_text, passages_found). passages_found == 0 means not seen yet.
    """
    subject = subject.strip()
    allowed = chunks_through(chunks, max_ep=max_ep, max_seconds=max_seconds)
    words = [w for w in re.findall(r'[a-z]+', subject.lower()) if w not in _STOP]
    if not words:
        return None, 0
    hits = [c for c in allowed
            if all(re.search(r'\b' + re.escape(w) + r'\b', c.text.lower()) for w in words)]
    if not hits:
        return None, 0

    context = "\n\n---\n\n".join(f"[{c.label}] {c.text}" for c in hits[:6])[:16000]
    look = _STYLES.get(style, _STYLES["cinematic"])
    system = (
        "You bring a character or moment from a show or film to life in words, using "
        "ONLY the subtitle dialogue provided.\n"
        "- Everything must be grounded in those lines: what was said, who said what to "
        "whom, what the dialogue reveals. If a detail isn't supported by the lines, "
        "leave it out rather than invent it, and use no outside knowledge of this show.\n"
        "- Never include or hint at anything from beyond the provided dialogue.\n"
        f"- Render it as {look}.\n"
        "- Write 1 to 2 short, vivid paragraphs."
    )
    user = (f'Subject: "{subject}". Dialogue the viewer has seen:\n\n{context}\n\n'
            f'Paint "{subject}" for them.')
    return recap.ask(system, user, temperature=0.6), len(hits)
