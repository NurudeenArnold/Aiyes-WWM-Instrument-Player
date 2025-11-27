# midi_tools/tempo.py

def extract_tempo_map(events):
    division = None
    tempos = []

    for ev in events:
        if not ev.get("is_data"):
            continue

        if ev["type"] == "Header":
            division = int(ev["args"][2])

        if ev["type"] == "Tempo":
            tempos.append((ev["time"], int(ev["args"][0])))

    if division is None:
        raise ValueError("No Header record with division found in file.")

    if not tempos:
        tempos = [(0, 500000)]

    tempos.sort(key=lambda x: x[0])
    return division, tempos


def ticks_to_ms(tick, tempo_map, division):
    ms_total = 0.0
    for i, (t0, tempo) in enumerate(tempo_map):
        if i + 1 < len(tempo_map):
            t1 = tempo_map[i + 1][0]
        else:
            t1 = tick

        if tick <= t0:
            break

        seg_start = t0
        seg_end = min(t1, tick)
        dticks = max(0, seg_end - seg_start)
        us_per_tick = tempo / division
        ms_total += dticks * us_per_tick / 1000.0

        if tick < t1:
            break

    return ms_total


def tick_diff_to_ms(t1, t2, tempo_map, division):
    return ticks_to_ms(t2, tempo_map, division) - ticks_to_ms(t1, tempo_map, division)
