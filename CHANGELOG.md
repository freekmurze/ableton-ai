# Changelog

All notable changes to `ableton-ai` are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.2.0

All of this batch is verified running in Ableton Live 12.

New tools: arrangement-view MIDI clips (create_arrangement_midi_clip), master
and return track device parameters, and add_shaped_automation (draws a repeating
waveform onto any parameter as clip automation; not a free-running LFO). Plus
per-note probability, rack internals and scale setting, which existed in the
remote script but had no tool.

Fixes: clip automation actually writes now (it called a non-existent
insert_value, then a zero-duration insert_step, both silent no-ops, so every
envelope came out flat). VST/AU plug-ins load from the browser. All note
commands use Live 11's note API, so Live no longer warns about legacy note
editing. The remote script's 260-branch command dispatch is now a lookup table,
with its first automated tests.

## 1.1.0

Added 20 tools for commands the remote script already supported but did not
expose, including the flagship features that previously had no tool at all:
per-note probability (add_notes_with_probability), rack internals
(get/set_chain_device_parameter), and scale setting (set_song_scale). Also
return tracks, clip follow actions, fades and markers, quantize, tap_tempo, and
more. 148 tools total.

The remote script's command dispatch is now a lookup table instead of a
260-branch if/elif across two chains plus a whitelist. Behaviour is unchanged,
proven by a static body-equivalence check, and the remote script has its first
automated tests.

Removed two browser commands (get_browser_categories, get_browser_items) that
called methods which never existed and always errored. Nothing used them.

## 1.0.0

First release.

Control Ableton Live from an AI assistant over MCP. Around 130 tools covering
most of the Live Object Model: tracks, devices and their parameters, clips,
MIDI notes, automation, the browser, transport, and the mixer.

Highlights:

- Per-note probability and velocity deviation via `add_notes_with_probability`.
- Reach devices nested inside racks with `get_chain_device_parameters` and
  `set_chain_device_parameter`.
- `set_song_scale`, plus a `get_scale_notes` that follows the song's scale.
- Clip automation that targets a specific device and returns the real curve when
  read back.
- One-command remote-script install: `uvx --from ableton-ai install-remote-script`.
- A Claude Code skill under `skills/ableton`.
