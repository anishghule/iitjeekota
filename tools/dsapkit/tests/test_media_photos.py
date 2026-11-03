import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from dsapkit.images.scrub import metadata_found, scrub
from dsapkit.media.photos import PhotoJob, PhotoProfile, check_photo, load_photo_jobs, photo_args
from dsapkit.paths import Paths
from dsapkit.site.model import load_site

PATHS = Paths.discover()
PROFILE = PhotoProfile("gallery", 1600, 3)
JOB = PhotoJob("gallery/old-batch", Path("in.jpg"), PROFILE)


def good_probe(**stream):
    s = {"codec_type": "video", "codec_name": "mjpeg", "width": 1600, "height": 1200, **stream}
    return {"streams": [s]}


class JobsTest(unittest.TestCase):
    def test_the_project_shrinks_its_large_photos_from_committed_copies(self):
        jobs = {j.slot: j for j in load_photo_jobs(PATHS)}
        self.assertEqual(set(jobs), {"gallery/old-batch", "gallery/office-chat", "gallery/mht-cet-poster"})
        for job in jobs.values():
            self.assertTrue(job.source.is_relative_to(PATHS.root / "packages/media/originals"))
            self.assertEqual(job.profile.max_edge, 1600)


class ArgumentsTest(unittest.TestCase):
    def test_the_photo_loses_every_piece_of_metadata_and_is_never_enlarged(self):
        args = photo_args("ffmpeg", JOB, Path("out.jpg"))
        self.assertEqual(args[args.index("-map_metadata") + 1], "-1")
        self.assertEqual(args[args.index("-frames:v") + 1], "1")
        self.assertEqual(args[args.index("-q:v") + 1], "3")
        scale = args[args.index("-vf") + 1]
        self.assertIn("min(1600,iw)", scale)
        self.assertIn("force_original_aspect_ratio=decrease", scale)
        self.assertEqual(args[-1], "out.jpg")


class CheckTest(unittest.TestCase):
    def test_a_right_photo_has_no_problems(self):
        self.assertEqual(check_photo(good_probe(), JOB), [])

    def test_each_way_a_photo_can_be_wrong(self):
        self.assertTrue(any("expected a JPEG" in p for p in check_photo(good_probe(codec_name="png"), JOB)))
        self.assertTrue(any("longest edge" in p for p in check_photo(good_probe(width=4160, height=3120), JOB)))
        self.assertTrue(any("metadata left" in p for p in check_photo(good_probe(tags={"comment": "x"}), JOB)))
        self.assertTrue(any("one picture" in p for p in check_photo({"streams": []}, JOB)))


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is not installed")
class FfmpegTest(unittest.TestCase):
    def test_a_large_tagged_photo_comes_out_small_upright_and_clean(self):
        with tempfile.TemporaryDirectory(prefix="dsapkit-test-") as scratch:
            source, out = Path(scratch) / "big.jpg", Path(scratch) / "out.jpg"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=3200x2400:rate=1", "-frames:v", "1", str(source)],
                           check=True)
            self.assertIn(b"Lavc", source.read_bytes())  # ffmpeg's own comment segment: the kind of thing a camera leaves too
            subprocess.run(photo_args("ffmpeg", PhotoJob("gallery/old-batch", source, PROFILE), out), check=True)
            data = out.read_bytes()
            self.assertNotIn(b"Lavc", data)
            self.assertEqual(metadata_found(scrub(data)), [])
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out)],
                                   check=True, capture_output=True, text=True).stdout.strip()
            self.assertEqual(probe, "1600,1200")


class KotaCostFactTest(unittest.TestCase):
    """The cost sum on the home page starts from the kota.cost fact, so its amounts must be usable as numbers."""

    def test_amounts_are_whole_rupees_and_the_year_of_hostel_is_the_middle_of_the_month_range_times_twelve(self):
        site = load_site(PATHS)
        cost = {}
        for name in ("coaching", "coachingHigh", "hostelMonthLow", "hostelMonthHigh", "hostelYear", "checked"):
            value, why = site.fact_value("kota.cost", name)
            self.assertIsNone(why, why)
            cost[name] = value
        for name in ("coaching", "coachingHigh", "hostelMonthLow", "hostelMonthHigh", "hostelYear"):
            self.assertRegex(cost[name], r"^\d+$")
        self.assertRegex(cost["checked"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(int(cost["hostelYear"]), 12 * (int(cost["hostelMonthLow"]) + int(cost["hostelMonthHigh"])) // 2)
        self.assertLess(int(cost["coaching"]), int(cost["coachingHigh"]))
        self.assertTrue(site.fact_value("kota.cost", "nothing")[1].startswith("unknown"))


if __name__ == "__main__":
    unittest.main()
