from pipeline.chunk import Chunk

def test_chunk_defaults():
    c = Chunk(
        chunk_id="ostep/ch01/p0001/0000",
        book_id="ostep",
        source_file="ch01.pdf",
        element_type="text",
        content="Hello world.",
        token_count=2,
    )
    assert c.page_start is None
    assert c.start_sec is None
    assert c.end_sec is None

def test_chunk_audio_fields():
    c = Chunk(
        chunk_id="ostep/segment-01/0000",
        book_id="ostep",
        source_file="segment-01.mp3",
        element_type="audio",
        content="There are 340 processes.",
        token_count=6,
        start_sec=74.0,
        end_sec=101.0,
    )
    assert c.start_sec == 74.0
    assert c.page_start is None

def test_chunk_to_dict_round_trip():
    import dataclasses
    c = Chunk(
        chunk_id="b/f/p0001/0000",
        book_id="b",
        source_file="f.pdf",
        element_type="text",
        content="x",
        token_count=1,
        page_start=1,
    )
    d = dataclasses.asdict(c)
    assert d["page_start"] == 1
    assert d["start_sec"] is None
