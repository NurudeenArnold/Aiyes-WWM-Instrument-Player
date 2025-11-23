# csv_to_macro.py

from midi_tools.io_midicsv import load_midicsv
from midi_tools.tempo import extract_tempo_map, ticks_to_ms
from pitch_to_keymap import pitch_to_key

def csv_to_keystroke_macro(csv_path: str):
    """
    Convert a processed midicsv file into a list of keystroke macro events.

    Returns:
        [{"time": float_seconds, "key": "shift+q", "pitch": 72, "channel": 0}, ...]
    """
    events = load_midicsv(csv_path)
    division, tempo_map = extract_tempo_map(events)

    macro = []

    for ev in events:
        if not ev.get("is_data"):
            continue
        if ev["type"] != "Note_on_c":
            continue

        channel = int(ev["args"][0])
        pitch   = int(ev["args"][1])
        vel     = int(ev["args"][2])

        if vel <= 0:
            continue  # ignore zero-velocity Note_on

        key_combo = pitch_to_key(pitch)
        if key_combo is None:
            # Outside 3-octave playable range → skip
            continue

        t_seconds = ticks_to_ms(ev["time"], tempo_map, division) / 1000.0

        macro.append({
            "time":   t_seconds,
            "key":    key_combo,
            "pitch":  pitch,
            "channel": channel,
        })

    macro.sort(key=lambda x: x["time"])
    return macro
