# midi_tools/io_midicsv.py
import chardet
import py_midicsv as pm

def detect_encoding(path):
    encoding_type = chardet.detect(open(path, "rb").read())["encoding"]
    return encoding_type

def load_midicsv(path):
    events = []
    with open(path, "r", newline="", encoding=detect_encoding(path)) as f:
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


def midi_to_csv(midi_path, csv_out):
    csv_lines = pm.midi_to_csv(midi_path)
    with open(csv_out, "w", encoding=detect_encoding(midi_path)) as f:
        f.writelines(csv_lines)


def csv_to_midi(csv_in, midi_out):
    with open(csv_in, "r", encoding="utf-8") as f:
        csv_lines = f.readlines()
    midi_object = pm.csv_to_midi(csv_lines)
    with open(midi_out, "wb") as output_file:
        midi_writer = pm.FileWriter(output_file)
        midi_writer.write(midi_object)
