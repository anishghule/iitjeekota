import json
import unittest

from dsapkit.images.scrub import metadata_found
from dsapkit.media.library import load_library, waiting
from dsapkit.paths import Paths

PATHS = Paths.discover()
ORIGINALS = "packages/media/originals/"
LARGEST_ORIGINAL = 25_000_000  # GitHub refuses a file over 100 MB; a copy this big is a sign it needs shrinking first


def local_sources() -> list[tuple[str, str]]:
    """(where, path) for every source that is a repository path, in the manifest and in encode.json."""
    out = [(s.id, s.source) for s in load_library(PATHS).slots if s.source and not s.source.startswith("https://")]
    encode = json.loads(PATHS.media_encode.read_text())
    for key in ("jobs", "photos"):
        out += [(f"encode.json {job['slot']}", job["source"]) for job in encode.get(key, [])]
    return out


class OriginalsTest(unittest.TestCase):
    """The build reads only what is committed: resources/ is gitignored, so a clean checkout (CI) does not have it."""

    def test_every_local_source_is_a_committed_copy_in_originals(self):
        sources = local_sources()
        self.assertTrue(sources)
        for where, path in sources:
            self.assertTrue(path.startswith(ORIGINALS), f"{where}: {path} is not under {ORIGINALS}")
            self.assertTrue((PATHS.root / path).is_file(), f"{where}: {path} is missing")

    def test_a_committed_slot_is_a_pinned_file_with_no_source_and_is_never_waiting(self):
        library = load_library(PATHS)
        committed = [s for s in library.slots if s.origin == "committed"]
        self.assertTrue(committed)
        lock = {e["id"] for e in json.loads(PATHS.media_lock.read_text())["files"]}
        for slot in committed:
            self.assertTrue(slot.pinned, slot.id)
            self.assertEqual(slot.source, "", f"{slot.id}: a committed file has no source to fetch from")
            self.assertTrue((PATHS.root / slot.file).is_file(), slot.id)
            self.assertIn(slot.id, lock)
        self.assertEqual([s.id for s in waiting(PATHS, library.slots) if s.origin == "committed"], [])

    def test_the_copies_carry_no_hidden_data_and_none_is_huge(self):
        files = [f for f in (PATHS.root / ORIGINALS).rglob("*") if f.is_file()]
        self.assertTrue(files)
        for file in files:
            data = file.read_bytes()
            self.assertLess(len(data), LARGEST_ORIGINAL, file.name)
            self.assertEqual(metadata_found(data, True), [], file.name)


if __name__ == "__main__":
    unittest.main()
