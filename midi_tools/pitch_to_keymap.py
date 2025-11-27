# # pitch_to_keymap.py
#
# BASE_LOW   = 48      # low octave C
# BASE_MED   = BASE_LOW + 12   # 60
# BASE_HIGH  = BASE_LOW + 24   # 72
#
# PITCH_TO_KEY = {
#     # ---------- High octave (q–u row) ----------
#     BASE_HIGH + 0:  "q",        # do
#     BASE_HIGH + 1:  "shift+q",  # do sharp
#     BASE_HIGH + 2:  "w",        # re
#     BASE_HIGH + 3:  "ctrl+e",   # mi flat
#     BASE_HIGH + 4:  "e",        # mi
#     BASE_HIGH + 5:  "r",        # fa
#     BASE_HIGH + 6:  "shift+r",  # fa sharp
#     BASE_HIGH + 7:  "t",        # so
#     BASE_HIGH + 8:  "shift+t",  # so sharp
#     BASE_HIGH + 9:  "y",        # la
#     BASE_HIGH + 10: "ctrl+u",   # ti flat
#     BASE_HIGH + 11: "u",        # ti
#
#     # ---------- Medium octave (a–j row) ----------
#     BASE_MED + 0:   "a",        # do
#     BASE_MED + 1:   "shift+a",  # do sharp
#     BASE_MED + 2:   "s",        # re
#     BASE_MED + 3:   "ctrl+d",   # mi flat
#     BASE_MED + 4:   "d",        # mi
#     BASE_MED + 5:   "f",        # fa
#     BASE_MED + 6:   "shift+f",  # fa sharp
#     BASE_MED + 7:   "g",        # so
#     BASE_MED + 8:   "shift+g",  # so sharp
#     BASE_MED + 9:   "h",        # la
#     BASE_MED + 10:  "ctrl+j",   # ti flat
#     BASE_MED + 11:  "j",        # ti
#
#     # ---------- Low octave (z–m row) ----------
#     BASE_LOW + 0:   "z",        # do
#     BASE_LOW + 1:   "shift+z",  # do sharp
#     BASE_LOW + 2:   "x",        # re
#     BASE_LOW + 3:   "ctrl+c",   # mi flat
#     BASE_LOW + 4:   "c",        # mi
#     BASE_LOW + 5:   "v",        # fa
#     BASE_LOW + 6:   "shift+v",  # fa sharp
#     BASE_LOW + 7:   "b",        # so
#     BASE_LOW + 8:   "shift+b",  # so sharp
#     BASE_LOW + 9:   "n",        # la
#     BASE_LOW + 10:  "ctrl+m",   # ti flat
#     BASE_LOW + 11:  "m",        # ti
# }
#
# def pitch_to_key(pitch: int) -> str | None:
#     """
#     Map a MIDI pitch to your digital instrument key combo.
#
#     Assumes your pipeline has already transposed everything into the
#     3-octave window starting at BASE_LOW (i.e. 48–83 by default).
#     """
#     return PITCH_TO_KEY.get(pitch)

# midi_tools/pitch_to_keymap.py

# We assume your pipeline has already transposed everything into
# a 3-octave range: 48–59 (low), 60–71 (medium), 72–83 (high).

BASE_LOW  = 48          # low octave C
BASE_MED  = BASE_LOW + 12   # 60
BASE_HIGH = BASE_LOW + 24   # 72

PITCH_TO_KEY = {
    # ---------- High octave (q–u row) ----------
    BASE_HIGH + 0:  "q",        # do
    BASE_HIGH + 1:  "shift+q",  # do sharp
    BASE_HIGH + 2:  "w",        # re
    BASE_HIGH + 3:  "ctrl+e",   # mi flat
    BASE_HIGH + 4:  "e",        # mi
    BASE_HIGH + 5:  "r",        # fa
    BASE_HIGH + 6:  "shift+r",  # fa sharp
    BASE_HIGH + 7:  "t",        # so
    BASE_HIGH + 8:  "shift+t",  # so sharp
    BASE_HIGH + 9:  "y",        # la
    BASE_HIGH + 10: "ctrl+u",   # ti flat
    BASE_HIGH + 11: "u",        # ti

    # ---------- Medium octave (a–j row) ----------
    BASE_MED + 0:   "a",        # do
    BASE_MED + 1:   "shift+a",  # do sharp
    BASE_MED + 2:   "s",        # re
    BASE_MED + 3:   "ctrl+d",   # mi flat
    BASE_MED + 4:   "d",        # mi
    BASE_MED + 5:   "f",        # fa
    BASE_MED + 6:   "shift+f",  # fa sharp
    BASE_MED + 7:   "g",        # so
    BASE_MED + 8:   "shift+g",  # so sharp
    BASE_MED + 9:   "h",        # la
    BASE_MED + 10:  "ctrl+j",   # ti flat
    BASE_MED + 11:  "j",        # ti

    # ---------- Low octave (z–m row) ----------
    BASE_LOW + 0:   "z",        # do
    BASE_LOW + 1:   "shift+z",  # do sharp
    BASE_LOW + 2:   "x",        # re
    BASE_LOW + 3:   "ctrl+c",   # mi flat
    BASE_LOW + 4:   "c",        # mi
    BASE_LOW + 5:   "v",        # fa
    BASE_LOW + 6:   "shift+v",  # fa sharp
    BASE_LOW + 7:   "b",        # so
    BASE_LOW + 8:   "shift+b",  # so sharp
    BASE_LOW + 9:   "n",        # la
    BASE_LOW + 10:  "ctrl+m",   # ti flat
    BASE_LOW + 11:  "m",        # ti
}


def pitch_to_key(pitch: int) -> str | None:
    """
    Map a MIDI pitch to your digital instrument key combo.

    Returns:
        key combo string like "q" or "shift+g", or None if out of range.
    """
    return PITCH_TO_KEY.get(pitch)

