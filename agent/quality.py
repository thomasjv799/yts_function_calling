QUALITY_RANK = {"2160p": 3, "1080p": 2, "720p": 1}
TYPE_RANK = {"bluray": 2, "web": 1}
SEED_THRESHOLD = 20


def select_best_torrent(torrents: list[dict]) -> dict | None:
    """Select the best torrent from a list.

    Among torrents with seeds >= 20, picks the highest quality + BluRay type.
    Falls back to the highest-seeded torrent if none meet the seed threshold.
    """
    if not torrents:
        return None

    candidates = [t for t in torrents if t.get("seeds", 0) >= SEED_THRESHOLD]

    if candidates:
        # If we have candidates with good seeds, prioritize quality and type
        def score(t: dict) -> tuple[int, int, int]:
            quality = QUALITY_RANK.get(t.get("quality", ""), 0)
            kind = TYPE_RANK.get(t.get("type", "").lower(), 0)
            seeds = t.get("seeds", 0)
            return (quality, kind, seeds)
        return max(candidates, key=score)
    else:
        # Fallback: return the highest-seeded torrent
        return max(torrents, key=lambda t: t.get("seeds", 0))
