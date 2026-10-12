import struct
import zlib

from app.icons.default_icon import NOTE_PATTERN, PLAYLIST_COLORS, render_note_png


def test_pattern_is_16_by_16() -> None:
    assert len(NOTE_PATTERN) == 16
    assert all(len(row) == 16 for row in NOTE_PATTERN)


def test_render_produces_a_16x16_rgba_png_in_the_given_colour() -> None:
    png = render_note_png(PLAYLIST_COLORS["blue"])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    width, height, depth, colour_type = struct.unpack(">IIBB", png[16:26])
    assert (width, height, depth, colour_type) == (16, 16, 8, 6)

    idat_start = png.index(b"IDAT") + 4
    idat_length = struct.unpack(">I", png[idat_start - 8 : idat_start - 4])[0]
    raw = zlib.decompress(png[idat_start : idat_start + idat_length])
    assert len(raw) == 16 * (1 + 16 * 4)

    row, col = 1, 6  # a filled pixel of the note
    assert NOTE_PATTERN[row][col] == "#"
    offset = row * (1 + 64) + 1 + col * 4
    assert raw[offset : offset + 4] == bytes((0x3B, 0x82, 0xF6, 255))
