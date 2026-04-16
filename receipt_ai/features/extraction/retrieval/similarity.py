from __future__ import annotations

import math


def l2_norm(vector: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vector))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = l2_norm(a)
    nb = l2_norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def top_k_by_score(
    items: list[tuple[float, int]],
    k: int,
) -> list[tuple[float, int]]:
    if k <= 0:
        return []
    scored = sorted(items, key=lambda t: t[0], reverse=True)
    return scored[:k]
