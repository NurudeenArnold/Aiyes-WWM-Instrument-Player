# midi_tools/notes.py
from .tempo import tick_diff_to_ms

def collect_note_ons(events):
    notes = []
    for idx, ev in enumerate(events):
        if not ev.get("is_data"):
            continue
        if ev["type"] == "Note_on_c":
            channel = int(ev["args"][0])
            pitch = int(ev["args"][1])
            velocity = int(ev["args"][2])
            if velocity > 0:
                notes.append({
                    "idx": idx,
                    "track": ev["track"],
                    "time": ev["time"],
                    "channel": channel,
                    "pitch": pitch
                })
    return notes


def kmeans_1d_two_clusters(values, iterations=20):
    if not values:
        return None, None, None

    min_v = min(values)
    max_v = max(values)
    c_low = float(min_v)
    c_high = float(max_v)

    for _ in range(iterations):
        low_group = []
        high_group = []
        for v in values:
            if abs(v - c_low) <= abs(v - c_high):
                low_group.append(v)
            else:
                high_group.append(v)

        if low_group:
            c_low = sum(low_group) / len(low_group)
        if high_group:
            c_high = sum(high_group) / len(high_group)

    if c_low > c_high:
        c_low, c_high = c_high, c_low

    threshold = (c_low + c_high) / 2.0
    return c_low, c_high, threshold


def group_chords(notes, tempo_map, division, window_ms=20.0):
    if not notes:
        return []

    notes_sorted = sorted(notes, key=lambda x: x["time"])
    groups = []

    current_group = [notes_sorted[0]]
    ref_time = notes_sorted[0]["time"]

    for n in notes_sorted[1:]:
        dt_ms = tick_diff_to_ms(ref_time, n["time"], tempo_map, division)
        if dt_ms <= window_ms:
            current_group.append(n)
        else:
            groups.append(current_group)
            current_group = [n]
            ref_time = n["time"]

    groups.append(current_group)
    return groups
