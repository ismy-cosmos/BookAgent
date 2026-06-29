import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from pipeline.parse.image import VLMImageParser


def _make_fake_png(tmp_path) -> str:
    # Minimal 1x1 red pixel PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    p = tmp_path / "test.png"
    p.write_bytes(png_bytes)
    return str(p)


def test_image_parser_returns_one_figure_element(tmp_path):
    img = _make_fake_png(tmp_path)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "A red pixel on white background."}}

    with patch("pipeline.parse.image.httpx.post", return_value=mock_resp):
        parser = VLMImageParser(ollama_base="http://fake", model="qwen3:test")
        elems = parser.parse(img)

    assert len(elems) == 1
    assert elems[0].type == "figure"
    assert "red" in elems[0].content.lower()
    assert elems[0].page_num == 0


def test_image_parser_sends_base64(tmp_path):
    img = _make_fake_png(tmp_path)
    img_bytes = Path(img).read_bytes()
    expected_b64 = base64.b64encode(img_bytes).decode()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "A pixel."}}

    with patch("pipeline.parse.image.httpx.post", return_value=mock_resp) as mock_post:
        VLMImageParser(ollama_base="http://fake", model="m").parse(img)

    call_json = mock_post.call_args.kwargs["json"]
    images = call_json["messages"][0]["images"]
    assert images[0] == expected_b64


def test_image_parser_jpg(tmp_path):
    # JPEG magic bytes
    jpg = tmp_path / "test.jpg"
    jpg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "A JPEG."}}

    with patch("pipeline.parse.image.httpx.post", return_value=mock_resp):
        elems = VLMImageParser(ollama_base="http://fake", model="m").parse(str(jpg))

    assert elems[0].type == "figure"


def test_image_parser_jpeg(tmp_path):
    jpeg = tmp_path / "test.jpeg"
    jpeg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "A JPEG."}}

    with patch("pipeline.parse.image.httpx.post", return_value=mock_resp):
        elems = VLMImageParser(ollama_base="http://fake", model="m").parse(str(jpeg))

    assert elems[0].type == "figure"


def test_image_parser_file_not_found(tmp_path):
    with pytest.raises(ValueError, match="File not found"):
        VLMImageParser(ollama_base="http://fake", model="m").parse(str(tmp_path / "missing.png"))


def test_image_parser_bad_ollama_response(tmp_path):
    img = _make_fake_png(tmp_path)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"unexpected": "format"}  # 缺少 message.content

    with patch("pipeline.parse.image.httpx.post", return_value=mock_resp):
        with pytest.raises(ValueError, match="Unexpected Ollama response"):
            VLMImageParser(ollama_base="http://fake", model="m").parse(img)


def test_image_parser_http_error(tmp_path):
    img = _make_fake_png(tmp_path)
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 500")

    with patch("pipeline.parse.image.httpx.post", return_value=mock_resp):
        with pytest.raises(Exception, match="HTTP 500"):
            VLMImageParser(ollama_base="http://fake", model="m").parse(img)


def test_image_parser_svg_conversion_error(tmp_path):
    svg = tmp_path / "bad.svg"
    svg.write_bytes(b"not valid svg")

    with patch("pipeline.parse.image.httpx.post"):
        with patch("cairosvg.svg2png", side_effect=Exception("SVG parse error")):
            with pytest.raises(ValueError, match="SVG conversion failed"):
                VLMImageParser(ollama_base="http://fake", model="m").parse(str(svg))
