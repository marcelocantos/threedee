# Bambu X1C LAN tools

Scripts for slicing against the X1 Carbon's full Studio presets, uploading
to the printer over FTPS, starting and watching a print over MQTT, and
grabbing a camera still. They talk to the printer on the LAN only.

## Credentials

The MQTT/FTPS user is `bblp`. The access code and serial are read at
runtime from Bambu Studio's config
(`~/Library/Application Support/BambuStudio/BambuStudio.conf`). They must
never be hard-coded or committed.

The LAN IP is not in that config when Studio is in LAN Only mode. Set
`BAMBU_IP`, or copy `ip.local.example` to `ip.local` (gitignored) and put
the address on the first line.

The MQTT and camera clients skip TLS certificate verification: the printer
uses a self-signed certificate.

`send.py`, `status.py`, `monitor.py` and `light.py` need `paho-mqtt`
(`pip install -r tools/bambu/requirements.txt`). `snap.py` needs `ffmpeg`.

## Scripts

Run them from this directory (they import `creds` as a sibling), or add it
to `PYTHONPATH`.

- `flatten.py` — Flatten Studio's machine, process and filament presets,
  resolving both `inherits` and `include`. Defaults are the X1C 0.4 mm
  nozzle, 0.20 mm Standard, and Bambu PLA Basic. Pass `--filament-map` with
  a 0-based AMS tray id and `--filament-colour` if needed. Exits nonzero if
  the flattened start gcode has no `M620 S[initial_no_support_extruder]A`.
- `ftp.py` — List the SD card, or upload a file to its root, over implicit
  FTPS on port 990.
- `send.py` — Start a `project_file` print of a file already on the SD
  card. `--ams-tray` is required and is 0-based. `--check` only inspects a
  local `.gcode.3mf` for a real `M620 S0A` line.
- `status.py` — Current job and AMS tray contents (read-only).
- `monitor.py` — Poll status until FINISH or FAILED holds, or the time
  limit is reached. Read-only; never pauses, stops, or starts a print.
- `snap.py` — One still from the LAN live view (`rtsps`, port 322).
- `light.py` — Chamber light `on` or `off`.

The printer must be in LAN Only mode with Developer Mode enabled, and a
FAT32 microSD card must be in the slot, before `project_file` will run.

## Lessons from the mixer-stand prints (13 November 2026)

- **FAT32 only.** The X1C will not read an exFAT card (HMS 0500-0100-0003-0006,
  "Unformatted SD Card"). Format the card on the printer itself. A nearly
  full card only affects timelapse (HMS 0500-0100-0003-0004).
- **`ams_mapping` is a 0-based tray id.** Slot 1 (first AMS slot) is `0`,
  slot 2 is `1`. Passing `1` when you meant "slot 1" sends the job to the
  second spool.
- **`flatten.py` must resolve `include` templates, not just `inherits`.**
  The X1C start gcode lives in included templates that override
  `fdm_machine_common`. A flatten that skips `include` produces a generic
  start sequence with no AMS load. The first mixer-stand API job ran all
  259 layers, reported success, and left nothing on the bed and no purge
  waste, because the toolhead never loaded filament.
- **Check for `M620 S0A` before sending.** In the flattened preset the AMS
  load is the template `M620 S[initial_no_support_extruder]A`; after
  slicing it becomes a real `M620 S0A` line in the plate gcode. `send.py`
  checks the sliced file by default and refuses to send if that command is
  missing (a mention inside a header comment is not enough). A matching
  `M621 S0A` and `G1 E50` are a good sign too.
- **Cloud mode rejects local `project_file`.** The ACK is "mqtt message
  verify failed", `err_code` 84033543, HMS 0500-0500-0001-0007. LAN Only
  plus Developer Mode is required; the Developer Mode warning is real, but
  the local API does not work without it.
