import json
import shutil
import unittest
from dataclasses import replace
from pathlib import Path

from dsapkit.errors import BuildError
from dsapkit.media.encode import Job, Profile, check_output, keyframe_args, load_jobs, longest_gap, poster_args, probe_args, video_args
from dsapkit.paths import Paths

PATHS = Paths.discover()


def project_profile(name: str) -> Profile:
    p = json.loads(PATHS.media_encode.read_text())["profiles"][name]
    return Profile(name, p["maxWidth"], p["fps"], p["crf"], p["preset"], p["gop"], p["posterQuality"], frozenset(p["allowedTags"]))


# The classroom film's job as it was made. The originals are 173 MB, outside the repository, so no job is kept in encode.json.
JOB = Job("home/classroom-film", Path("/work/film.mp4"), project_profile("clip"), 1.0, 14.0, "home/classroom-film-poster", 5.0)


def good_probe(**stream):
    s = {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 1080, "height": 2522, "r_frame_rate": "30/1",
         "tags": {"language": "und", "handler_name": "VideoHandler"}, **stream}
    return {"streams": [s], "format": {"duration": "14.033", "tags": {"major_brand": "isom", "minor_version": "512"}}}


class JobsTest(unittest.TestCase):
    def test_the_profiles_the_films_were_made_with_are_kept(self):
        self.assertEqual((JOB.profile.max_width, JOB.profile.fps, JOB.profile.gop), (1080, 30, 60))
        self.assertEqual(project_profile("clip-wide").max_width, 1920)

    def test_every_source_must_be_inside_the_repository(self):
        data = json.loads(PATHS.media_encode.read_text())
        data["jobs"] = [{"slot": "home/classroom-film", "source": "../elsewhere.mp4", "profile": "clip", "startSeconds": 1, "seconds": 14,
                         "poster": {"slot": "home/classroom-film-poster", "atSeconds": 5}}]
        copy = PATHS.media_encode.with_name("encode-test.json")
        copy.write_text(json.dumps(data))
        try:
            paths = replace_encode(PATHS, copy)
            with self.assertRaises(BuildError) as raised:
                load_jobs(paths)
            self.assertIn("inside the repository", str(raised.exception))
        finally:
            copy.unlink()


def replace_encode(paths: Paths, file: Path):
    class Other(type(paths)):
        @property
        def media_encode(self) -> Path:
            return file
    return Other(paths.root)


class ArgumentsTest(unittest.TestCase):
    def test_the_film_loses_sound_and_every_piece_of_metadata(self):
        args = video_args("ffmpeg", JOB, Path("out.mp4"))
        self.assertIn("-an", args)
        self.assertEqual(args[args.index("-map_metadata") + 1], "-1")
        self.assertEqual(args[args.index("-map_chapters") + 1], "-1")
        self.assertIn("encoder=", args)
        self.assertEqual(args[args.index("-pix_fmt") + 1], "yuv420p")
        self.assertEqual(args[args.index("-g") + 1], str(JOB.profile.gop))
        self.assertEqual(args[args.index("-t") + 1], "14")
        self.assertEqual(args[-1], "out.mp4")

    def test_commands_are_argument_lists_that_cannot_be_read_as_options(self):
        for args in (video_args("ffmpeg", JOB, Path("o.mp4")), poster_args("ffmpeg", JOB, Path("f.mp4"), Path("p.jpg")),
                     probe_args("ffprobe", Path("f.mp4")), keyframe_args("ffprobe", Path("f.mp4"))):
            self.assertIsInstance(args, list)
            self.assertTrue(all(isinstance(a, str) for a in args))
        # the source follows -i, so a file name that starts with a dash is still a file name
        args = video_args("ffmpeg", JOB, Path("o.mp4"))
        self.assertEqual(args[args.index("-i") + 1], str(JOB.source))
        self.assertTrue(str(JOB.source).startswith("/"))

    def test_the_poster_has_no_metadata_and_one_frame(self):
        args = poster_args("ffmpeg", JOB, Path("f.mp4"), Path("p.jpg"))
        self.assertEqual(args[args.index("-frames:v") + 1], "1")
        self.assertEqual(args[args.index("-map_metadata") + 1], "-1")


class CheckTest(unittest.TestCase):
    def test_a_right_film_passes(self):
        self.assertEqual(check_output(good_probe(), JOB.profile.gop, JOB), [])

    def test_sound_or_extra_streams_fail(self):
        probe = good_probe()
        probe["streams"].append({"codec_type": "audio", "codec_name": "aac"})
        self.assertTrue(check_output(probe, JOB.profile.gop, JOB)[0].startswith("home/classroom-film: expected one video stream"))

    def test_wrong_codec_size_rate_length_and_keyframes_fail(self):
        self.assertTrue(any("h264 yuv420p" in m for m in check_output(good_probe(pix_fmt="yuvj420p"), JOB.profile.gop, JOB)))
        self.assertTrue(any("even size" in m for m in check_output(good_probe(width=1920), JOB.profile.gop, JOB)))
        self.assertTrue(any("even size" in m for m in check_output(good_probe(height=2521), JOB.profile.gop, JOB)))
        self.assertTrue(any("frame rate" in m for m in check_output(good_probe(r_frame_rate="60/1"), JOB.profile.gop, JOB)))
        long = good_probe()
        long["format"]["duration"] = "20.0"
        self.assertTrue(any("longer than" in m for m in check_output(long, JOB.profile.gop, JOB)))
        self.assertTrue(any("between keyframes" in m for m in check_output(good_probe(), JOB.profile.gop + 1, JOB)))

    def test_where_it_was_filmed_or_when_must_not_survive(self):
        probe = good_probe()
        probe["format"]["tags"].update({"creation_time": "2026-03-25T15:49:22Z", "location": "+18.5810+073.8171/"})
        problems = check_output(probe, JOB.profile.gop, JOB)
        self.assertTrue(any("creation_time" in m and "location" in m for m in problems))

    def test_keyframe_spacing_is_counted_from_ffprobe_output(self):
        self.assertEqual(longest_gap(["1", "0", "0", "0", "1", "0", "0", "0", "1"]), 4)
        self.assertEqual(longest_gap(["1", "0", "0", "0", "0", "0"]), 6)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is not installed")
class FilesTest(unittest.TestCase):
    """The film and poster the project ships: read back with ffprobe, not trusted from the encoder's own settings."""

    def test_the_shipped_film_has_no_sound_and_no_place_or_time_in_it(self):
        import subprocess
        film = PATHS.root / "packages/media/assets/home/classroom-film.mp4"
        if not film.exists():
            self.skipTest("run make media-encode")
        probe = json.loads(subprocess.run(probe_args("ffprobe", film), capture_output=True, text=True, check=True).stdout)
        flags = subprocess.run(keyframe_args("ffprobe", film), capture_output=True, text=True, check=True).stdout.splitlines()
        self.assertEqual(check_output(probe, longest_gap(flags), JOB), [])
        self.assertNotIn(b"location", film.read_bytes()[:4096].lower())


if __name__ == "__main__":
    unittest.main()
