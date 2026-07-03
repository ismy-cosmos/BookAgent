def test_citation_fields():
    from pipeline.agent.schema import Citation
    c = Citation(chunk_id="b/f/p0001/0000", source_file="f.pdf", element_type="text",
                 citation="f.pdf p.1", score=0.12)
    assert c.chunk_id == "b/f/p0001/0000"
    assert c.source_file == "f.pdf"
    assert c.element_type == "text"
    assert c.citation == "f.pdf p.1"
    assert c.score == 0.12


def test_citation_score_can_be_none():
    from pipeline.agent.schema import Citation
    c = Citation(chunk_id="id", source_file="f.pdf", element_type="text",
                 citation="f.pdf", score=None)
    assert c.score is None


def test_chat_turn_defaults_empty_citations():
    from pipeline.agent.schema import ChatTurn
    t = ChatTurn(question="q", answer="a")
    assert t.citations == []


def test_chat_turn_holds_citations():
    from pipeline.agent.schema import ChatTurn, Citation
    c = Citation(chunk_id="id1", source_file="f.pdf", element_type="text",
                 citation="f.pdf p.1", score=0.1)
    t = ChatTurn(question="q", answer="a", citations=[c])
    assert t.citations[0].chunk_id == "id1"


def test_chat_turn_instances_do_not_share_citations_list():
    from pipeline.agent.schema import ChatTurn
    t1 = ChatTurn(question="q1", answer="a1")
    t2 = ChatTurn(question="q2", answer="a2")
    t1.citations.append("x")
    assert t2.citations == []  # default_factory 隔离每个实例的列表