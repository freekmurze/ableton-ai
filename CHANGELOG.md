# Changelog

All notable changes to `ableton-ai` are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.3.0

### Added

- The Arrangement timeline is readable. `get_arrangement_clips` lists a track's
  clips and `get_arrangement_clip_notes` reads the notes inside one. Until now
  every note tool addressed Session clip slots, so anything recorded onto the
  timeline was invisible and reported "No clip in slot".
- `set_arrangement_clip_notes`, which edits an existing Arrangement clip in
  place. Creating a clip to change its notes discarded the loop braces, the
  name, the colour and any clip envelopes, and collapsed a stretched loop down
  to its loop length. Editing keeps all of it, so a 16 beat loop spread across
  300 bars stays spread, and rewriting its single stored copy updates every
  repeat at once.
- Per-note probability and velocity deviation survive in both directions, so a
  recorded take can be read, edited and written back without flattening its
  randomness or its humanization.

### Fixed

- `create_arrangement_midi_clip` kept per-note probability but dropped
  velocity_deviation, so humanization was silently lost on every clip it wrote.
  Both writers now share one note builder.
- Setters no longer report success over a failed operation. `send_command`
  raises on a top-level error, but several handlers report failure in-band as
  an `error` key inside the result, which produced confident nonsense like
  "Set track color to None". A `failed()` helper now gives every setter the
  same failure contract.
- `__version__` read package metadata under the old distribution name, so it
  always fell back to `0.0.0.dev0`.

### Changed

- Setters echo Live's own display string where there is one, so a single call
  reports "Set Frequency to 800 Hz" rather than a raw normalized float. One
  call is now enough to verify what landed.
- Grouping fails honestly instead of pretending. The Live API cannot group
  existing tracks, and the docs now point at return tracks, which is the
  scriptable way to share an effect.
- The skill documents the Session and Arrangement split, the loop versus extent
  trap, and corrects the claim that dropdowns cannot be set. Ordinary quantized
  parameters set fine; only choosers that pick another object cannot.

## 1.2.0

All of this batch is verified running in Ableton Live 12.

### Added

- Arrangement-view MIDI clips (create_arrangement_midi_clip).
- Master and return track device parameters.
- add_shaped_automation, which draws a repeating waveform onto any parameter as
  clip automation (not a free-running LFO).
- Tools for per-note probability, rack internals, and scale setting, which
  existed in the remote script but had no tool.

### Fixed

- Clip automation actually writes now. It called a non-existent insert_value,
  then a zero-duration insert_step, both silent no-ops, so every envelope came
  out flat.
- VST/AU plug-ins load from the browser.
- All note commands use Live 11's note API, so Live no longer warns about legacy
  note editing.

### Changed

- The remote script's 260-branch command dispatch is now a lookup table, with
  its first automated tests.

## 1.1.0

### Added

- 20 tools for commands the remote script already supported but did not expose,
  including the flagship features that previously had no tool at all: per-note
  probability (add_notes_with_probability), rack internals
  (get/set_chain_device_parameter), and scale setting (set_song_scale). Also
  return tracks, clip follow actions, fades and markers, quantize, tap_tempo,
  and more. 148 tools total.

### Changed

- The remote script's command dispatch is now a lookup table instead of a
  260-branch if/elif across two chains plus a whitelist. Behaviour is unchanged,
  proven by a static body-equivalence check, and the remote script has its first
  automated tests.

### Removed

- Two browser commands (get_browser_categories, get_browser_items) that called
  methods which never existed and always errored. Nothing used them.

## 1.0.0

First release. Control Ableton Live from an AI assistant over MCP. Around 130
tools covering most of the Live Object Model: tracks, devices and their
parameters, clips, MIDI notes, automation, the browser, transport, and the
mixer.

### Added

- Per-note probability and velocity deviation via `add_notes_with_probability`.
- Reach devices nested inside racks with `get_chain_device_parameters` and
  `set_chain_device_parameter`.
- `set_song_scale`, plus a `get_scale_notes` that follows the song's scale.
- Clip automation that targets a specific device and returns the real curve when
  read back.
- One-command remote-script install: `uvx --from ableton-ai install-remote-script`.
- A Claude Code skill under `skills/ableton`.
