"""Tests for the remote script's command dispatch.

The remote script runs inside Ableton, so it normally can't be imported here.
We mock the _Framework.ControlSurface base and load it off-Live, which lets us
test the dispatch table and threading routing without a running Ableton. This
is the only automated coverage the remote script has.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

REMOTE_SCRIPT = Path(__file__).resolve().parents[2] / "remote_script" / "__init__.py"


@pytest.fixture(scope="module")
def remote_class() -> Any:
    """Load the remote script class with the Ableton framework mocked out."""
    fw = types.ModuleType("_Framework")
    cs = types.ModuleType("_Framework.ControlSurface")

    class ControlSurface:
        def __init__(self, *a: Any, **k: Any) -> None: ...
        def log_message(self, *a: Any) -> None: ...
        def show_message(self, *a: Any) -> None: ...

    cs.ControlSurface = ControlSurface  # type: ignore[attr-defined]
    fw.ControlSurface = cs  # type: ignore[attr-defined]
    sys.modules["_Framework"] = fw
    sys.modules["_Framework.ControlSurface"] = cs

    spec = importlib.util.spec_from_file_location("remote_script_under_test", REMOTE_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AbletonAI


@pytest.fixture
def instance(remote_class: Any) -> Any:
    """A remote-script instance that never opened a socket, with main-thread
    scheduling collapsed to run inline."""
    obj = remote_class.__new__(remote_class)
    obj.schedule_message = lambda delay, fn: fn()
    return obj


def test_unknown_command_errors(instance: Any) -> None:
    result = instance._process_command({"type": "no_such_command", "params": {}})
    assert result["status"] == "error"
    assert "Unknown command" in result["message"]


def test_read_command_runs_directly(instance: Any) -> None:
    instance._get_session_info = lambda: {"tempo": 120}
    result = instance._process_command({"type": "get_session_info", "params": {}})
    assert result["status"] == "success"
    assert result["result"] == {"tempo": 120}


def test_write_command_is_scheduled_and_returns_result(instance: Any) -> None:
    calls = []
    instance._create_midi_track = lambda index: calls.append(index) or {"name": "1-MIDI"}
    result = instance._process_command({"type": "create_midi_track", "params": {"index": -1}})
    assert result["status"] == "success"
    assert result["result"]["name"] == "1-MIDI"
    assert calls == [-1]


def test_dispatch_table_marks_reads_and_writes(instance: Any) -> None:
    assert instance._DISPATCH["get_session_info"] == ("_rd_get_session_info", False)
    assert instance._DISPATCH["create_midi_track"] == ("_wr_create_midi_track", True)


def test_orphan_command_stays_unreachable(instance: Any) -> None:
    """load_instrument_or_effect had a handler but was never whitelisted, so it
    was unreachable. The refactor must not accidentally expose it."""
    assert "load_instrument_or_effect" not in instance._DISPATCH


def test_state_changing_commands_route_to_main_thread(instance: Any) -> None:
    """A representative set of mutating commands must be flagged for the main
    thread, because mutating Live off the main thread crashes it."""
    for cmd in ("create_midi_track", "set_track_volume", "add_notes_to_clip", "set_tempo"):
        assert instance._DISPATCH[cmd][1] is True, f"{cmd} must run on the main thread"


def test_write_note_tuples_uses_modern_api_on_live11(instance: object) -> None:
    """On Live 11+ (clip has add_new_notes) the helper must use it, not the
    legacy set_notes that triggers Ableton's data-loss warning."""

    class ModernClip:
        length = 4.0

        def __init__(self) -> None:
            self.added: object = None
            self.set_notes_called = False

        def remove_notes_extended(self, *a: object) -> None: ...
        def add_new_notes(self, specs: object) -> None:
            self.added = specs

        def set_notes(self, notes: object) -> None:
            self.set_notes_called = True

    import sys

    Live = type(sys)("Live")
    Clip = type(sys)("Live.Clip")

    class MidiNoteSpecification:
        def __init__(self, **kw: object) -> None:
            self.kw = kw

    Clip.MidiNoteSpecification = MidiNoteSpecification
    Live.Clip = Clip
    sys.modules["Live"] = Live
    sys.modules["Live.Clip"] = Clip

    clip = ModernClip()
    count = instance._write_note_tuples(clip, [(60, 0.0, 1.0, 100, False)], replace=True)

    assert count == 1
    assert clip.added is not None, "should have used add_new_notes"
    assert clip.set_notes_called is False, "must not use legacy set_notes on Live 11+"


def test_write_note_tuples_does_not_recurse_on_legacy_clip(instance: object) -> None:
    """A clip without add_new_notes must fall through to set_notes exactly once,
    not call the helper again (the regex refactor briefly made this infinite)."""

    class LegacyClip:
        length = 4.0

        def __init__(self) -> None:
            self.set_notes_calls = 0

        def remove_notes(self, *a: object) -> None: ...
        def set_notes(self, notes: object) -> None:
            self.set_notes_calls += 1

    clip = LegacyClip()
    count = instance._write_note_tuples(clip, [(60, 0.0, 1.0, 100, False)], replace=True)

    assert count == 1
    assert clip.set_notes_calls == 1


# -- reading notes off the Arrangement timeline ----------------------------


class _ArrNote:
    """Stands in for a Live MidiNote from get_notes_extended."""

    def __init__(self, pitch: float, start: float, prob: float = 1.0) -> None:
        self.pitch = pitch
        self.start_time = start
        self.duration = 0.25
        self.velocity = 100
        self.mute = False
        self.probability = prob
        self.velocity_deviation = 3


class _ArrClip:
    is_midi_clip = True
    name = "Elektro 82"
    start_time = 230.0
    end_time = 1378.0
    length = 16.0
    looping = True
    loop_start = 0.0
    loop_end = 16.0
    start_marker = 0.0
    end_marker = 16.0

    def __init__(self) -> None:
        self.requested: tuple[object, ...] | None = None

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):  # type: ignore[no-untyped-def]
        self.requested = (from_pitch, pitch_span, from_time, time_span)
        return [_ArrNote(38, 4.0, 0.5), _ArrNote(36, 0.0)]


def _song_with(clips: list[object], has_attr: bool = True) -> object:
    track = types.SimpleNamespace()
    if has_attr:
        track.arrangement_clips = clips
    return types.SimpleNamespace(tracks=[track])


def test_arrangement_clip_notes_is_a_read_command(instance: Any) -> None:
    assert instance._DISPATCH["get_arrangement_clip_notes"] == (
        "_rd_get_arrangement_clip_notes",
        False,
    )


def test_arrangement_clip_notes_returns_notes_with_probability(instance: Any) -> None:
    clip = _ArrClip()
    instance._song = _song_with([clip])

    result = instance._get_arrangement_clip_notes(0, 0)

    assert result["note_count"] == 2
    assert result["has_probability"] is True
    assert result["clip_name"] == "Elektro 82"
    # sorted by time then pitch, so the downbeat kick comes first
    assert result["notes"][0]["pitch"] == 36
    assert result["notes"][1]["probability"] == 0.5
    assert result["notes"][1]["velocity_deviation"] == 3


def test_arrangement_clip_notes_reads_the_loop_not_the_extent(instance: Any) -> None:
    """A 16-beat loop stretched over 1147 beats must be read across its marker
    region. Reading the extent would return the same notes many times over."""
    clip = _ArrClip()
    instance._song = _song_with([clip])

    instance._get_arrangement_clip_notes(0, 0)

    assert clip.requested is not None
    _, _, from_time, time_span = clip.requested
    assert from_time == 0.0
    assert time_span == 16.0, "must span the markers, not start_time..end_time"


def test_arrangement_clip_notes_falls_back_without_extended_api(instance: Any) -> None:
    class LegacyArrClip:
        is_midi_clip = True
        name = "old"
        length = 4.0
        start_marker = 0.0
        end_marker = 4.0

        def __init__(self) -> None:
            self.deselected = False

        def select_all_notes(self) -> None: ...
        def get_selected_notes(self):  # type: ignore[no-untyped-def]
            return [(60, 0.0, 1.0, 100, False)]

        def deselect_all_notes(self) -> None:
            self.deselected = True

    clip = LegacyArrClip()
    instance._song = _song_with([clip])

    result = instance._get_arrangement_clip_notes(0, 0)

    assert result["note_count"] == 1
    assert result["has_probability"] is False
    assert "probability" not in result["notes"][0]
    assert clip.deselected is True


def test_arrangement_clip_notes_rejects_bad_index(instance: Any) -> None:
    instance._song = _song_with([])
    assert "out of range" in instance._get_arrangement_clip_notes(0, 0)["error"]


def test_arrangement_clip_notes_rejects_audio_clip(instance: Any) -> None:
    audio = types.SimpleNamespace(is_midi_clip=False)
    instance._song = _song_with([audio])
    assert "not a MIDI clip" in instance._get_arrangement_clip_notes(0, 0)["error"]


def test_arrangement_clip_notes_needs_live_11(instance: Any) -> None:
    instance._song = _song_with([], has_attr=False)
    assert "Live 11" in instance._get_arrangement_clip_notes(0, 0)["error"]


# -- writing notes into an existing Arrangement clip -----------------------


class _FakeSpec:
    """Stands in for Live.Clip.MidiNoteSpecification.

    The real object always exposes probability and velocity_deviation, so the
    defaults are declared here. The code guards on hasattr to stay safe on Live
    builds that predate them.
    """

    probability = 1.0
    velocity_deviation = 0.0

    def __init__(self, **kw: Any) -> None:
        for k, v in kw.items():
            setattr(self, k, v)


def _install_fake_live(monkeypatch: pytest.MonkeyPatch, accepts_probability: bool = True) -> None:
    Live = types.ModuleType("Live")
    Clip = types.ModuleType("Live.Clip")

    def make(**kw: Any) -> _FakeSpec:
        if "probability" in kw and not accepts_probability:
            raise TypeError("this Live build has no probability kwarg")
        return _FakeSpec(**kw)

    Clip.MidiNoteSpecification = make  # type: ignore[attr-defined]
    Live.Clip = Clip  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "Live", Live)
    monkeypatch.setitem(sys.modules, "Live.Clip", Clip)


class _WritableArrClip(_ArrClip):
    def __init__(self) -> None:
        super().__init__()
        self.added: tuple[Any, ...] = ()
        self.removed: tuple[Any, ...] | None = None
        self.recreated = False

    def remove_notes_extended(self, *a: Any) -> None:
        self.removed = a

    def add_new_notes(self, specs: tuple[Any, ...]) -> None:
        self.added = specs


def test_set_arrangement_clip_notes_is_a_write_command(instance: Any) -> None:
    """Mutating Live off the main thread crashes it, so this must be flagged."""
    assert instance._DISPATCH["set_arrangement_clip_notes"] == (
        "_wr_set_arrangement_clip_notes",
        True,
    )


def test_set_arrangement_clip_notes_keeps_probability_and_humanization(
    instance: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_live(monkeypatch)
    clip = _WritableArrClip()
    instance._song = _song_with([clip])

    result = instance._set_arrangement_clip_notes(
        0, 0, [{"pitch": 36, "start_time": 0.0, "probability": 0.42, "velocity_deviation": 9}]
    )

    assert result["notes_added"] == 1
    spec = clip.added[0]
    assert spec.probability == 0.42, "randomness must survive the write"
    assert spec.velocity_deviation == 9, "humanization must survive the write"


def test_note_specs_set_probability_when_kwarg_unsupported(
    instance: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Older Live builds reject probability in the constructor. It must then be
    assigned afterwards rather than silently dropped."""
    _install_fake_live(monkeypatch, accepts_probability=False)

    specs = instance._note_specs([{"pitch": 60, "probability": 0.3, "velocity_deviation": 4}])

    assert specs[0].probability == 0.3
    assert specs[0].velocity_deviation == 4


def test_set_arrangement_clip_notes_edits_in_place(
    instance: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The clip object must be reused, so loop braces, name and colour survive.
    Rebuilding it via create_midi_clip would collapse a stretched loop."""
    _install_fake_live(monkeypatch)
    clip = _WritableArrClip()
    instance._song = _song_with([clip])

    result = instance._set_arrangement_clip_notes(0, 0, [{"pitch": 36}])

    assert clip.recreated is False
    assert result["clip_name"] == "Elektro 82"
    assert result["length"] == 16.0, "loop length untouched"
    assert result["end_time"] == 1378.0, "stretched extent untouched"


def test_set_arrangement_clip_notes_replace_clears_only_the_loop(
    instance: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_live(monkeypatch)
    clip = _WritableArrClip()
    instance._song = _song_with([clip])

    result = instance._set_arrangement_clip_notes(0, 0, [{"pitch": 36}], replace=True)

    assert clip.removed == (0, 128, 0.0, 16.0), "must clear the marker region, not the extent"
    assert result["notes_removed"] == 2


def test_set_arrangement_clip_notes_can_layer_without_replacing(
    instance: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_live(monkeypatch)
    clip = _WritableArrClip()
    instance._song = _song_with([clip])

    result = instance._set_arrangement_clip_notes(0, 0, [{"pitch": 36}], replace=False)

    assert clip.removed is None, "replace=False must not delete anything"
    assert result["notes_removed"] == 0
    assert result["notes_added"] == 1


def test_set_arrangement_clip_notes_rejects_audio_clip(instance: Any) -> None:
    instance._song = _song_with([types.SimpleNamespace(is_midi_clip=False)])
    assert "not a MIDI clip" in instance._set_arrangement_clip_notes(0, 0, [])["error"]


def test_create_arrangement_clip_keeps_humanization(
    instance: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """create_arrangement_midi_clip used to set probability but drop
    velocity_deviation, so humanization was lost on every clip it made."""
    _install_fake_live(monkeypatch)
    clip = _WritableArrClip()
    track = types.SimpleNamespace(has_midi_input=True, create_midi_clip=lambda start, length: clip)
    instance._song = types.SimpleNamespace(tracks=[track])

    instance._create_arrangement_midi_clip(
        0, 0.0, 16.0, [{"pitch": 36, "probability": 0.6, "velocity_deviation": 7}]
    )

    assert clip.added[0].probability == 0.6
    assert clip.added[0].velocity_deviation == 7
