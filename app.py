import html
from pathlib import Path

import streamlit as st

import recap                       
from chunker import load_show, chunks_through, fmt_time
from leak_test import find_leaks
from vocab import explain_term
from visualize import set_scene
from discuss import answer as discuss_answer
from show_index import build_index

SHOW = recap.SHOW
ACCENT = "#7C6CDE"   # projector violet
SEALED = "#0E1220"   # the dark of the unwatched episodes
PANEL = "#171C2E"
BONE = "#E6E4F0"
FOG = "#9A9DB3"
SAFE = "#6FAE8E"
LEAK = "#C9584D"

st.set_page_config(page_title="Previously on…", page_icon="🎬", layout="centered")


@st.cache_data(show_spinner=False)
def get_chunks(path):
    return load_show(path)


@st.cache_resource(show_spinner="Indexing the show for discussion…")
def get_index(_chunks, show_path):
    # No embedding_function → Chroma's built-in local model. Free, no key,
    # downloads once on first use.
    return build_index(_chunks, name="discuss")


def recap_up_to(chunks, max_ep=None, max_seconds=None, spot="episode ?"):
    text = "\n\n".join(f"[{c.label}] {c.text}"
                       for c in chunks_through(chunks, max_ep=max_ep, max_seconds=max_seconds))
    if len(text) > recap.MAX_CHARS:
        text = text[-recap.MAX_CHARS:]
    user = (f"Here is the dialogue for everything I've watched so far, up to {spot}:"
            f"\n\n{text}\n\n"
            "Give me a spoiler-free 'previously on' recap so I can pick up where I "
            "left off. Cover the main plot, the key characters, and where things "
            "stand right now. Keep it to a few short paragraphs.")
    return recap.ask(recap.SYSTEM, user, temperature=0.3)


def unsafe_recap(chunks):
    # No spoiler guard: let it watch all the way to the end, where the reveals live.
    whole = "\n\n".join(c.text for c in chunks)
    tail = whole[-150_000:]
    return recap.ask("Recap this show for a viewer, including how things turn out. "
                     "One short paragraph, and name the key characters involved.",
                     tail, temperature=0.3)


def badge(ok, msg):
    color = SAFE if ok else LEAK
    mark = "✓" if ok else "✗"
    st.markdown(
        f"<div style='display:inline-block;padding:.5rem .9rem;border-radius:999px;"
        f"background:{color}22;color:{color};border:1px solid {color}66;"
        f"font-weight:600;font-size:.95rem;'>{mark}&nbsp; {html.escape(msg)}</div>",
        unsafe_allow_html=True)


def boundary_bar(frac):
    pct = round(frac * 100, 1)
    st.markdown(
        f"<div style='display:flex;height:12px;border-radius:6px;overflow:hidden;"
        f"border:1px solid #2A3050;margin:.3rem 0 .35rem;'>"
        f"<div style='width:{pct}%;background:{ACCENT};'></div>"
        f"<div style='width:{100 - pct}%;background:{SEALED};'></div></div>",
        unsafe_allow_html=True)


def card(text):
    body = html.escape(text).replace("\n", "<br>")
    st.markdown(
        f"<div style='background:{PANEL};border:1px solid #2A3050;border-left:3px solid {ACCENT};"
        f"border-radius:8px;padding:1.1rem 1.3rem;line-height:1.65;color:{BONE};'>{body}</div>",
        unsafe_allow_html=True)


# ---------------- page ----------------
chunks = get_chunks(SHOW)
IS_MOVIE = Path(SHOW).is_file()
title = Path(SHOW).stem if IS_MOVIE else Path(SHOW).name

st.markdown(f"<div style='letter-spacing:.25em;color:{FOG};font-size:.8rem;'>WATCHING COMPANION</div>",
            unsafe_allow_html=True)
st.markdown("<h1 style='margin:.1rem 0 .2rem;font-size:2.7rem;'>Previously on…</h1>",
            unsafe_allow_html=True)
st.markdown(f"<p style='color:{FOG};margin-top:0;'>Everything you've watched in "
            f"<em>{html.escape(title)}</em>, and not one second more.</p>",
            unsafe_allow_html=True)

st.write("")
if IS_MOVIE:
    runtime_min = max(1, int(max(c.t_end for c in chunks) // 60) + 1)
    minute = st.slider("Where did you pause?", 1, runtime_min, min(30, runtime_min),
                       format="%d min")
    max_ep, max_seconds = None, minute * 60
    spot = f"{minute} minutes in"
    frac = minute / runtime_min
    st.markdown(f"<div style='color:{BONE};'>You've watched the first <b>{minute} minutes</b> "
                f"of about {runtime_min}.</div>", unsafe_allow_html=True)
    boundary_bar(frac)
    st.caption(f"Watched: 0:00–{fmt_time(max_seconds)}.   "
               f"Sealed: the remaining {runtime_min - minute} minutes.")
else:
    labels = []
    for c in chunks:                       # unique episode labels, in watch order
        if not labels or labels[-1] != c.label:
            labels.append(c.label)
    last = len(labels)
    pick = st.select_slider("Which episode did you just finish?", options=labels,
                            value=labels[min(2, last - 1)])
    n = labels.index(pick) + 1
    max_ep, max_seconds = n, None
    spot = f"{pick} (episode {n} of {last})"
    frac = n / last
    st.markdown(f"<div style='color:{BONE};'>You've watched through <b>{pick}</b> "
                f"— episode {n} of {last}.</div>", unsafe_allow_html=True)
    boundary_bar(frac)
    sealed = labels[n] if n < last else None
    st.caption(f"Watched: {labels[0]}–{pick}." +
               (f"   Sealed: {sealed}–{labels[-1]}." if sealed else "   Nothing sealed — you're caught up."))
current_ep_for_leaks = max_ep if max_ep is not None else 1

st.write("")
tab_recap, tab_who, tab_scene, tab_discuss = st.tabs(
    ["Catch me up", "Who? What?", "Set the scene", "Discuss"])

with tab_recap:
    if st.button("Catch me up", type="primary", key="recap_btn"):
        with st.spinner(f"Rewatching up to {spot}…"):
            text = recap_up_to(chunks, max_ep, max_seconds, spot)
        st.session_state["result"] = {"spot": spot, "text": text,
                                      "leaks": find_leaks(text, chunks, current_ep_for_leaks)
                                      if not IS_MOVIE else []}

    res = st.session_state.get("result")
    if res:
        st.write("")
        if IS_MOVIE:
            badge(True, "Spoiler-safe — the model never received anything past your pause point")
        elif res["leaks"]:
            nm, ep = res["leaks"][0]
            badge(False, f"Leak — '{nm}' first appears in episode {ep}")
        else:
            badge(True, "Spoiler-safe — checked against every later episode, nothing leaked")
        st.write("")
        card(res["text"])
        st.caption(f"Built only from what you've watched up to {res['spot']}. "
                   "The model never received the rest.")

    if not IS_MOVIE:
        st.write("")
        with st.expander("Prove the guard actually works"):
            st.write("Generate a recap that's allowed to watch ahead, then run the "
                     "same leak-check on it.")
            if st.button("Show what happens without the guard", key="guard_btn"):
                with st.spinner("Letting it watch to the end…"):
                    bad = unsafe_recap(chunks)
                bad_leaks = find_leaks(bad, chunks, current_ep_for_leaks)
                if bad_leaks:
                    nm, ep = bad_leaks[0]
                    badge(False, f"Leak caught — '{nm}' first appears in episode {ep}, "
                                 f"you're on {current_ep_for_leaks}")
                else:
                    badge(True, "No leak this time — try an earlier episode")
                st.write("")
                card(bad)

with tab_who:
    st.write("Forgot who someone is, or what that thing they keep mentioning means? "
             "Get it explained from only what you've watched, no spoilers.")
    with st.form("who_form"):
        term = st.text_input("Character, place, or term", key="who_term",
                             placeholder="e.g. the Upside Down")
        submitted = st.form_submit_button("Who / what is it?")
    if submitted and term.strip():
        with st.spinner("Checking what you've watched…"):
            explanation, found = explain_term(chunks, term, max_ep, max_seconds)
        st.session_state["who"] = {"term": term, "spot": spot,
                                   "text": explanation, "found": found}

    v = st.session_state.get("who")
    if v:
        st.write("")
        card(v["text"])
        if v["found"]:
            st.caption(f"Explained only from what you've watched up to {v['spot']} · "
                       f"found in {v['found']} scene{'s' if v['found'] != 1 else ''}.")
        else:
            st.caption(f"Checked everything up to {v['spot']}.")

with tab_scene:
    st.write("Relive a character or moment the way the show has played it so far — "
             "painted in words. Nothing from later can show up.")
    with st.form("scene_form"):
        col1, col2 = st.columns([3, 2])
        with col1:
            subject = st.text_input("Character or moment", key="scene_subject",
                                    placeholder="e.g. Eleven")
        with col2:
            style = st.selectbox("Style", ["Cinematic", "Novelistic"], key="scene_style")
        submitted = st.form_submit_button("Set the scene")
    if submitted and subject.strip():
        with st.spinner("Rewatching their scenes…"):
            try:
                text, found = set_scene(chunks, subject, max_ep, max_seconds,
                                        style.lower())
                st.session_state["scene"] = {"subject": subject, "spot": spot,
                                             "text": text, "found": found, "error": None}
            except Exception as e:
                st.session_state["scene"] = {"subject": subject, "spot": spot,
                                             "error": str(e)}

    z = st.session_state.get("scene")
    if z:
        st.write("")
        if z.get("error"):
            badge(False, "Couldn't set that scene")
            st.caption(html.escape(z["error"][:200]))
        elif not z.get("found"):
            card(f"“{z['subject']}” hasn't come up yet in what you've watched, so "
                 "there's nothing to set. Try a character or moment you've already seen.")
        else:
            card(z["text"])
            st.caption(f"Drawn only from what you've watched up to {z['spot']} · "
                       f"based on {z['found']} scene{'s' if z['found'] != 1 else ''}.")

with tab_discuss:
    st.write(f"Talk it through. Ask about characters, motives, theories. It only knows "
             f"what you've watched up to {spot}.")
    history = st.session_state.setdefault("chat", [])
    for m in history:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    q = st.chat_input("Ask about the show…")
    if q:
        history.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking…"):
                    col = get_index(chunks, SHOW)
                    a = discuss_answer(col, history[:-1], q, max_ep, max_seconds)
            except Exception as e:
                a = f"Something went wrong: {str(e)[:200]}"
            st.write(a)
        history.append({"role": "assistant", "content": a})
