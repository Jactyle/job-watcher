import struct
from pathlib import Path

import pytest

from pipeline import logos
from pipeline.logos import DOMAINS, PNG
from pipeline.sources import SOURCES

LOGOS = Path(__file__).resolve().parent.parent / "logos"


def fake_png(side: int) -> bytes:
    """Just enough of a PNG for the tool: the signature, a length, "IHDR", then width and height."""
    return PNG + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", side, side) + b"\x08\x06\x00\x00\x00"


def fake_ico(*images: bytes) -> bytes:
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, body = b"", b""
    for image in images:
        entries += b"\x10\x10\x00\x00\x01\x00\x20\x00" + struct.pack("<II", len(image), offset + len(body))
        body += image
    return head + entries + body


# --- the files in logos/

def test_every_source_has_a_logo_domain():
    assert set(DOMAINS) == {s["name"] for s in SOURCES}


def test_every_source_has_a_png_logo_file():
    for src in SOURCES:
        assert logos._is_png((LOGOS / f"{src['name']}.png").read_bytes()), src["name"]


def test_logo_files_are_square_and_not_oversized():
    for src in SOURCES:
        data = (LOGOS / f"{src['name']}.png").read_bytes()
        width, height = struct.unpack(">II", data[16:24])
        assert width == height, f"{src['name']} is {width}x{height}"
        assert width <= 300, f"{src['name']} is {width}px, bigger than any tile needs"


# --- the download tool

def test_ico_file_gives_its_largest_png_and_ignores_other_kinds():
    assert logos._png_from_ico(fake_ico(fake_png(16), fake_png(64), fake_png(32))) == fake_png(64)
    assert logos._png_from_ico(fake_ico(b"BM" + b"\x00" * 40)) == b""   # only a bitmap inside: nothing usable
    assert logos._png_from_ico(b"not an icon") == b""


def test_a_truncated_png_is_not_accepted():
    assert not logos._is_png(PNG + b"\x00\x00")
    assert logos._is_png(fake_png(8))


def test_fetch_icon_keeps_the_largest_and_stops_once_one_is_sharp(monkeypatch):
    asked = []
    pages = {"a": fake_png(48), "b": fake_ico(fake_png(32), fake_png(200)), "c": fake_png(400), "d": b"junk"}

    def get(url):
        asked.append(url)
        if url not in pages:
            raise OSError("not found")
        return pages[url]

    monkeypatch.setattr(logos, "_icon_urls", lambda domain: iter(["x", "a", "d", "b", "c"]))
    monkeypatch.setattr(logos, "_get", get)
    assert logos.fetch_icon("example.com") == fake_png(200)   # 200 px is sharp enough, so "c" is never asked for
    assert "c" not in asked and asked[-1] == "b"


def test_fetch_icon_fails_cleanly_when_nothing_is_found(monkeypatch):
    monkeypatch.setattr(logos, "_icon_urls", lambda domain: iter(["a"]))
    monkeypatch.setattr(logos, "_get", lambda url: b"<html>no</html>")
    with pytest.raises(ValueError):
        logos.fetch_icon("example.com")


def test_only_web_addresses_are_followed():
    for url in ("file:///etc/passwd", "ftp://x/y.png", "data:image/png;base64,AAAA"):
        with pytest.raises(ValueError):
            logos._get(url)


def test_main_never_replaces_a_logo_with_a_smaller_one(monkeypatch, tmp_path):
    monkeypatch.setattr(logos, "LOGOS", tmp_path)
    (tmp_path / "stripe.png").write_bytes(fake_png(128))
    monkeypatch.setattr(logos, "fetch_icon", lambda domain: fake_png(48))
    assert logos.main(["stripe"]) == 0
    assert (tmp_path / "stripe.png").read_bytes() == fake_png(128)
    monkeypatch.setattr(logos, "fetch_icon", lambda domain: fake_png(256))
    logos.main(["stripe"])
    assert (tmp_path / "stripe.png").read_bytes() == fake_png(256)


def test_main_reports_a_failure_and_keeps_going(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(logos, "LOGOS", tmp_path)

    def fetch(domain):
        if domain == DOMAINS["stripe"]:
            raise ValueError("no icon found")
        return fake_png(64)

    monkeypatch.setattr(logos, "fetch_icon", fetch)
    assert logos.main(["stripe", "coinbase"]) == 1
    assert (tmp_path / "coinbase.png").exists() and not (tmp_path / "stripe.png").exists()
    assert "FAILED stripe" in capsys.readouterr().err
