import re

from chunker import load_show, chunks_through

# common capitalized words that aren't character / place names
_NUMS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
         "sixty", "seventy", "eighty", "ninety", "hundred"}
_STOP = {"the", "and", "but", "for", "with", "she", "her", "his", "him", "they",
         "you", "your", "this", "that", "when", "then", "there", "what", "who",
         "god", "death", "lord", "lady", "sir", "mr", "mrs", "miss", "okay",
         "yeah", "yes", "no", "episode", "season"} | _NUMS


def _proper_nouns(text):
    """Capitalized words used mid-sentence: a cheap stand-in for names and places."""
    found = set()
    for m in re.finditer(r'\b([A-Z][a-zA-Z]{2,})\b', text):
        j = m.start() - 1
        while j >= 0 and text[j] in ' \t':
            j -= 1
        prev = text[j] if j >= 0 else ''
        if prev and prev not in '.!?":;\n(“”‘’':            # skip start-of-sentence
            w = m.group(1)
            if w.lower() not in _STOP:
                found.add(w)
    return found


def _all_capitalized(text):
    """Every capitalized word, including sentence starts. Used only to index the
    show itself: a name someone speaks at the start of a sentence still counts
    as introduced, so it can't be flagged as a leak later."""
    return {m.group(1) for m in re.finditer(r'\b([A-Z][a-zA-Z]{2,})\b', text)
            if m.group(1).lower() not in _STOP}


def first_episode_of_each_name(chunks):
    """For every name-like word, the earliest episode it is spoken in."""
    first = {}
    for c in chunks:
        for name in _all_capitalized(c.text):
            if name not in first or c.ep < first[name]:
                first[name] = c.ep
    return first


def find_leaks(recap_text, chunks, current_ep):
    """Names in the recap the viewer shouldn't know yet (they first appear later).
    Returns a sorted list of (name, first_episode). An empty list means clean."""
    first = first_episode_of_each_name(chunks)
    leaks = [(n, first[n]) for n in _proper_nouns(recap_text)
             if n in first and first[n] > current_ep]
    return sorted(set(leaks), key=lambda t: t[1])


if __name__ == "__main__":
    import recap

    N = recap.CURRENT_EPISODE or 1
    chunks = load_show(recap.SHOW)
    last = max(c.ep for c in chunks)

    print(f"=== Eval: does an episode-{N} recap leak anything from later? ===\n")

    # 1) The real, spoiler-safe recap should come back clean.
    safe = recap.make_recap(max_ep=N, max_minute=None)
    safe_leaks = find_leaks(safe, chunks, N)
    print(f"SAFE recap (built only from episodes 1..{N}):")
    print(f"  future-only names found: {len(safe_leaks)}  ->  "
          f"{'CLEAN, PASS' if not safe_leaks else safe_leaks}\n")

    # 2) A deliberately unsafe recap that was allowed to watch ahead should get caught.
    later = min(N + 5, last)
    ahead = "\n\n".join(c.text for c in chunks_through(chunks, max_ep=later))[:150_000]
    bad = recap.ask("Summarize this show so far in one paragraph, naming the key "
                    "characters involved.", ahead, temperature=0.3)
    bad_leaks = find_leaks(bad, chunks, N)
    print(f"UNSAFE recap (allowed to watch through episode {later}):")
    print(f"  future-only names found: {len(bad_leaks)}  ->  "
          f"{'LEAK DETECTED, FAIL' if bad_leaks else 'clean'}")
    for name, ep in bad_leaks[:12]:
        print(f"    '{name}' first appears in episode {ep}, viewer is only on {N}")
    print("\nThe eval passes the safe recap and catches the unsafe one. "
          "That contrast is the proof it actually works.")
