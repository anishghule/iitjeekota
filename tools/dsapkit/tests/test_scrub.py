import struct
import unittest
import zlib

from dsapkit.errors import BuildError
from dsapkit.images.scrub import metadata_found, mp4_metadata_found, scrub
from dsapkit.paths import Paths

PATHS = Paths.discover()
ASSETS = PATHS.media_assets


def segment(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def exif(orientation: int | None = None, gps: bool = True) -> bytes:
    """An EXIF block (little endian) with an optional orientation and a pointer to GPS data."""
    entries = []
    if orientation is not None:
        entries.append(struct.pack("<HHIHH", 0x0112, 3, 1, orientation, 0))
    if gps:
        entries.append(struct.pack("<HHII", 0x8825, 4, 1, 100))  # a pointer to the GPS block
    tiff = b"II*\0" + struct.pack("<I", 8) + struct.pack("<H", len(entries)) + b"".join(entries) + struct.pack("<I", 0)
    return b"Exif\0\0" + tiff + b"GPSLatitude 18.58 GPSLongitude 73.81 Pune"


PICTURE = segment(0xDB, b"\0" + bytes(64)) + segment(0xC0, b"\x08\0\x10\0\x10\x01\x01\x11\0") + segment(0xC4, b"\0" + bytes(28)) \
    + segment(0xDA, b"\x01\x01\0\0\x3f\0") + b"\x12\xff\x00\x34\xff\xd0\x56\xff\x00\xff\xd1\x78"
JFIF = b"JFIF\0\x01\x01\0\0\x01\0\x01\0\0"
JFIF_WITH_THUMB = b"JFIF\0\x01\x01\0\0\x01\0\x01\x02\x01" + bytes(6)


def jpeg(*before: bytes, after: bytes = b"") -> bytes:
    return b"\xff\xd8" + b"".join(before) + PICTURE + b"\xff\xd9" + after


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(*extra: bytes, tail: bytes = b"") -> bytes:
    ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
    idat = png_chunk(b"IDAT", zlib.compress(b"\0" + bytes(6) + b"\0" + bytes(6)))
    return b"\x89PNG\r\n\x1a\n" + ihdr + b"".join(extra) + idat + png_chunk(b"IEND", b"") + tail


def webp(*extra: bytes, flags: int = 0) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return kind + struct.pack("<I", len(data)) + data + (b"\0" if len(data) & 1 else b"")
    vp8x = chunk(b"VP8X", bytes([flags]) + bytes(3) + struct.pack("<I", 1)[:3] + struct.pack("<I", 1)[:3])
    body = b"WEBP" + vp8x + b"".join(chunk(k, d) for k, d in extra) + chunk(b"VP8 ", bytes(10))
    return b"RIFF" + struct.pack("<I", len(body)) + body


class JpegTest(unittest.TestCase):
    def test_location_time_phone_comment_thumbnail_and_trailing_data_all_go(self):
        dirty = jpeg(segment(0xE0, JFIF_WITH_THUMB), segment(0xE1, exif()), segment(0xE1, b"http://ns.adobe.com/xap/1.0/\0<x:xmpmeta/>"),
                     segment(0xED, b"Photoshop 3.0\0IPTC"), segment(0xFE, b"taken with my phone"), after=b"\xff\xd8secondcopy\xff\xd9")
        self.assertEqual(metadata_found(dirty), ["EXIF", "IPTC", "XMP", "comment", "data after the end of the picture", "thumbnail"])
        clean = scrub(dirty)
        self.assertEqual(metadata_found(clean), [])
        for secret in (b"GPS", b"Pune", b"xmpmeta", b"IPTC", b"phone", b"secondcopy"):
            self.assertNotIn(secret, clean)

    def test_the_picture_itself_is_not_touched(self):
        clean = scrub(jpeg(segment(0xE1, exif())))
        self.assertTrue(clean.endswith(PICTURE + b"\xff\xd9"))
        self.assertIn(b"\xff\x00", clean)  # byte stuffing in the picture data survives
        self.assertIn(b"\xff\xd0", clean)  # so do restart markers

    def test_scrubbing_is_repeatable_and_a_clean_file_is_unchanged(self):
        once = scrub(jpeg(segment(0xE0, JFIF), segment(0xE1, exif())))
        self.assertEqual(scrub(once), once)
        self.assertEqual(scrub(jpeg(segment(0xE0, JFIF))), jpeg(segment(0xE0, JFIF)))

    def test_the_colour_profile_stays_only_when_asked(self):
        profile = segment(0xE2, b"ICC_PROFILE\0\x01\x01" + bytes(20))
        self.assertIn(b"ICC_PROFILE", scrub(jpeg(profile)))
        self.assertNotIn(b"ICC_PROFILE", scrub(jpeg(profile), keep_profile=False))
        self.assertEqual(metadata_found(jpeg(profile)), [])
        self.assertEqual(metadata_found(jpeg(profile), keep_profile=False), ["colour profile"])

    def test_a_photo_that_is_upright_only_by_its_tag_is_refused_not_turned_sideways(self):
        for turn in (3, 6, 8):
            with self.assertRaises(BuildError) as raised:
                scrub(jpeg(segment(0xE1, exif(orientation=turn))))
            self.assertIn("Rotate it upright", str(raised.exception))
        self.assertTrue(scrub(jpeg(segment(0xE1, exif(orientation=1)))))

    def test_a_broken_file_is_an_error(self):
        with self.assertRaises(BuildError):
            scrub(b"\xff\xd8\xff\xe1\x00\x10short")
        with self.assertRaises(BuildError):
            scrub(b"\xff\xd8" + PICTURE)  # no end marker


class PngTest(unittest.TestCase):
    def test_text_time_exif_and_trailing_data_all_go(self):
        dirty = png(png_chunk(b"tEXt", b"Location\0Pune"), png_chunk(b"tIME", bytes(7)), png_chunk(b"eXIf", exif(gps=True)[6:]),
                    png_chunk(b"pHYs", bytes(9)), png_chunk(b"iTXt", b"XML:com.adobe.xmp\0\0\0\0\0<x/>"), tail=b"extra bytes after the end")
        self.assertEqual(metadata_found(dirty), ["data after the end of the picture", "eXIf", "iTXt", "pHYs", "tEXt", "tIME"])
        clean = scrub(dirty)
        self.assertEqual(metadata_found(clean), [])
        self.assertEqual(clean, png())
        self.assertNotIn(b"Pune", clean)

    def test_colour_chunks_stay(self):
        keep = png_chunk(b"gAMA", bytes(4)) + png_chunk(b"sRGB", b"\0")
        self.assertEqual(scrub(png(keep)), png(keep))

    def test_a_sideways_png_is_refused(self):
        with self.assertRaises(BuildError):
            scrub(png(png_chunk(b"eXIf", exif(orientation=6, gps=False)[6:])))


class WebpTest(unittest.TestCase):
    def test_exif_and_xmp_go_and_the_header_flags_follow(self):
        dirty = webp((b"EXIF", exif()), (b"XMP ", b"<x:xmpmeta/>"), flags=0x08 | 0x04 | 0x10)
        self.assertEqual(metadata_found(dirty), ["EXIF", "XMP"])
        clean = scrub(dirty)
        self.assertEqual(metadata_found(clean), [])
        self.assertEqual(clean, webp(flags=0x10))  # the alpha flag stays; the EXIF and XMP flags are cleared
        self.assertEqual(struct.unpack("<I", clean[4:8])[0], len(clean) - 8)
        self.assertNotIn(b"GPS", clean)

    def test_a_sideways_webp_is_refused(self):
        with self.assertRaises(BuildError):
            scrub(webp((b"EXIF", exif(orientation=6, gps=False)), flags=0x08))


class Mp4Test(unittest.TestCase):
    @staticmethod
    def box(kind: bytes, payload: bytes = b"") -> bytes:
        return struct.pack(">I", len(payload) + 8) + kind + payload

    def mp4(self, *moov_children: bytes, created: int = 0) -> bytes:
        mvhd = self.box(b"mvhd", bytes([0]) + bytes(3) + struct.pack(">II", created, created) + bytes(88))
        return self.box(b"ftyp", b"isom\0\0\2\0isom") + self.box(b"moov", mvhd + b"".join(moov_children)) + self.box(b"mdat", bytes(8))

    def test_a_film_with_nothing_hidden_is_clean(self):
        self.assertEqual(mp4_metadata_found(self.mp4()), [])
        empty_shell = self.box(b"udta", self.box(b"meta", bytes(4) + self.box(b"hdlr", bytes(21)) + self.box(b"ilst")))
        self.assertEqual(mp4_metadata_found(self.mp4(empty_shell)), [])

    def test_where_when_and_tags_are_found(self):
        location = self.box(b"udta", self.box(b"\xa9xyz", b"\0\x04\0\0+18.5810+073.8171/"))
        self.assertEqual(mp4_metadata_found(self.mp4(location)), ["location", "user data"])
        tags = self.box(b"udta", self.box(b"meta", bytes(4) + self.box(b"hdlr", bytes(21)) + self.box(b"ilst", self.box(b"\xa9too", b"Lavf"))))
        self.assertEqual(mp4_metadata_found(self.mp4(tags)), ["metadata", "user data"])
        self.assertEqual(mp4_metadata_found(self.mp4(created=3_700_000_000)), ["creation or modification time"])

    def test_a_hidden_extension_box_is_found(self):
        self.assertEqual(mp4_metadata_found(self.mp4() + self.box(b"uuid", bytes(16) + b"<x:xmpmeta/>")), ["extension data (often XMP)"])


class ShippedFilesTest(unittest.TestCase):
    """The files the project really ships, read as shipped."""

    def test_every_pinned_media_file_is_clean(self):
        files = [f for f in sorted(ASSETS.rglob("*")) if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4"}]
        self.assertTrue(files)
        for file in files:
            self.assertEqual(metadata_found(file.read_bytes()), [], file.name)

    def test_a_real_photo_with_location_added_comes_back_byte_for_byte_as_shipped(self):
        poster = ASSETS / "home" / "classroom-film-poster.jpg"
        if not poster.exists():
            self.skipTest("run make media-encode")
        shipped = poster.read_bytes()
        dirty = shipped[:2] + segment(0xE1, exif()) + segment(0xFE, b"IMG_0001 Pune") + shipped[2:]
        self.assertNotEqual(metadata_found(dirty), [])
        self.assertEqual(scrub(dirty), shipped)


if __name__ == "__main__":
    unittest.main()
