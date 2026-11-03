"""Turn supplied videos into the files the site serves (packages/media/encode.json).

Each job reads one source video from inside the repository and writes the file of an awaited video
slot, plus a poster photo for it. Encoding always drops the sound and every piece of metadata: phone
videos carry the place and time they were filmed, and classroom sound can carry names. The output is
checked with ffprobe before it is written (codec, pixel format, size, frame rate, length, keyframe
spacing, no stray tags). ffmpeg is run with an argument list, never through a shell.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..errors import BuildError
from ..images.scrub import metadata_found, scrub
from ..jsonio import read_json, write_bytes
from ..paths import Paths
from .library import Library, load_library
from .tools import Runner, find_tool, run_checked


@dataclass(frozen=True)
class Profile:
    name: str
    max_width: int
    fps: int
    crf: int
    preset: str
    gop: int
    poster_quality: int
    allowed_tags: frozenset[str]


@dataclass(frozen=True)
class Job:
    slot: str
    source: Path
    profile: Profile
    start: float
    seconds: float
    poster_slot: str
    poster_at: float


@dataclass(frozen=True)
class Encoded:
    slot: str
    poster_slot: str
    width: int
    height: int
    seconds: float
    bytes: int
    poster_bytes: int


def load_jobs(paths: Paths, library: Library | None = None) -> list[Job]:
    """The jobs in encode.json, checked against the media manifest and the repository."""
    raw = read_json(paths.media_encode)
    library = library or load_library(paths)
    slots = {s.id: s for s in library.slots}
    profiles = {name: Profile(name, p["maxWidth"], p["fps"], p["crf"], p["preset"], p["gop"], p["posterQuality"],
                              frozenset(p["allowedTags"])) for name, p in raw["profiles"].items()}
    jobs, problems = [], []
    for entry in raw["jobs"]:
        where = entry.get("slot", "?")
        film, poster = slots.get(entry.get("slot", "")), slots.get(entry.get("poster", {}).get("slot", ""))
        source = (paths.root / entry.get("source", "")).resolve()
        if film is None or film.kind != "video" or film.origin != "encoded":
            problems.append(f"{where}: needs an encoded video slot in manifest.json")
        if poster is None or poster.kind != "image" or poster.origin != "encoded":
            problems.append(f"{where}: its poster needs an encoded image slot in manifest.json")
        for slot in (film, poster):
            if slot is not None and slot.source != entry.get("source"):
                problems.append(f"{slot.id}: manifest source {slot.source!r} must name the job's source {entry.get('source')!r}")
        if not source.is_relative_to(paths.root) or not source.is_file():
            problems.append(f"{where}: source {entry.get('source')} is not a file inside the repository")
        if entry.get("profile") not in profiles:
            problems.append(f"{where}: unknown profile {entry.get('profile')!r}")
        if not (entry.get("seconds", 0) > 0 and entry.get("startSeconds", -1) >= 0):
            problems.append(f"{where}: startSeconds and seconds must be numbers, seconds above zero")
        if problems:
            continue
        jobs.append(Job(entry["slot"], source, profiles[entry["profile"]], float(entry["startSeconds"]), float(entry["seconds"]),
                        entry["poster"]["slot"], float(entry["poster"]["atSeconds"])))
    if problems:
        raise BuildError("packages/media/encode.json:\n  " + "\n  ".join(problems))
    return jobs


def _scale(profile: Profile, colour_range: str) -> str:
    # Never wider than max_width, never enlarged, even sides. Video uses studio range (tv), a JPEG full range (pc).
    return f"scale=w='min({profile.max_width},iw)':h=-2:out_range={colour_range}"


def video_args(ffmpeg: str, job: Job, output: Path) -> list[str]:
    p = job.profile
    return [
        ffmpeg, "-nostdin", "-v", "error", "-y", "-ss", f"{job.start:g}", "-t", f"{job.seconds:g}", "-i", str(job.source),
        "-map", "0:v:0", "-an", "-map_metadata", "-1", "-map_chapters", "-1", "-metadata:s:v:0", "encoder=",
        "-vf", f"{_scale(p, 'tv')},fps={p.fps},format=yuv420p",
        "-c:v", "libx264", "-x264-params", "no-info=1", "-preset", p.preset, "-crf", str(p.crf), "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-g", str(p.gop), "-keyint_min", str(p.gop), "-sc_threshold", "0",
        "-movflags", "+faststart", "-fflags", "+bitexact", "-flags:v", "+bitexact", str(output),
    ]


def poster_args(ffmpeg: str, job: Job, film: Path, output: Path) -> list[str]:
    p = job.profile
    return [
        ffmpeg, "-nostdin", "-v", "error", "-y", "-ss", f"{job.poster_at:g}", "-i", str(film), "-frames:v", "1",
        "-map_metadata", "-1", "-vf", f"{_scale(p, 'pc')},format=yuvj420p", "-q:v", str(p.poster_quality), "-fflags", "+bitexact", str(output),
    ]


def probe_args(ffprobe: str, path: Path) -> list[str]:
    return [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]


def keyframe_args(ffprobe: str, path: Path) -> list[str]:
    return [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=key_frame", "-of", "csv=p=0", str(path)]


def longest_gap(flags: Sequence[str]) -> int:
    """Most frames between two keyframes, from ffprobe's key_frame column (1 or 0 per frame)."""
    gap = longest = 0
    for flag in flags:
        if flag.strip().startswith("1"):
            gap = 1
        else:
            gap += 1
        longest = max(longest, gap)
    return longest


def check_output(probe: Mapping[str, Any], gap: int, job: Job) -> list[str]:
    """Everything the encoded film must be, as problems (empty when it is right)."""
    p, problems = job.profile, []
    streams = probe.get("streams", [])
    if len(streams) != 1 or streams[0].get("codec_type") != "video":
        return [f"{job.slot}: expected one video stream and nothing else (sound, data), got {[s.get('codec_type') for s in streams]}"]
    s, fmt = streams[0], probe.get("format", {})
    if s.get("codec_name") != "h264" or s.get("pix_fmt") != "yuv420p":
        problems.append(f"{job.slot}: expected h264 yuv420p, got {s.get('codec_name')} {s.get('pix_fmt')}")
    width, height = int(s.get("width", 0)), int(s.get("height", 0))
    if not 0 < width <= p.max_width or width % 2 or height % 2:
        problems.append(f"{job.slot}: {width}x{height} is not an even size within {p.max_width} px wide")
    if s.get("r_frame_rate") != f"{p.fps}/1":
        problems.append(f"{job.slot}: frame rate {s.get('r_frame_rate')}, expected {p.fps}/1")
    if float(fmt.get("duration", 0)) > job.seconds + 0.1:
        problems.append(f"{job.slot}: {fmt.get('duration')} s is longer than the {job.seconds:g} s asked for")
    if gap > p.gop:
        problems.append(f"{job.slot}: {gap} frames between keyframes, the profile allows {p.gop}")
    tags = {**fmt.get("tags", {}), **s.get("tags", {})}
    stray = sorted(set(tags) - p.allowed_tags)
    if stray:
        problems.append(f"{job.slot}: metadata left in the file: {', '.join(stray)}")
    return problems


def encode_all(paths: Paths, run: Runner = subprocess.run) -> list[Encoded]:
    """Encode every job into its slot's file and poster. Nothing is written for a job that fails its checks."""
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    timeout = int(read_json(paths.media_encode)["timeoutSeconds"])
    library = load_library(paths)
    slots = {s.id: s for s in library.slots}
    results = []
    for job in load_jobs(paths, library):
        source = json.loads(run_checked(run, probe_args(ffprobe, job.source), timeout, f"reading {job.source.name}"))
        length = float(source["format"]["duration"])
        if job.start + job.seconds > length + 0.05:
            raise BuildError(f"{job.slot}: {job.source.name} is {length:.1f} s long; {job.start:g} + {job.seconds:g} s runs past the end")
        with tempfile.TemporaryDirectory(prefix="dsapkit-encode-") as scratch:
            film, poster = Path(scratch) / "film.mp4", Path(scratch) / "poster.jpg"
            run_checked(run, video_args(ffmpeg, job, film), timeout, f"encoding {job.slot}")
            probe = json.loads(run_checked(run, probe_args(ffprobe, film), timeout, f"checking {job.slot}"))
            gap = longest_gap(run_checked(run, keyframe_args(ffprobe, film), timeout, f"checking {job.slot}").splitlines())
            problems = check_output(probe, gap, job)
            if problems:
                raise BuildError("encoded film is not as the profile asks:\n  " + "\n  ".join(problems))
            run_checked(run, poster_args(ffmpeg, job, film, poster), timeout, f"making the poster of {job.slot}")
            film_bytes, poster_bytes = film.read_bytes(), scrub(poster.read_bytes(), library.keep_profile)
            hidden = metadata_found(film_bytes) + metadata_found(poster_bytes, library.keep_profile)
            if hidden:
                raise BuildError(f"{job.slot}: the encoded files still carry {', '.join(hidden)}")
        write_bytes(paths.root / slots[job.slot].file, film_bytes)
        write_bytes(paths.root / slots[job.poster_slot].file, poster_bytes)
        s = probe["streams"][0]
        results.append(Encoded(job.slot, job.poster_slot, int(s["width"]), int(s["height"]), float(probe["format"]["duration"]),
                               len(film_bytes), len(poster_bytes)))
    return results
