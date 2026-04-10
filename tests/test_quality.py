from agent.quality import select_best_torrent


def test_prefers_1080p_bluray_with_good_seeds():
    torrents = [
        {"quality": "720p", "type": "web", "seeds": 50, "url": "http://a.com/720p.torrent"},
        {"quality": "1080p", "type": "bluray", "seeds": 80, "url": "http://a.com/1080p.torrent"},
        {"quality": "2160p", "type": "web", "seeds": 3, "url": "http://a.com/4k.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["quality"] == "1080p"
    assert result["type"] == "bluray"


def test_falls_back_to_highest_seeded_when_no_torrent_meets_threshold():
    torrents = [
        {"quality": "1080p", "type": "bluray", "seeds": 2, "url": "http://a.com/1080p.torrent"},
        {"quality": "720p", "type": "web", "seeds": 15, "url": "http://a.com/720p.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["seeds"] == 15


def test_returns_none_for_empty_list():
    assert select_best_torrent([]) is None


def test_prefers_2160p_over_1080p_when_both_have_good_seeds():
    torrents = [
        {"quality": "1080p", "type": "bluray", "seeds": 100, "url": "http://a.com/1080p.torrent"},
        {"quality": "2160p", "type": "bluray", "seeds": 30, "url": "http://a.com/4k.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["quality"] == "2160p"


def test_prefers_bluray_over_web_at_same_quality():
    torrents = [
        {"quality": "1080p", "type": "web", "seeds": 50, "url": "http://a.com/web.torrent"},
        {"quality": "1080p", "type": "bluray", "seeds": 30, "url": "http://a.com/bluray.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["type"] == "bluray"
