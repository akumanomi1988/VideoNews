from scripts.MediaManagers.SRT_Processor import SRTProcessor


def test_long_pause_splits_cues_even_when_tts_word_has_no_punctuation():
    processor = SRTProcessor("unused.srt", pause_threshold=0.3)
    words = [
        {"index": 1, "start": 10.0, "end": 10.3, "text": "despidos"},
        {"index": 2, "start": 11.2, "end": 11.6, "text": "Algunos"},
    ]

    groups = processor.group_subtitles(words)

    assert [[word["text"] for word in group] for group in groups] == [
        ["despidos"], ["Algunos"]]


def test_short_pause_can_keep_words_in_one_caption():
    processor = SRTProcessor("unused.srt", pause_threshold=0.3)
    words = [
        {"index": 1, "start": 1.0, "end": 1.2, "text": "La"},
        {"index": 2, "start": 1.35, "end": 1.6, "text": "noticia"},
    ]

    groups = processor.group_subtitles(words)

    assert [[word["text"] for word in group] for group in groups] == [["La", "noticia"]]
