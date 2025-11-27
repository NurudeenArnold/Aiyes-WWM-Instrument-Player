# midi_tools/macro.py
#
# from .io_midicsv import load_midicsv
# from .tempo import extract_tempo_map, ticks_to_ms
# from .pitch_to_keymap import pitch_to_key
#
#
# def csv_to_keystroke_macro(csv_path: str):
#     """
#     Convert a processed midicsv file into a list of keystroke macro events.
#
#     Each macro event is:
#         {"time": seconds_from_start, "key": "shift+q", "pitch": 72, "channel": 0}
#     """
#     events = load_midicsv(csv_path)
#     division, tempo_map = extract_tempo_map(events)
#
#     macro = []
#
#     for ev in events:
#         if not ev.get("is_data"):
#             continue
#         if ev["type"] != "Note_on_c":
#             continue
#
#         # Note_on_c: channel, pitch, velocity
#         channel = int(ev["args"][0])
#         pitch   = int(ev["args"][1])
#         vel     = int(ev["args"][2])
#
#         # Ignore 0-velocity Note_on (these are Note_offs in some MIDI styles)
#         if vel <= 0:
#             continue
#
#         key_combo = pitch_to_key(pitch)
#         if key_combo is None:
#             # Outside 3-octave playable range → skip
#             continue
#
#         t_seconds = ticks_to_ms(ev["time"], tempo_map, division) / 1000.0
#
#         macro.append({
#             "time":    t_seconds,
#             "key":     key_combo,
#             "pitch":   pitch,
#             "channel": channel,
#         })
#
#     macro.sort(key=lambda x: x["time"])
#     return macro
#
#
# def write_python_macro_script(macro, script_path: str):
#     """
#     Write a standalone Python script that can play this macro using the
#     'keyboard' library.
#     """
#     lines = []
#     lines.append("# Auto-generated macro script")
#     lines.append("import time")
#     lines.append("import keyboard")
#     lines.append("")
#     lines.append("macro = [")
#
#     for ev in macro:
#         lines.append(
#             f"    {{'time': {ev['time']:.6f}, 'key': {ev['key']!r}}},"
#         )
#
#     lines.append("]")
#     lines.append("")
#     lines.append("def play():")
#     lines.append("    if not macro:")
#     lines.append("        print('Macro is empty – nothing to play.')")
#     lines.append("        return")
#     lines.append("")
#     lines.append("    start_time = time.time()")
#     lines.append("    for event in macro:")
#     lines.append("        target = event['time']")
#     lines.append("        key = event['key']")
#     lines.append("        now = time.time() - start_time")
#     lines.append("        delay = target - now")
#     lines.append("        if delay > 0:")
#     lines.append("            time.sleep(delay)")
#     lines.append("        keyboard.send(key)")
#     lines.append("")
#     lines.append("if __name__ == '__main__':")
#     lines.append("    input('Focus your digital instrument window, then press Enter to start...')")
#     lines.append("    play()")
#     lines.append("")
#
#     with open(script_path, "w", encoding="utf-8") as f:
#         f.write("\n".join(lines))


# midi_tools/macro.py

from midi_tools.io_midicsv import load_midicsv
from midi_tools.tempo import extract_tempo_map, ticks_to_ms
from midi_tools.pitch_to_keymap import pitch_to_key

# How close notes have to be (in seconds) to count as "same time" chord.
CHORD_WINDOW_SECONDS = 0.02   # 20 ms

# How much to stagger chord notes (in seconds) when rolling them.
CHORD_ROLL_STEP_SECONDS = 0.005  # 5 ms


def roll_chords_in_macro(macro):
    """
    For any group of macro events occurring within CHORD_WINDOW_SECONDS from
    the first note in that group, stagger their times by CHORD_ROLL_STEP_SECONDS
    so a monophonic instrument can play them sequentially.

    Mutates the macro list in-place and assumes it's already sorted by 'time'.
    """
    i = 0
    n = len(macro)

    while i < n:
        start_time = macro[i]["time"]
        j = i + 1

        # Find all events that occur within CHORD_WINDOW_SECONDS of the first.
        while j < n and (macro[j]["time"] - start_time) <= CHORD_WINDOW_SECONDS:
            j += 1

        # [i, j) is the chord group (could be size 1).
        group_size = j - i
        if group_size > 1:
            # Stagger each note in the group.
            for k in range(i, j):
                offset = (k - i) * CHORD_ROLL_STEP_SECONDS
                macro[k]["time"] = start_time + offset

        i = j


def csv_to_keystroke_macro(csv_path: str):
    """
    Convert a processed midicsv file into a list of keystroke macro events.

    Each macro event is:
        {"time": seconds_from_start, "key": "shift+q", "pitch": 72, "channel": 0}
    """
    events = load_midicsv(csv_path)
    division, tempo_map = extract_tempo_map(events)

    macro = []

    for ev in events:
        if not ev.get("is_data"):
            continue
        if ev["type"] != "Note_on_c":
            continue

        # Note_on_c: channel, pitch, velocity
        channel = int(ev["args"][0])
        pitch   = int(ev["args"][1])
        vel     = int(ev["args"][2])

        # Ignore 0-velocity Note_on (these are Note_offs in some MIDI styles)
        if vel <= 0:
            continue

        key_combo = pitch_to_key(pitch)
        if key_combo is None:
            # Outside 3-octave playable range → skip
            continue

        t_seconds = ticks_to_ms(ev["time"], tempo_map, division) / 1000.0

        macro.append({
            "time":    t_seconds,
            "key":     key_combo,
            "pitch":   pitch,
            "channel": channel,
        })

    # Sort by time first
    macro.sort(key=lambda x: x["time"])

    # Then roll any chords so a monophonic instrument can handle them
    roll_chords_in_macro(macro)

    return macro


def write_python_macro_script(macro, script_path: str):
    """
    Write a standalone Python script that can play this macro using the
    'keyboard' library.
    """
    lines = ["# Auto-generated macro script", "import time", "import keyboard", "", "macro = ["]

    for ev in macro:
        lines.append(
            f"    {{'time': {ev['time']:.6f}, 'key': {ev['key']!r}}},"
        )

    lines.append("]")
    lines.append("")
    lines.append("def play():")
    lines.append("    if not macro:")
    lines.append("        print('Macro is empty – nothing to play.')")
    lines.append("        return")
    lines.append("")
    lines.append("    start_time = time.time()")
    lines.append("    for event in macro:")
    lines.append("        target = event['time']")
    lines.append("        key = event['key']")
    lines.append("        now = time.time() - start_time")
    lines.append("        delay = target - now")
    lines.append("        if delay > 0:")
    lines.append("            time.sleep(delay)")
    lines.append("        keyboard.send(key)")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    input('Focus your digital instrument window, then press Enter to start...')")
    lines.append("    play()")
    lines.append("")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
