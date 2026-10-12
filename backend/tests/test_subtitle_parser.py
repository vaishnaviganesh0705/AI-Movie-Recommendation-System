from app.rag.subtitle_parser import parse_subtitle_content, clean_subtitle_text, parse_subtitle_file


def test_clean_subtitle_text():
    dirty = "<i>COOPER:</i> Murphy! <font color='#ffff00'>Look at this.</font>\nDownloaded from opensubtitles.org"
    cleaned, speaker = clean_subtitle_text(dirty)
    assert "COOPER:" not in cleaned
    assert speaker == "COOPER"
    assert "Murphy! Look at this." in cleaned
    assert "opensubtitles" not in cleaned


def test_parse_subtitle_content_srt():
    sample_srt = """1
00:00:05,000 --> 00:00:08,500
COOPER: We used to look up at the sky.

2
00:00:09,000 --> 00:00:12,200
And wonder at our place in the stars.
"""
    entries = parse_subtitle_content(sample_srt, file_format="srt")
    assert len(entries) == 2
    assert entries[0]["sequence"] == 1
    assert entries[0]["start_seconds"] == 5.0
    assert entries[0]["end_seconds"] == 8.5
    assert entries[0]["speaker"] == "COOPER"
    assert "We used to look up at the sky." in entries[0]["text"]

    assert entries[1]["sequence"] == 2
    assert entries[1]["start_seconds"] == 9.0
    assert entries[1]["end_seconds"] == 12.2
    assert "stars." in entries[1]["text"]


def test_parse_subtitle_content_vtt():
    sample_vtt = """WEBVTT

1
00:01:10.000 --> 00:01:15.000
BRAND: Love is the one thing that transcends dimensions.
"""
    entries = parse_subtitle_content(sample_vtt, file_format="vtt")
    assert len(entries) == 1
    assert entries[0]["start_seconds"] == 70.0
    assert entries[0]["end_seconds"] == 75.0
    assert entries[0]["speaker"] == "BRAND"
