# Changelog

All notable changes to `ableton-ai` are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
