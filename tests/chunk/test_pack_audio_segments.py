from pipeline.chunk.chunker import pack_audio_segments, _token_count


def _seg(text, start, end, score=1.0):
    return {"text": text, "start": start, "end": end, "score": score}


def test_small_segments_merge_into_one_chunk():
    segments = [
        _seg("Hello there.", 0.0, 2.0),
        _seg("This is a test.", 2.0, 4.0),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert len(chunks) == 1
    assert "Hello there." in chunks[0].content
    assert "This is a test." in chunks[0].content


def test_token_limit_triggers_new_chunk():
    long_text = "This is a segment about operating systems. " * 20  # 远超128 token
    segments = [
        _seg(long_text, 0.0, 30.0),
        _seg(long_text, 30.0, 60.0),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3", max_tokens=256)
    assert len(chunks) == 2


def test_start_end_sec_span_first_and_last_segment():
    segments = [
        _seg("First.", 10.0, 12.0),
        _seg("Second.", 12.0, 15.0),
        _seg("Third.", 15.0, 20.0),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert len(chunks) == 1
    assert chunks[0].start_sec == 10.0
    assert chunks[0].end_sec == 20.0


def test_chunk_id_format_sequential():
    long_text = "This is a segment about operating systems. " * 20
    segments = [_seg(long_text, 0.0, 30.0), _seg(long_text, 30.0, 60.0)]
    chunks = pack_audio_segments(segments, book_id="mybook", source_file="lecture.mp3", max_tokens=256)
    assert chunks[0].chunk_id == "mybook/lecture.mp3/0000"
    assert chunks[1].chunk_id == "mybook/lecture.mp3/0001"


def test_low_confidence_weighted_average_below_threshold():
    segments = [
        _seg("word word word word.", 0.0, 2.0, score=0.3),
        _seg("word word word word.", 2.0, 4.0, score=0.4),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert len(chunks) == 1
    assert chunks[0].low_confidence is True


def test_low_confidence_weighted_average_above_threshold():
    segments = [
        _seg("word word word word.", 0.0, 2.0, score=0.9),
        _seg("word word word word.", 2.0, 4.0, score=0.95),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert len(chunks) == 1
    assert chunks[0].low_confidence is False


def test_blank_text_segments_skipped():
    segments = [
        _seg("Hello.", 0.0, 2.0),
        _seg("   ", 2.0, 3.0),
        _seg("World.", 3.0, 5.0),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert len(chunks) == 1
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 5.0
    assert "Hello" in chunks[0].content
    assert "World" in chunks[0].content


def test_empty_segments_list_returns_empty():
    assert pack_audio_segments([], book_id="b", source_file="lecture.mp3") == []


def test_page_start_and_end_are_none():
    chunks = pack_audio_segments([_seg("Hi.", 0.0, 1.0)], book_id="b", source_file="lecture.mp3")
    assert chunks[0].page_start is None
    assert chunks[0].page_end is None


def test_element_type_is_audio():
    chunks = pack_audio_segments([_seg("Hi.", 0.0, 1.0)], book_id="b", source_file="lecture.mp3")
    assert chunks[0].element_type == "audio"


def test_token_count_reflects_joined_content_not_sum():
    segments = [_seg("Hello there.", 0.0, 2.0), _seg("This is a test.", 2.0, 4.0)]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert chunks[0].token_count == _token_count("Hello there. This is a test.")


def test_low_confidence_weighted_by_token_count_not_simple_average():
    # 简单算术平均 (0.9+0.2)/2=0.55 < 0.6 会误判整个chunk为低置信度；
    # 按token数加权平均后，长的高分segment应该主导结果，> 0.6
    long_high = "This is a long segment about operating systems that is clear. " * 5
    short_low = "uh."
    segments = [
        _seg(long_high, 0.0, 20.0, score=0.9),
        _seg(short_low, 20.0, 21.0, score=0.2),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert len(chunks) == 1
    assert chunks[0].low_confidence is False
