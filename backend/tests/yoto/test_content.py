from app.yoto.content import MAX_CHAPTERS, ContentTrack, build_content


def track(n: int, icon: str | None = None) -> ContentTrack:
    return ContentTrack(f"Song {n}", f"sha{n}", 100 + n, 1000 * n, "stereo", "aac", icon)


def test_one_chapter_per_track_in_given_order() -> None:
    body = build_content("Kids", [track(2), track(1)], shuffle=False)
    chapters = body["content"]["chapters"]

    assert body["title"] == "Kids"
    assert [c["key"] for c in chapters] == ["01", "02"]
    assert [c["title"] for c in chapters] == ["Song 2", "Song 1"]
    assert chapters[0]["overlayLabel"] == "1"
    audio = chapters[0]["tracks"][0]
    assert audio == {
        "key": "01",
        "title": "Song 2",
        "trackUrl": "yoto:#sha2",
        "duration": 102,
        "fileSize": 2000,
        "channels": "stereo",
        "format": "aac",
        "type": "audio",
        "overlayLabel": "1",
    }
    assert "config" not in body["content"]


def test_icons_are_set_on_chapter_and_track() -> None:
    chapter = build_content("Kids", [track(1, icon="ic1")], shuffle=False)["content"]["chapters"][0]
    assert chapter["display"] == {"icon16x16": "yoto:#ic1"}
    assert chapter["tracks"][0]["display"] == {"icon16x16": "yoto:#ic1"}


def test_shuffle_config_covers_all_chapters() -> None:
    body = build_content("Kids", [track(1), track(2), track(3)], shuffle=True)
    assert body["content"]["config"] == {"shuffle": [{"start": 0, "end": 2, "limit": 3}]}


def test_shuffle_is_omitted_for_a_single_track() -> None:
    assert "config" not in build_content("Kids", [track(1)], shuffle=True)["content"]


def test_tracks_beyond_the_yoto_limit_are_dropped() -> None:
    body = build_content("Big", [track(n) for n in range(MAX_CHAPTERS + 5)], shuffle=False)
    chapters = body["content"]["chapters"]
    assert len(chapters) == MAX_CHAPTERS
    assert chapters[-1]["key"] == "100"


def test_metadata_totals_and_cover() -> None:
    body = build_content("Kids", [track(1), track(2)], shuffle=False, cover_url="https://c/1.jpg")
    assert body["metadata"]["media"] == {"duration": 203, "fileSize": 3000, "readableFileSize": 0.0}
    assert body["metadata"]["cover"] == {"imageL": "https://c/1.jpg"}


def test_numeric_channel_count_is_sent_as_number() -> None:
    t = ContentTrack("S", "sha", 1, 1, "2", "aac")
    audio = build_content("K", [t], shuffle=False)["content"]["chapters"][0]["tracks"][0]
    assert audio["channels"] == 2
