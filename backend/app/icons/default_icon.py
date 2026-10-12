import struct
import zlib

PLAYLIST_COLORS: dict[str, str] = {
    "orange": "#F26B3A",
    "yellow": "#F5B82E",
    "blue": "#3B82F6",
    "green": "#22A06B",
    "pink": "#EC4899",
    "purple": "#8B5CF6",
    "red": "#E5484D",
    "teal": "#14B8A6",
}

# Beamed eighth notes, '#' = filled pixel.
NOTE_PATTERN: tuple[str, ...] = (
    "................",
    "......########..",
    "......########..",
    "......#......#..",
    "......#......#..",
    "......#......#..",
    "......#......#..",
    "......#......#..",
    "......#......#..",
    "...####...####..",
    "..#####..#####..",
    "..#####..#####..",
    "...###....###...",
    "................",
    "................",
    "................",
)


def render_note_png(hex_color: str) -> bytes:
    """Render the music-note icon as a 16x16 RGBA PNG in the given colour."""
    red, green, blue = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    filled = bytes((red, green, blue, 255))
    empty = bytes(4)
    raw = b"".join(
        b"\x00" + b"".join(filled if pixel == "#" else empty for pixel in row)
        for row in NOTE_PATTERN
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", 16, 16, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
