import base64
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from PIL import Image as PILImage
from openai import OpenAIError

from pipeline.parse.image import VLMImageParser, _resize_to_limit, load_image_element


@pytest.fixture(autouse=True)
def mock_release_call():
    """Autouse: every parse() call hits _release_model() in a finally block.
    Mock it globally so no test makes a real network call regardless of
    which path it exercises."""
    with patch("pipeline.parse.image._release_model") as mock_release:
        yield mock_release


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


def _make_response(content):
    resp = MagicMock()
    resp.choices[0].message.content = content
    return resp


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_returns_one_figure_element(mock_openai_cls, tmp_path):
    img = _make_fake_png(tmp_path)
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_response("A red pixel on white background.")
    )

    parser = VLMImageParser(ollama_base="http://fake", model="qwen3:test")
    elems = parser.parse(img)

    assert len(elems) == 1
    assert elems[0].type == "figure"
    assert "red" in elems[0].content.lower()
    assert elems[0].page_num == 0


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_sends_base64(mock_openai_cls, tmp_path):
    img = _make_fake_png(tmp_path)
    img_bytes = Path(img).read_bytes()
    expected_b64 = base64.b64encode(img_bytes).decode()
    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_response("A pixel.")

    VLMImageParser(ollama_base="http://fake", model="m").parse(img)

    messages = mock_create.call_args.kwargs["messages"]
    image_url = messages[0]["content"][1]["image_url"]["url"]
    assert image_url == f"data:image/png;base64,{expected_b64}"


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_jpg(mock_openai_cls, tmp_path):
    jpg = tmp_path / "test.jpg"
    jpg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_response("A JPEG.")
    )

    elems = VLMImageParser(ollama_base="http://fake", model="m").parse(str(jpg))

    assert elems[0].type == "figure"


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_jpeg(mock_openai_cls, tmp_path):
    jpeg = tmp_path / "test.jpeg"
    jpeg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_response("A JPEG.")
    )

    elems = VLMImageParser(ollama_base="http://fake", model="m").parse(str(jpeg))

    assert elems[0].type == "figure"


def test_image_parser_file_not_found(tmp_path):
    with pytest.raises(ValueError, match="File not found"):
        VLMImageParser(ollama_base="http://fake", model="m").parse(str(tmp_path / "missing.png"))


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_bad_ollama_response(mock_openai_cls, tmp_path):
    img = _make_fake_png(tmp_path)
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_response(None)
    )

    with pytest.raises(ValueError, match="Unexpected Ollama response"):
        VLMImageParser(ollama_base="http://fake", model="m").parse(img)


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_http_error(mock_openai_cls, tmp_path):
    img = _make_fake_png(tmp_path)
    mock_openai_cls.return_value.chat.completions.create.side_effect = (
        OpenAIError("connection failed")
    )

    with pytest.raises(ValueError, match="Ollama vision call failed"):
        VLMImageParser(ollama_base="http://fake", model="m").parse(img)


def test_image_parser_svg_conversion_error(tmp_path):
    svg = tmp_path / "bad.svg"
    svg.write_bytes(b"not valid svg")

    with patch("cairosvg.svg2png", side_effect=Exception("SVG parse error")):
        with pytest.raises(ValueError, match="SVG conversion failed"):
            VLMImageParser(ollama_base="http://fake", model="m").parse(str(svg))


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_releases_model_after_use(mock_openai_cls, mock_release_call, tmp_path):
    img = _make_fake_png(tmp_path)
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_response("A pixel.")
    )

    VLMImageParser(ollama_base="http://fake", model="m").parse(img)

    mock_release_call.assert_called_once_with("http://fake", "m")


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_releases_model_even_on_failure(mock_openai_cls, mock_release_call, tmp_path):
    img = _make_fake_png(tmp_path)
    mock_openai_cls.return_value.chat.completions.create.side_effect = (
        OpenAIError("connection failed")
    )

    with pytest.raises(ValueError):
        VLMImageParser(ollama_base="http://fake", model="m").parse(img)

    mock_release_call.assert_called_once_with("http://fake", "m")


# ── _resize_to_limit / load_image_element ───────────────────────────────────────

def _png_bytes(w, h):
    buf = io.BytesIO()
    PILImage.new("RGB", (w, h), color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_resize_large_image_capped_to_2048_long_edge():
    out = _resize_to_limit(_png_bytes(3000, 1500))
    img = PILImage.open(io.BytesIO(out))
    assert max(img.size) == 2048
    # 长宽比保持（3000:1500 = 2:1）
    assert img.size == (2048, 1024)


def test_resize_small_image_untouched():
    original = _png_bytes(800, 600)
    assert _resize_to_limit(original) is original


def test_resize_unparseable_bytes_pass_through():
    garbage = b"\xff\xd8\xff" + b"\x00" * 10
    assert _resize_to_limit(garbage) is garbage


@patch("pipeline.parse.image.OpenAI")
def test_image_parser_parse_sends_resized_image(mock_openai_cls, tmp_path):
    big = tmp_path / "big.png"
    big.write_bytes(_png_bytes(3000, 1500))
    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_response("A big image.")

    VLMImageParser(ollama_base="http://fake", model="m").parse(str(big))

    messages = mock_create.call_args.kwargs["messages"]
    url = messages[0]["content"][1]["image_url"]["url"]
    sent = base64.b64decode(url.split("base64,")[1])
    assert max(PILImage.open(io.BytesIO(sent)).size) == 2048


def test_load_image_element_carries_bytes_no_vlm_call(tmp_path):
    img = _make_fake_png(tmp_path)
    elem = load_image_element(img)
    assert elem.type == "figure"
    assert elem.content == "![](test.png)"
    assert elem.metadata["image_bytes"] == Path(img).read_bytes()


def test_load_image_element_missing_file():
    with pytest.raises(ValueError, match="File not found"):
        load_image_element("/nonexistent/x.png")