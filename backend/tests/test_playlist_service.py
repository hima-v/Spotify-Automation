from app.playlists.service import _chunks, _truncate_error


def test_chunks_100():
    items = [f"spotify:track:{i}" for i in range(205)]
    chunks = list(_chunks(items, 100))
    assert [len(c) for c in chunks] == [100, 100, 5]
    assert chunks[0][0] == "spotify:track:0"
    assert chunks[-1][-1] == "spotify:track:204"


def test_truncate_error():
    msg = "x" * 2000
    out = _truncate_error(msg, limit=100)
    assert len(out) == 100
    assert out.endswith("...")

