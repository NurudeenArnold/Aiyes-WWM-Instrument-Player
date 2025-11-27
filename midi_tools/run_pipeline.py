# # run_pipeline.py
# import os
# from midi_tools.io_midicsv import midi_to_csv, csv_to_midi
# from midi_tools.pipeline import process_file
#
# def run_one(midi_input, midicsv_exe, csvmidi_exe, cleanup=False):
#     folder = os.path.dirname(midi_input)
#     base = os.path.splitext(os.path.basename(midi_input))[0]
#
#     tmp_csv = os.path.join(folder, base + "_raw.csv")
#     tmp_csv_transposed = os.path.join(folder, base + "_transposed.csv")
#     midi_output = os.path.join(folder, base + "_transposed.mid")
#
#     print("Step 1 — Converting MIDI → CSV with midicsv...")
#     midi_to_csv(midicsv_exe, midi_input, tmp_csv)
#
#     print("Step 2 — Transposing CSV...")
#     process_file(tmp_csv, tmp_csv_transposed)
#
#     print("Step 3 — Converting CSV → MIDI with csvmidi...")
#     csv_to_midi(csvmidi_exe, tmp_csv_transposed, midi_output)
#
#     if cleanup:
#         try:
#             os.remove(tmp_csv)
#             os.remove(tmp_csv_transposed)
#         except OSError:
#             pass
#
#     print("\nDONE!")
#     print("Created:", midi_output)
#
#
# def main():
#     # --- USER SETTINGS: edit these in PyCharm and hit Run ---
#     midicsv_exe = r"C:\Users\miria\OneDrive\Desktop\MIDI\midicsv.exe"
#     csvmidi_exe = r"C:\Users\miria\OneDrive\Desktop\MIDI\csvmidi.exe"
#
#     # Choose which piece you’re working on:
#     midi_input = (
#         r"C:\Users\miria\OneDrive\Desktop\MIDI\Final Fantasy VII - Final Fantasy VII Theme Piano Version.mid"
#         # or:
#         # r"C:\Users\miria\OneDrive\Desktop\MIDI\Spirited Away - Ryuu no Shounen - from the Official Piano Solo Album.mid"
#     )
#
#     run_one(midi_input, midicsv_exe, csvmidi_exe, cleanup=False)
#
#
# if __name__ == "__main__":
#     main()


#
# # run_pipeline.py
# import os
# from midi_tools.io_midicsv import midi_to_csv, csv_to_midi
# from midi_tools.pipeline import process_file
# from midi_tools.macro import csv_to_keystroke_macro, write_python_macro_script
#
#
# def run_one(midi_input, midicsv_exe, csvmidi_exe, cleanup=False):
#     folder = os.path.dirname(midi_input)
#     base = os.path.splitext(os.path.basename(midi_input))[0]
#
#     tmp_csv = os.path.join(folder, base + "_raw.csv")
#     tmp_csv_transposed = os.path.join(folder, base + "_transposed.csv")
#     midi_output = os.path.join(folder, base + "_transposed.mid")
#     macro_script = os.path.join(folder, base + "_macro.py")
#
#     # 1) MIDI → raw CSV
#     print("Step 1 — Converting MIDI → CSV with midicsv...")
#     midi_to_csv(midicsv_exe, midi_input, tmp_csv)
#
#     # 2) Process CSV (hand mapping & pruning)
#     print("Step 2 — Processing CSV (hand mapping, deletion rules)...")
#     process_file(tmp_csv, tmp_csv_transposed)
#
#     # 3) Processed CSV → MIDI
#     print("Step 3 — Converting processed CSV → MIDI with csvmidi...")
#     csv_to_midi(csvmidi_exe, tmp_csv_transposed, midi_output)
#     print(f"  → Wrote processed MIDI to: {midi_output}")
#
#     # 4) Processed CSV → Python macro script
#     print("Step 4 — Building Python macro from processed CSV...")
#     macro = csv_to_keystroke_macro(tmp_csv_transposed)
#     print(f"  → {len(macro)} macro events")
#     write_python_macro_script(macro, macro_script)
#     print(f"  → Wrote macro script to: {macro_script}")
#
#     # Optional cleanup of intermediate CSV files
#     if cleanup:
#         print("Cleaning up temporary CSV files...")
#         for path in (tmp_csv, tmp_csv_transposed):
#             try:
#                 os.remove(path)
#             except OSError:
#                 pass
#
#
# def main():
#     # Update these paths for your system:
#     midicsv_exe = r"C:\Users\miria\OneDrive\Desktop\MIDI\midicsv.exe"
#     csvmidi_exe = r"C:\Users\miria\OneDrive\Desktop\MIDI\csvmidi.exe"
#
#     # Choose which piece you’re working on:
#     midi_input = (
#         r"C:\Users\miria\OneDrive\Desktop\MIDI\Final Fantasy VII_ AC - Aerith's Theme Piano Version.mid"
#         # or:
#         # r"C:\Users\miria\OneDrive\Desktop\MIDI\Spirited Away - Ryuu no Shounen - from the Official Piano Solo Album.mid"
#     )
#
#     run_one(midi_input, midicsv_exe, csvmidi_exe, cleanup=False)
#
#
# if __name__ == "__main__":
#     main()



# run_pipeline.py
import os

from midi_tools.io_midicsv import midi_to_csv, csv_to_midi, load_midicsv
from midi_tools.pipeline import process_file
from midi_tools.macro import csv_to_keystroke_macro, write_python_macro_script
from midi_tools.notes import collect_note_ons


def print_pitch_debug_from_csv(csv_path: str, label: str):
    """
    Load a midicsv file, collect all Note_on_c events, and print pitch stats.
    """
    print(f"\n=== {label} ===")
    try:
        events = load_midicsv(csv_path)
    except FileNotFoundError:
        print(f"  (File not found: {csv_path})")
        return

    notes = collect_note_ons(events)
    if not notes:
        print("  No Note_on_c events with velocity > 0 found.")
        return

    pitches = sorted(n["pitch"] for n in notes)
    p_min = pitches[0]
    p_max = pitches[-1]

    print(f"  Note-on count: {len(pitches)}")
    print(f"  Pitch range: {p_min} – {p_max}")
    # Show a few lowest & highest pitches to spot weird outliers
    print(f"  Lowest few pitches: {pitches[:10]}")
    print(f"  Highest few pitches: {pitches[-10:]}")


def print_pitch_debug_from_macro(macro, label: str):
    """
    Print pitch stats from the generated macro list.
    Each macro event is: {'time': float, 'key': 'shift+q', 'pitch': int, 'channel': int}
    """
    print(f"\n=== {label} ===")
    if not macro:
        print("  Macro is empty.")
        return

    pitches = sorted(ev["pitch"] for ev in macro)
    p_min = pitches[0]
    p_max = pitches[-1]

    print(f"  Macro event count: {len(macro)}")
    print(f"  Pitch range: {p_min} – {p_max}")
    print(f"  Lowest few macro pitches: {pitches[:10]}")
    print(f"  Highest few macro pitches: {pitches[-10:]}")

    # Also show a few of the highest-pitch macro events with their key mappings
    print("  Sample highest-pitch macro events (time, pitch -> key):")
    for ev in macro[-10:]:
        print(f"    t={ev['time']:.3f}s  pitch={ev['pitch']}  key={ev['key']}")


def run_one(midi_input, midicsv_exe, csvmidi_exe, cleanup=False):
    folder = os.path.dirname(midi_input)
    base = os.path.splitext(os.path.basename(midi_input))[0]

    tmp_csv = os.path.join(folder, base + "_raw.csv")
    tmp_csv_transposed = os.path.join(folder, base + "_transposed.csv")
    midi_output = os.path.join(folder, base + "_transposed.mid")
    macro_script = os.path.join(folder, base + "_macro.py")

    # 1) MIDI → raw CSV
    print("Step 1 — Converting MIDI → CSV with midicsv...")
    midi_to_csv(midicsv_exe, midi_input, tmp_csv)

    # Debug: inspect raw CSV pitch range
    print_pitch_debug_from_csv(str(tmp_csv), "Raw CSV pitch stats")

    # 2) Process CSV (hand mapping & sliding into 3-oct window)
    print("\nStep 2 — Processing CSV (hand mapping / sliding into window)...")
    process_file(tmp_csv, tmp_csv_transposed)

    # Debug: inspect processed CSV pitch range
    print_pitch_debug_from_csv(str(tmp_csv_transposed), "Processed CSV pitch stats")

    # 3) Processed CSV → MIDI
    print("\nStep 3 — Converting processed CSV → MIDI with csvmidi...")
    csv_to_midi(csvmidi_exe, tmp_csv_transposed, midi_output)
    print(f"  → Wrote processed MIDI to: {midi_output}")

    # 4) Processed CSV → Python macro script
    print("\nStep 4 — Building Python macro from processed CSV...")
    macro = csv_to_keystroke_macro(str(tmp_csv_transposed))
    print(f"  → {len(macro)} macro events")

    # Debug: inspect macro pitch range
    print_pitch_debug_from_macro(macro, "Macro pitch stats")

    write_python_macro_script(macro, str(macro_script))
    print(f"  → Wrote macro script to: {macro_script}")

    # Optional cleanup of intermediate CSV files
    if cleanup:
        print("\nCleaning up temporary CSV files...")
        for path in (tmp_csv, tmp_csv_transposed):
            try:
                os.remove(path)
            except OSError:
                pass

    print("\nDONE!")


def main():
    # Update these paths for your system:
    midicsv_exe = r"C:\Users\miria\OneDrive\Desktop\MIDI\midicsv.exe"
    csvmidi_exe = r"C:\Users\miria\OneDrive\Desktop\MIDI\csvmidi.exe"

    # Choose which piece you’re working on:
    midi_input = (
        r"C:\Users\miria\OneDrive\Desktop\MIDI\Final Fantasy VII_ AC - Tifa's Theme Piano Version.mid"
    )

    run_one(midi_input, midicsv_exe, csvmidi_exe, cleanup=False)


if __name__ == "__main__":
    main()



## in command prompy
## python "C:\path\to\Song_macro.py"

## python "C:\Users\miria\OneDrive\Desktop\MIDI\Final Fantasy VII_ AC - Aerith's Theme Piano Version_macro.py"

## python "C:\Users\miria\OneDrive\Desktop\MIDI\Spirited Away - Waltz of Chihiro_macro.py"

## python "C:\Users\miria\OneDrive\Desktop\MIDI\Final Fantasy VII_ AC - Tifa's Theme Piano Version_macro.py"
