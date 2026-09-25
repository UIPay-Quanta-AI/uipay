import io

import pytest
from PIL import Image

from app.providers.ocr.base import OCRInputError
from app.providers.ocr.image import ValidatedImage, validate_image


def _create_test_image(
    fmt: str = "PNG", size: tuple[int, int] = (100, 100), color: str = "red"
) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_validate_image_empty_bytes():
    with pytest.raises(OCRInputError, match="Image input is empty"):
        validate_image(b"")


def test_validate_image_corrupt_bytes():
    with pytest.raises(OCRInputError, match="not recognised or supported"):
        validate_image(b"not an image data string")


def test_validate_image_exceeds_max_bytes():
    data = _create_test_image("PNG")
    with pytest.raises(OCRInputError, match="exceeds the configured limit"):
        validate_image(data, max_bytes=10)


def test_validate_image_exceeds_max_pixels():
    data = _create_test_image("PNG", size=(200, 200))
    with pytest.raises(OCRInputError, match="exceeds the configured limit"):
        validate_image(data, max_pixels=1000)  # 200*200 = 40,000 > 1,000


def test_validate_image_unsupported_format():
    data = _create_test_image("BMP")
    with pytest.raises(OCRInputError, match="Image format 'BMP' is not supported"):
        validate_image(data)


def test_validate_image_valid_png():
    data = _create_test_image("PNG", size=(120, 80))
    val = validate_image(data)

    assert isinstance(val, ValidatedImage)
    assert val.data == data
    assert val.width == 120
    assert val.height == 80
    assert val.format == "PNG"
    assert val.mode == "RGB"
    assert val.pixel_count == 120 * 80


def test_validate_image_valid_jpeg():
    data = _create_test_image("JPEG", size=(50, 50))
    val = validate_image(data)

    assert val.format == "JPEG"
    assert val.width == 50
    assert val.height == 50


def test_validate_image_valid_webp():
    data = _create_test_image("WEBP", size=(60, 40))
    val = validate_image(data)

    assert val.format == "WEBP"
    assert val.width == 60
    assert val.height == 40
