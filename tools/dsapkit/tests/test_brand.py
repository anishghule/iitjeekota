import struct
import unittest

from dsapkit.brand.favicons import ico_container
from dsapkit.brand.og import wrap_text
from dsapkit.brand.svg import Affine, place
from dsapkit.errors import BuildError
from dsapkit.images.info import image_size, media_size, media_type
from dsapkit.images.png import Box, decode_png
from dsapkit.media.library import Slot, check_file, check_media, load_slots, waiting
from dsapkit.paths import Paths

PATHS = Paths.discover()


def width_of(text: str) -> float:
    """A stand-in font: every character is 10 px wide."""
    return len(text) * 10.0


class AffineTest(unittest.TestCase):
    def test_translate_scale_rotate(self):
        m = Affine.translate(10, 20) @ Affine.scale(2)
        self.assertEqual(m.apply(1, 1), (12, 22))
        r = Affine.rotate(90).apply(1, 0)
        self.assertAlmostEqual(r[0], 0)
        self.assertAlmostEqual(r[1], 1)

    def test_place_transforms_template_points(self):
        self.assertEqual(place("M0 0L1 1Z", Affine.translate(5, 5) @ Affine.scale(10)), "M 5 5 L 15 15 Z")

    def test_place_refuses_relative_commands(self):
        with self.assertRaises(BuildError):
            place("m0 0l1 1", Affine())


class WrapTest(unittest.TestCase):
    def test_greedy_wrap_fills_lines(self):
        self.assertEqual(wrap_text("aa bb cc dd", width_of, 50, balance=False), ["aa bb", "cc dd"])

    def test_balance_avoids_a_lonely_last_word(self):
        text = "IIT JEE coaching in Pune powered by Kota"
        greedy = wrap_text(text, width_of, 200, balance=False)
        balanced = wrap_text(text, width_of, 200, balance=True)
        self.assertEqual(len(greedy), len(balanced))
        self.assertLessEqual(max(map(width_of, balanced)) - min(map(width_of, balanced)),
                             max(map(width_of, greedy)) - min(map(width_of, greedy)))


class ImagesTest(unittest.TestCase):
    def test_square_around_a_box(self):
        self.assertEqual(Box(10, 0, 30, 40).square(), (0.0, 0.0, 40))

    def test_official_logo_is_found_and_centred(self):
        path = PATHS.root / next(s.file for s in load_slots(PATHS)[0] if s.id == "brand/logo-medal")
        pixels = decode_png(path.read_bytes())
        box = pixels.alpha_box(8)
        self.assertGreater(box.width, 900)
        self.assertLess(abs(box.width - box.height), 10)  # a round medal

    def test_image_sizes(self):
        for slot in load_slots(PATHS)[0]:
            path = PATHS.root / slot.file
            if slot.origin == "supplied" and path.exists():
                width, height = image_size(path.read_bytes())
                self.assertGreater(width * height, 0)


class IcoTest(unittest.TestCase):
    def test_header_and_directory(self):
        data = ico_container([(16, b"a" * 5), (32, b"b" * 7)])
        self.assertEqual(struct.unpack("<HHH", data[:6]), (0, 1, 2))
        first = struct.unpack("<BBBBHHII", data[6:22])
        self.assertEqual((first[0], first[6], first[7]), (16, 5, 6 + 32))


def box(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(body), kind) + body


def mp4(width: int, height: int, quarter_turn: bool = False) -> bytes:
    """A minimal MP4 header: ftyp, then moov > trak > tkhd (version 0) with a display matrix."""
    one, zero, w_one = 0x10000, 0, 0x40000000
    matrix = (zero, one, zero, -one, zero, zero, zero, zero, w_one) if quarter_turn else (one, zero, zero, zero, one, zero, zero, zero, w_one)
    tkhd = bytes(40) + struct.pack(">9i", *matrix) + struct.pack(">II", width << 16, height << 16)
    return box(b"ftyp", b"isom" + bytes(4)) + box(b"moov", box(b"trak", box(b"tkhd", tkhd)))


def slot(**spec) -> Slot:
    return Slot("test/slot", "awaited", "video", "packages/media/assets/test.mp4", "", {"en": "x"}, False, False, "", spec=spec)


class Mp4Test(unittest.TestCase):
    def test_landscape_size(self):
        self.assertEqual(media_type(mp4(1920, 1080)), "video/mp4")
        self.assertEqual(media_size(mp4(1920, 1080)), (1920, 1080))

    def test_phone_video_turned_upright(self):
        self.assertEqual(media_size(mp4(1920, 1080, quarter_turn=True)), (1080, 1920))


class MediaTest(unittest.TestCase):
    LIMITS = {"image": 12_000_000, "video": 80_000_000}

    def test_supplied_media_matches_the_lock(self):
        slots = check_media(PATHS, require_generated=False)
        self.assertTrue(any(s.id == "brand/logo-medal" and not s.placeholder for s in slots))

    def test_missing_awaited_files_are_waiting_not_errors(self):
        slots = check_media(PATHS, require_generated=False)
        waiting_ids = {s.id for s in waiting(PATHS, slots)}
        self.assertTrue(all(s.origin == "awaited" for s in slots if s.id in waiting_ids))

    def test_spec_checks_orientation_size_and_kind(self):
        upright = slot(orientation="portrait", minWidth=1080, minHeight=1920)
        self.assertEqual(check_file(upright, mp4(1920, 1080, quarter_turn=True), self.LIMITS), [])
        problems = check_file(upright, mp4(1010, 432), self.LIMITS)
        self.assertTrue(any("smaller than" in p for p in problems))
        self.assertTrue(any("should be portrait" in p for p in problems))
        photo = (PATHS.root / "packages/media/assets/brand/dsap-medal.png").read_bytes()
        self.assertTrue(any("expected video" in p for p in check_file(upright, photo, self.LIMITS)))


if __name__ == "__main__":
    unittest.main()
