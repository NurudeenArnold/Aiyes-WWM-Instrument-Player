# midi_tools/pipeline.py
# from .io_midicsv import load_midicsv, write_midicsv
# from .tempo import extract_tempo_map
# from .notes import collect_note_ons, kmeans_1d_two_clusters, group_chords
# from .mapping import apply_hand_mapping
#
# def process_file(infile, outfile,
#                  Lmin=48, Lmax=66,
#                  Rmin=72, Rmax=83):
#     events = load_midicsv(infile)
#     division, tempo_map = extract_tempo_map(events)
#     notes = collect_note_ons(events)
#     pitches = [n["pitch"] for n in notes]
#
#     if not pitches:
#         print("No note-on events found.")
#         write_midicsv(events, outfile)
#         return
#
#     c_low, c_high, threshold = kmeans_1d_two_clusters(pitches)
#
#     left_notes = [n for n in notes if n["pitch"] <= threshold]
#     right_notes = [n for n in notes if n["pitch"] > threshold]
#     # left_chords = group_chords(left_notes, tempo_map, division)
#     # right_chords = group_chords(right_notes, tempo_map, division)
#
#     print("Applying new side-mapping with deletion rules...")
#     events = apply_hand_mapping(events, threshold, Lmin, Lmax, Rmin, Rmax)
#
#     write_midicsv(events, outfile)

from midi_tools.io_midicsv import load_midicsv, write_midicsv
from midi_tools.notes import collect_note_ons, kmeans_1d_two_clusters
from midi_tools.mapping import apply_hand_mapping


def process_file(infile, outfile,
                 window_min=48, window_max=83):
    """
    Preprocess a MIDI→CSV file:

      1) Load events.
      2) Compute basic pitch stats (for logging / future use).
      3) Apply a simple global transpose so that the highest pitch
         lands at window_max and everything else is shifted equally.
      4) Drop any notes that fall outside [window_min, window_max].
      5) Write the transformed CSV.

    This ignores hand-splitting; it only ensures the top of the
    piece is always in range of the instrument.
    """
    events = load_midicsv(infile)

    notes = collect_note_ons(events)
    pitches = [n["pitch"] for n in notes]

    if not pitches:
        print("No note-on events found.")
        write_midicsv(events, outfile)
        return

    P_min = min(pitches)
    P_max = max(pitches)
    print(f"Original pitch range: {P_min} – {P_max}")

    # We no longer really need the k-means threshold, but we compute it
    # for potential future diagnostics; apply_hand_mapping ignores it.
    c_low, c_high, threshold = kmeans_1d_two_clusters(pitches)
    print("K-means clusters (unused for transpose, just info):")
    print(f"  low  center = {c_low:.2f}")
    print(f"  high center = {c_high:.2f}")
    print(f"  split threshold = {threshold:.2f}")

    print(f"Applying simple global transpose into [{window_min}, {window_max}]...")
    events = apply_hand_mapping(events, threshold, window_min, window_max)

    write_midicsv(events, outfile)

