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


# ── issue #56: 说话人切换内联标签 ────────────────────────────────────────────

def _seg_spk(text, start, end, speaker, score=1.0):
    return {"text": text, "start": start, "end": end, "score": score, "speaker": speaker}


def test_speaker_tag_inserted_on_first_segment():
    segments = [_seg_spk("Hello.", 0.0, 2.0, "SPEAKER_00")]
    chunks = pack_audio_segments(segments, book_id="b", source_file="hearing.mp3")
    assert chunks[0].content == "[SPEAKER_00] Hello."


def test_speaker_tag_not_repeated_for_same_speaker_consecutive_segments():
    segments = [
        _seg_spk("First sentence.", 0.0, 2.0, "SPEAKER_00"),
        _seg_spk("Second sentence.", 2.0, 4.0, "SPEAKER_00"),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="hearing.mp3")
    assert chunks[0].content == "[SPEAKER_00] First sentence. Second sentence."


def test_speaker_tag_inserted_on_speaker_change():
    segments = [
        _seg_spk("Question.", 0.0, 2.0, "SPEAKER_00"),
        _seg_spk("Answer.", 2.0, 4.0, "SPEAKER_01"),
        _seg_spk("Follow-up.", 4.0, 6.0, "SPEAKER_00"),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="hearing.mp3")
    assert chunks[0].content == "[SPEAKER_00] Question. [SPEAKER_01] Answer. [SPEAKER_00] Follow-up."


def test_no_speaker_info_produces_no_tags_default_behavior_unchanged():
    segments = [
        _seg("First.", 0.0, 2.0),
        _seg("Second.", 2.0, 4.0),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="lecture.mp3")
    assert "[SPEAKER" not in chunks[0].content
    assert chunks[0].content == "First. Second."


def test_speaker_tag_reappears_at_start_of_new_chunk_even_if_same_speaker_continues():
    """跨chunk边界的关键情况：说话人A被token预算切到两个chunk，
    第二个chunk开头即使还是A也要重新打标签——每个chunk独立被检索，
    不能依赖上一个chunk的隐式上下文。"""
    long_text_a1 = "Speaker A talking at length about the case. " * 15
    long_text_a2 = "Speaker A continues the same point without interruption. " * 15
    segments = [
        _seg_spk(long_text_a1, 0.0, 30.0, "SPEAKER_00"),
        _seg_spk(long_text_a2, 30.0, 60.0, "SPEAKER_00"),
    ]
    chunks = pack_audio_segments(segments, book_id="b", source_file="hearing.mp3", max_tokens=256)
    assert len(chunks) == 2
    assert chunks[0].content.startswith("[SPEAKER_00] ")
    assert chunks[1].content.startswith("[SPEAKER_00] ")
