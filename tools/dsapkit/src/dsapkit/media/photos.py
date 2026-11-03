"""Shrink supplied photos into the files the site serves (photoProfiles and photos in packages/media/encode.json).

A phone photo can be 8000 px wide and carries where and when it was taken. Each job reads one photo from
inside the repository and writes the file of an encoded image slot: no longer than the profile's longest
edge, never enlarged, upright (the camera's orientation is applied, then dropped), JPEG, no metadata.
The output is checked with ffprobe and scrubbed again before it is written, like a poster.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..errors import BuildError
from ..images.scrub import metadata_found, scrub
from ..jsonio import read_json, write_bytes
from ..paths import Paths
from .encode import probe_args
from .library import Library, load_library
from .tools import Runner, find_tool, run_checked


@dataclass(frozen=True)
class PhotoProfile:
    name: str
    max_edge: int
    quality: int  # ffmpeg's JPEG scale: 2 is best, 31 is worst


@dataclass(frozen=True)
class PhotoJob:
    slot: str
    source: Path
    profile: PhotoProfile


@dataclass(frozen=True)
class Photo:
    slot: str
    width: int
    height: int
    bytes: int


def load_photo_jobs(paths: Paths, library: Library | None = None) -> list[PhotoJob]:
    """The photo jobs in encode.json, checked against the media manifest and the repository."""
    raw = read_json(paths.media_encode)
    library = library or load_library(paths)
    slots = {s.id: s for s in library.slots}
    profiles = {name: PhotoProfile(name, p["maxEdge"], p["quality"]) for name, p in raw.get("photoProfiles", {}).items()}
    jobs, problems = [], []
    for entry in raw.get("photos", []):
        where = entry.get("slot", "?")
        slot = slots.get(entry.get("slot", ""))
        source = (paths.root / entry.get("source", "")).resolve()
        if slot is None or slot.kind != "image" or slot.origin != "encoded":
            problems.append(f"{where}: needs an encoded image slot in manifest.json")
        elif slot.source != entry.get("source"):
            problems.append(f"{slot.id}: manifest source {slot.source!r} must name the job's source {entry.get('source')!r}")
        if not source.is_relative_to(paths.root) or not source.is_file():
            problems.append(f"{where}: source {entry.get('source')} is not a file inside the repository")
        if entry.get("profile") not in profiles:
            problems.append(f"{where}: unknown photo profile {entry.get('profile')!r}")
        if not problems:
            jobs.append(PhotoJob(entry["slot"], source, profiles[entry["profile"]]))
    if problems:
        raise BuildError("packages/media/encode.json:\n  " + "\n  ".join(problems))
    return jobs


def photo_args(ffmpeg: str, job: PhotoJob, output: Path) -> list[str]:
    edge = job.profile.max_edge
    # Fit inside edge x edge without enlarging; JPEG uses full range, so the scale says so.
    fit = f"scale=w='min({edge},iw)':h='min({edge},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2:out_range=pc"
    return [
        ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(job.source), "-map", "0:v:0", "-frames:v", "1",
        "-map_metadata", "-1", "-vf", f"{fit},format=yuvj420p", "-q:v", str(job.profile.quality),
        "-fflags", "+bitexact", "-flags:v", "+bitexact", str(output),
    ]


def check_photo(probe: Mapping[str, Any], job: PhotoJob) -> list[str]:
    """Everything the shrunk photo must be, as problems (empty when it is right)."""
    streams = probe.get("streams", [])
    if len(streams) != 1 or streams[0].get("codec_type") != "video":
        return [f"{job.slot}: expected one picture and nothing else, got {[s.get('codec_type') for s in streams]}"]
    s, problems = streams[0], []
    if s.get("codec_name") != "mjpeg":
        problems.append(f"{job.slot}: expected a JPEG, got {s.get('codec_name')}")
    width, height = int(s.get("width", 0)), int(s.get("height", 0))
    if not 0 < max(width, height) <= job.profile.max_edge:
        problems.append(f"{job.slot}: {width}x{height} is not within {job.profile.max_edge} px on its longest edge")
    if s.get("tags"):
        problems.append(f"{job.slot}: metadata left in the file: {', '.join(sorted(s['tags']))}")
    return problems


def encode_photos(paths: Paths, run: Runner = subprocess.run) -> list[Photo]:
    """Shrink every photo job into its slot's file. Nothing is written for a job that fails its checks."""
    library = load_library(paths)
    jobs = load_photo_jobs(paths, library)
    if not jobs:
        return []
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    timeout = int(read_json(paths.media_encode)["timeoutSeconds"])
    slots = {s.id: s for s in library.slots}
    results = []
    for job in jobs:
        with tempfile.TemporaryDirectory(prefix="dsapkit-photo-") as scratch:
            out = Path(scratch) / "photo.jpg"
            run_checked(run, photo_args(ffmpeg, job, out), timeout, f"shrinking {job.slot}")
            probe = json.loads(run_checked(run, probe_args(ffprobe, out), timeout, f"checking {job.slot}"))
            problems = check_photo(probe, job)
            if problems:
                raise BuildError("shrunk photo is not as the profile asks:\n  " + "\n  ".join(problems))
            data = scrub(out.read_bytes(), library.keep_profile)
            hidden = metadata_found(data, library.keep_profile)
            if hidden:
                raise BuildError(f"{job.slot}: the shrunk photo still carries {', '.join(hidden)}")
        write_bytes(paths.root / slots[job.slot].file, data)
        s = probe["streams"][0]
        results.append(Photo(job.slot, int(s["width"]), int(s["height"]), len(data)))
    return results
