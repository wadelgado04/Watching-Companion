import chromadb

from chunker import Chunk


def build_index(chunks: list[Chunk], name: str = "show",
                persist_dir: str = "./chroma", embedding_function=None):
    """Load chunks into a fresh Chroma collection, keyed by position metadata.

    Leave embedding_function as None to use Chroma's built-in local model
    (downloads once on first run — no API key needed, which matters here
    because the Claude API doesn't do embeddings).
    """
    client = chromadb.PersistentClient(path=persist_dir)
    try:                                   # start clean so re-running won't duplicate
        client.delete_collection(name)
    except Exception:
        pass

    kwargs = {"name": name}
    if embedding_function is not None:
        kwargs["embedding_function"] = embedding_function
    col = client.create_collection(**kwargs)

    col.add(
        ids=[str(c.id) for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[{
            "ep": c.ep,
            "label": c.label,
            "t_start": c.t_start,
            "t_end": c.t_end,
            "order": c.id,
        } for c in chunks],
    )
    return col


def _boundary(max_ep=None, max_seconds=None):
    """Build the Chroma metadata filter that enforces the spoiler line."""
    conds = []
    if max_ep is not None:
        conds.append({"ep": {"$lte": max_ep}})
    if max_seconds is not None:
        conds.append({"t_end": {"$lte": max_seconds}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def all_through(col, max_ep=None, max_seconds=None) -> list[dict]:
    """Every chunk up to the viewer's spot, back in watch order. Feeds the recap."""
    res = col.get(where=_boundary(max_ep, max_seconds))
    rows = [{"text": d, "ep": m["ep"], "label": m["label"],
             "t_start": m["t_start"], "order": m["order"]}
            for d, m in zip(res["documents"], res["metadatas"])]
    rows.sort(key=lambda r: r["order"])
    return rows


def search_through(col, query: str, max_ep=None, max_seconds=None,
                   k: int = 5) -> list[dict]:
    """Top-k chunks relevant to `query`, but only from what the viewer has watched.
    Feeds who/what-is and the discussion feature."""
    res = col.query(query_texts=[query],
                    where=_boundary(max_ep, max_seconds),
                    n_results=k)
    return [{"text": d, "ep": m["ep"], "label": m["label"], "t_start": m["t_start"]}
            for d, m in zip(res["documents"][0], res["metadatas"][0])]
