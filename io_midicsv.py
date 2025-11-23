# midi_tools/io_midicsv.py
import subprocess

def load_midicsv(path):
    events = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip("\n")
            striped = raw.strip()

            if striped == "" or striped.startswith("#") or striped.startswith(";"):
                events.append({"raw_line": raw, "is_data": False})
                continue

            parts = [p.strip() for p in raw.split(",")]
            if len(parts) < 3:
                events.append({"raw_line": raw, "is_data": False})
                continue

            track = int(parts[0])
            time = int(parts[1])
            etype = parts[2]
            args = parts[3:]

            events.append({
                "raw_line": raw,
                "is_data": True,
                "track": track,
                "time": time,
                "type": etype,
                "args": args
            })
    return events


def write_midicsv(events, outpath):
    with open(outpath, "w", encoding="utf-8", newline="\n") as f:
        for ev in events:
            if not ev.get("is_data"):
                f.write(ev["raw_line"] + "\n")
                continue

            line = f"{ev['track']}, {ev['time']}, {ev['type']}"
            for a in ev["args"]:
                line += f", {a}"
            f.write(line + "\n")


def midi_to_csv(midicsv_path, midi_path, csv_out):
    cmd = [midicsv_path, midi_path, csv_out]
    subprocess.run(cmd, check=True)


def csv_to_midi(csvmidi_path, csv_in, midi_out):
    cmd = [csvmidi_path, csv_in, midi_out]
    subprocess.run(cmd, check=True)
