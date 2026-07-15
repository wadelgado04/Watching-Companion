import recap
from show_index import search_through

SYSTEM = (
    "You are a thoughtful watch-party partner discussing a show or film with a viewer. "
    "You may use ONLY the subtitle passages provided and what the viewer has watched up "
    "to their current spot. Rules:\n"
    "- Ground what you say in the provided passages. Do not use any outside knowledge "
    "of this show, its plot, or its cast.\n"
    "- Never reveal, confirm, or hint at anything that happens after the viewer's "
    "current spot. If a question needs later information, say it hasn't happened yet in "
    "their watching and you can't say without spoiling.\n"
    "- You can analyze characters, motives, relationships, and themes, and you can "
    "theorize, but frame any theory as an open question, never as a known outcome.\n"
    "- Be conversational and concise."
)


def answer(col, history, question, max_ep=None, max_seconds=None, k=8):
    """history is the prior [{'role','content'}, ...] turns (without this question)."""
    passages = search_through(col, question, max_ep=max_ep,
                              max_seconds=max_seconds, k=k)
    context = ("\n\n---\n\n".join(f"[{p['label']}] {p['text']}" for p in passages)
               if passages else "(no passages found)")
    spot = (f"episode {max_ep}" if max_ep is not None else "partway into the film")
    system = (SYSTEM + f"\n\nThe viewer has watched through {spot}. Relevant dialogue "
              f"from what they have seen:\n\n{context}")
    messages = history + [{"role": "user", "content": question}]
    return recap.ask(system, messages, temperature=0.5)
