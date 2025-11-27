# midi_tools/mapping.py

# def apply_hand_mapping(events, threshold, Lmin, Lmax, Rmin, Rmax):
#     to_delete = set()
#
#     for idx, ev in enumerate(events):
#         if not ev.get("is_data"):
#             continue
#         if ev["type"] not in ("Note_on_c", "Note_off_c"):
#             continue
#
#         args = ev["args"]
#         pitch = int(args[1])
#
#         if pitch <= threshold:
#             if pitch > Lmax:
#                 to_delete.add(idx)
#         else:
#             if pitch < Rmin:
#                 to_delete.add(idx)
#
#     return [ev for i, ev in enumerate(events) if i not in to_delete]



#
# #
# # # midi_tools/mapping.py
# #
# def apply_hand_mapping(events, threshold, wmin=48, wmax=83):
#     """
#     Slide the MIDI's low and high pitch regions into a single playable window
#     [wmin, wmax], allowing overlap.
#
#     Conceptually:
#       - All note events are split into two segments by `threshold`:
#           * low segment:  pitches <= threshold
#           * high segment: pitches > threshold
#       - We find the global min and max pitch of the piece.
#       - Low segment is shifted so the global lowest pitch maps to wmin.
#       - High segment is shifted so the global highest pitch maps to wmax.
#       - Overlap between the segments inside [wmin, wmax] is fine.
#       - If any mapped note falls outside [wmin, wmax], we drop that note
#         (this ends up trimming only the highest notes of the low segment
#          or the lowest notes of the high segment when necessary).
#
#     All Note_on_c and Note_off_c events are updated consistently so note
#     pairs stay aligned.
#     """
#
#     # ---- Collect all pitches from note events ----
#     pitches = []
#
#     for ev in events:
#         if not ev.get("is_data"):
#             continue
#         if ev["type"] not in ("Note_on_c", "Note_off_c"):
#             continue
#
#         args = ev["args"]
#         if len(args) < 2:
#             continue
#
#         try:
#             pitch = int(args[1])
#         except ValueError:
#             continue
#
#         pitches.append(pitch)
#
#     if not pitches:
#         # No note events → nothing to do
#         return events
#
#     P_min = min(pitches)
#     P_max = max(pitches)
#
#     low_pitches  = [p for p in pitches if p <= threshold]
#     high_pitches = [p for p in pitches if p > threshold]
#
#     has_low = bool(low_pitches)
#     has_high = bool(high_pitches)
#
#     # ---- Compute offsets for low and high segments ----
#     # We always try to:
#     #   P_min  → wmin
#     #   P_max  → wmax
#     # when we have both low and high segments.
#     if has_low and has_high:
#         offset_low  = wmin - P_min
#         offset_high = wmax - P_max
#     else:
#         # Degenerate case: everything is effectively on one "side".
#         # We still want to preserve extremes as much as possible inside [wmin, wmax].
#         offset_candidate_low  = wmin - P_min
#         offset_candidate_high = wmax - P_max
#
#         span        = P_max - P_min
#         window_span = wmax - wmin
#
#         if span <= window_span:
#             # The full span can fit; choose an offset roughly between the two
#             # that keeps both ends inside the window.
#             offset = (offset_candidate_low + offset_candidate_high) / 2.0
#         else:
#             # Span is larger than the window. Prioritize mapping the lowest note
#             # onto wmin and rely on clipping overflow at the top.
#             offset = offset_candidate_low
#
#         offset_low = offset_high = offset
#
#     # ---- Apply offsets and drop notes that end up outside [wmin, wmax] ----
#     to_delete = set()
#
#     for idx, ev in enumerate(events):
#         if not ev.get("is_data"):
#             continue
#         if ev["type"] not in ("Note_on_c", "Note_off_c"):
#             continue
#
#         args = ev["args"]
#         if len(args) < 2:
#             continue
#
#         try:
#             pitch = int(args[1])
#         except ValueError:
#             continue
#
#         if has_low and has_high:
#             if pitch <= threshold:
#                 offset = offset_low
#             else:
#                 offset = offset_high
#         else:
#             # Single-segment case: everything uses the same offset
#             offset = offset_low  # == offset_high
#
#         new_pitch_f = pitch + offset
#         # Offset may be float in the degenerate centering case → round to int
#         new_pitch = int(round(new_pitch_f))
#
#         if new_pitch < wmin or new_pitch > wmax:
#             # This trims only the "overflow" interior notes:
#             #   - top of the low segment
#             #   - bottom of the high segment
#             to_delete.add(idx)
#             continue
#
#         # Update pitch in-place
#         args[1] = str(new_pitch)
#
#     # Return a new events list with any out-of-window notes removed
#     return [ev for i, ev in enumerate(events) if i not in to_delete]

# midi_tools/mapping.py

def apply_hand_mapping(events, _threshold=None, wmin=48, wmax=83):
    """
    Simple global transpose:

    - Find the highest pitch in the file.
    - Compute an offset so that this highest pitch maps to wmax.
    - Apply that same offset to ALL note events (Note_on_c / Note_off_c).
    - Drop any notes that, after transposition, fall outside [wmin, wmax].

    This guarantees that:
      - The highest note in the piece is always playable (mapped to wmax).
      - Lower notes are shifted down by the same amount.
      - Extremely low notes may be discarded if the original span is huge,
        but the top of the melody is preserved.
    """

    # ---- Collect all pitches from note events ----
    pitches = []

    for ev in events:
        if not ev.get("is_data"):
            continue
        if ev["type"] not in ("Note_on_c", "Note_off_c"):
            continue

        args = ev["args"]
        if len(args) < 2:
            continue

        try:
            pitch = int(args[1])
        except ValueError:
            continue

        pitches.append(pitch)

    if not pitches:
        # No note events → nothing to transpose
        return events

    P_max = max(pitches)

    # Offset so that the highest pitch lands exactly at wmax
    offset = wmax - P_max

    to_delete = set()

    for idx, ev in enumerate(events):
        if not ev.get("is_data"):
            continue
        if ev["type"] not in ("Note_on_c", "Note_off_c"):
            continue

        args = ev["args"]
        if len(args) < 2:
            continue

        try:
            pitch = int(args[1])
        except ValueError:
            continue

        new_pitch = pitch + offset

        # If transposed note is outside the playable window, drop it
        if new_pitch < wmin or new_pitch > wmax:
            to_delete.add(idx)
            continue

        # Update pitch in-place
        args[1] = str(new_pitch)

    # Return new event list with out-of-window notes removed
    return [ev for i, ev in enumerate(events) if i not in to_delete]
