import ctypes
import json
import os
import platform
import sys
import tempfile
import threading
import time
import traceback

import keyboard  # global key sender
from PyQt5 import QtCore, QtGui, QtWidgets

# --- Your existing tools ---
from midi_tools.io_midicsv import midi_to_csv
from midi_tools.macro import csv_to_keystroke_macro
from midi_tools.pipeline import process_file


# ==========================
#  CONFIG
# ==========================

def resource_path(relative_name: str) -> str:
    """
    Get absolute path to a bundled resource (works in dev & PyInstaller).

    - In dev: returns path relative to this file.
    - In frozen (one-file or one-folder): returns path
      inside the PyInstaller bundle.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS  # type: ignore[attr-defined]
    elif getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, relative_name)

STOP_HOTKEY = "Pause"
SLEEP_TIME = 2

WINDOW_MIN_PITCH = 48
WINDOW_MAX_PITCH = 83
PLAYLIST_GAP_SECONDS = 5.0


# ==========================
#  Nord Color Theme
# ==========================

# Nord palette colors
NORD_BG = "#2E3440"          # main window background
NORD_SURFACE = "#3B4252"     # panels / controls
NORD_SURFACE_ALT = "#434C5E" # hover / subtle contrast
NORD_BORDER = "#4C566A"

NORD_TEXT = "#ECEFF4"
NORD_TEXT_MUTED = "#D8DEE9"
NORD_HEADER = "#E5E9F0"

NORD_ACCENT = "#88C0D0"      # primary accent (selection / highlight)
NORD_ACCENT_POS = "#A3BE8C"  # positive, e.g. play
NORD_ERROR = "#BF616A"
NORD_WARNING = "#EBCB8B"

def enable_windows_dark_titlebar(window: QtWidgets.QWidget):
    """
    Try to enable the dark title bar on Windows 10/11 for this window.

    This uses the DwmSetWindowAttribute API. If it fails, or we're not on Windows, it quietly does nothing.
    """
    if platform.system() != "Windows":
        return

    try:
        hwnd = int(window.winId())
    except (Exception,):
        return

    DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # value for newer Windows 10/11
    DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19  # fallback for older builds

    # Prepare ctypes
    dwmapi = ctypes.windll.dwmapi
    attribute = ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE)
    use_dark = ctypes.c_int(1)

    # Try attribute 20 first
    result = dwmapi.DwmSetWindowAttribute(
        hwnd,
        attribute,
        ctypes.byref(use_dark),
        ctypes.sizeof(use_dark)
    )

    if result != 0:
        # Fallback: try attribute 19
        attribute = ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            attribute,
            ctypes.byref(use_dark),
            ctypes.sizeof(use_dark)
        )

def apply_nord_theme(app: QtWidgets.QApplication):
    """
    Apply a dark Nord theme to the whole application using QPalette + stylesheet.
    """
    app.setStyle("Fusion")  # Fusion works best with custom palettes

    palette = QtGui.QPalette()

    # Base colors
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(NORD_BG))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(NORD_TEXT))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(NORD_SURFACE))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(NORD_SURFACE_ALT))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(NORD_TEXT))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(NORD_SURFACE))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(NORD_TEXT))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(NORD_SURFACE))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(NORD_TEXT))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(NORD_ACCENT))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(NORD_BG))
    palette.setColor(QtGui.QPalette.Link, QtGui.QColor(NORD_ACCENT))

    # Disabled state
    disabled_text = QtGui.QColor(NORD_TEXT_MUTED)
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, disabled_text)
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, disabled_text)

    app.setPalette(palette)

    # Global stylesheet for finer control
    app.setStyleSheet(f"""
        QWidget {{
            background-color: {NORD_BG};
            color: {NORD_TEXT};
            font-size: 10pt;
        }}

        /* Playlist list */
        QListWidget {{
            background-color: {NORD_SURFACE};
            border: 1px solid {NORD_BORDER};
            border-radius: 4px;
        }}
        QListWidget::item {{
            padding: 4px 8px;
        }}
        QListWidget::item:selected {{
            background-color: {NORD_ACCENT};
            color: {NORD_BG};
        }}
        QListWidget::item:hover {{
            background-color: {NORD_SURFACE_ALT};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {NORD_SURFACE};
            border: 1px solid {NORD_BORDER};
            border-radius: 4px;
            padding: 4px 12px;
        }}
        QPushButton:hover:!disabled {{
            background-color: {NORD_SURFACE_ALT};
        }}
        QPushButton:pressed {{
            background-color: {NORD_BORDER};
        }}
        QPushButton:disabled {{
            color: {NORD_TEXT_MUTED};
            border-color: {NORD_SURFACE};
        }}

        /* Menu bar */
        QMenuBar {{
            background-color: {NORD_BG};
            border-bottom: 1px solid {NORD_BORDER};
        }}
        QMenuBar::item {{
            padding: 3px 8px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: {NORD_SURFACE};
        }}

        /* Menus */
        QMenu {{
            background-color: {NORD_SURFACE};
            border: 1px solid {NORD_BORDER};
        }}
        QMenu::item {{
            padding: 4px 18px 4px 24px;
        }}
        QMenu::item:selected {{
            background-color: {NORD_ACCENT};
            color: {NORD_BG};
        }}

        /* Section header label (Playlist) */
        QLabel#sectionLabel {{
            font-weight: bold;
            color: {NORD_HEADER};
        }}

        /* Status label styling */
        QLabel#statusLabel {{
            color: {NORD_TEXT_MUTED};
            font-style: italic;
        }}
    """)

# ==========================
#  Macro Builder
# ==========================

def build_macro_from_midi(midi_path: str):
    tmp_dir = tempfile.mkdtemp(prefix="winds_gui_")

    base = os.path.splitext(os.path.basename(midi_path))[0]
    raw_csv = os.path.join(tmp_dir, base + "_raw.csv")
    transposed_csv = os.path.join(tmp_dir, base + "_transposed.csv")

    midi_to_csv(midi_path, raw_csv)

    process_file(
        raw_csv,
        transposed_csv,
        window_min=WINDOW_MIN_PITCH,
        window_max=WINDOW_MAX_PITCH,
    )

    macro = csv_to_keystroke_macro(transposed_csv)
    return macro


# ==========================
#  Macro Playback
# ==========================

def play_macro(macro, stop_event: threading.Event):
    if not macro:
        print("Macro is empty.")
        return

    start = time.time()
    for event in macro:
        if stop_event.is_set():
            break

        delay = event["time"] - (time.time() - start)
        if delay > 0:
            if stop_event.wait(delay):
                break

        if stop_event.is_set():
            break

        keyboard.send(event["key"])


# ==========================
#  Main Window
# ==========================

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Aiye's Instrument Player - Where Winds Meet")
        self.setMinimumSize(600, 370)

        # State
        self.current_midi_path = None
        self.current_macro = None
        self.macro_cache = {}
        self.play_thread = None
        self.stop_event = threading.Event()
        self.playlist_mode = False

        # === LAYOUT ROOT ===
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(8)

        # === MENUBAR ===
        menubar = QtWidgets.QMenuBar()
        layout.setMenuBar(menubar)

        # File menu (Save/Load playlist)
        file_menu = menubar.addMenu("File")

        act_save = QtWidgets.QAction("Save Playlist…", self)
        act_save.triggered.connect(self.save_playlist)
        file_menu.addAction(act_save)

        act_load = QtWidgets.QAction("Load Playlist…", self)
        act_load.triggered.connect(self.load_playlist)
        file_menu.addAction(act_load)

        # Help menu (Instructions)
        help_menu = menubar.addMenu("Help")
        act_instructions = QtWidgets.QAction("Instructions", self)
        act_instructions.triggered.connect(self.show_instructions)
        help_menu.addAction(act_instructions)

        # === PLAYLIST ===
        # playlist_label = QtWidgets.QLabel("Playlist")
        # playlist_label.setStyleSheet("font-weight: bold;")
        #
        # self.playlist = QtWidgets.QListWidget()

        # playlist_label = QtWidgets.QLabel("Playlist")
        # playlist_label.setObjectName("sectionLabel")
        #
        # self.playlist.itemSelectionChanged.connect(self.on_playlist_selection_changed)
        # self.playlist.itemDoubleClicked.connect(self.on_playlist_item_double_clicked)
        #
        # # Allow click+drag reordering
        # self.playlist.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # self.playlist.setDefaultDropAction(QtCore.Qt.MoveAction)
        #
        # # Right-click context menu
        # self.playlist.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self.playlist.customContextMenuRequested.connect(
        #     self.show_playlist_context_menu
        # )
        # === PLAYLIST ===
        playlist_label = QtWidgets.QLabel("Playlist")
        playlist_label.setObjectName("sectionLabel")

        self.playlist = QtWidgets.QListWidget()
        self.playlist.itemSelectionChanged.connect(self.on_playlist_selection_changed)
        self.playlist.itemDoubleClicked.connect(self.on_playlist_item_double_clicked)

        # Allow click+drag reordering
        self.playlist.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.playlist.setDefaultDropAction(QtCore.Qt.MoveAction)

        # Right-click context menu
        self.playlist.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.playlist.customContextMenuRequested.connect(self.show_playlist_context_menu)

        # === STATUS AREA ===
        self.file_label = QtWidgets.QLabel("No MIDI loaded.")
        self.file_label.setWordWrap(True)

        # self.status_label = QtWidgets.QLabel("Ready.")
        # self.status_label.setStyleSheet("color: #555;")
        self.status_label = QtWidgets.QLabel("Ready.")
        self.status_label.setObjectName("statusLabel")


        # === BUTTONS ===
        self.open_button = QtWidgets.QPushButton("Open MIDI…")
        self.open_button.clicked.connect(self.on_open_clicked)

        self.play_button = QtWidgets.QPushButton("Play")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.on_play_clicked)

        self.play_playlist_button = QtWidgets.QPushButton("Play Playlist")
        self.play_playlist_button.setEnabled(False)
        self.play_playlist_button.clicked.connect(self.on_play_playlist_clicked)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_stop_clicked)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.open_button)
        button_row.addStretch()
        button_row.addWidget(self.play_button)
        button_row.addWidget(self.play_playlist_button)
        button_row.addWidget(self.stop_button)

        # === BUILD LAYOUT ===
        layout.addWidget(playlist_label)
        layout.addWidget(self.playlist)
        layout.addWidget(self.file_label)
        layout.addWidget(self.status_label)
        layout.addLayout(button_row)

        # === GLOBAL PANIC HOTKEY ===
        keyboard.add_hotkey(STOP_HOTKEY, self._on_global_hotkey)

    # ==========================
    #  Instructions Popup
    # ==========================

    def show_instructions(self):
        QtWidgets.QMessageBox.information(
            self,
            "Instructions",
            (
                "Play: plays just the currently loaded song.\n"
                "Play Playlist: plays all from the selected song through to the end.\n"
                f"Stop / {STOP_HOTKEY}: interrupts the current song and cancels the rest of the playlist.\n"
                f"After hitting play, you have {SLEEP_TIME} seconds to switch to your WWM client before keystrokes begin playing.\n"
                f"{STOP_HOTKEY} stops keystroke play even within WWM.\n"
                "THIS PROGRAM MUST BE RUN IN ADMINISTRATOR MODE FOR KEYSTROKES TO FUNCTION IN WWM."
            ),
        )

    # ==========================
    #  Playlist Context Menu
    # ==========================

    def show_playlist_context_menu(self, pos: QtCore.QPoint):
        item = self.playlist.itemAt(pos)
        if not item:
            return

        menu = QtWidgets.QMenu(self)
        remove_action = menu.addAction("Remove track")

        chosen = menu.exec_(self.playlist.mapToGlobal(pos))
        if chosen is not remove_action:
            return

        row = self.playlist.row(item)
        path = item.data(QtCore.Qt.UserRole)

        # Remove from widget
        self.playlist.takeItem(row)

        # Drop cached macro
        if path in self.macro_cache:
            del self.macro_cache[path]

        # If it was the current track, clear state
        if self.current_midi_path == path:
            self.current_midi_path = None
            self.current_macro = None
            self.stop_playback()
            self.file_label.setText("No MIDI loaded.")
            self.status_label.setText("Ready.")
            self.play_button.setEnabled(False)

        # Adjust playlist button
        if self.playlist.count() == 0:
            self.play_playlist_button.setEnabled(False)
        else:
            new_row = min(row, self.playlist.count() - 1)
            if new_row >= 0:
                self.playlist.setCurrentRow(new_row)

    # ==========================
    #  Save / Load Playlist
    # ==========================

    def save_playlist(self):
        if self.playlist.count() == 0:
            QtWidgets.QMessageBox.information(
                self,
                "Save Playlist",
                "There are no tracks in the playlist to save.",
            )
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Playlist",
            "",
            "Playlists (*.json)",
        )
        if not path:
            return

        # Make sure it ends with .json (optional nicety)
        if not path.lower().endswith(".json"):
            path += ".json"

        entries = []
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            p = item.data(QtCore.Qt.UserRole)
            entries.append(p)

        data = {"tracks": entries}

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error Saving Playlist",
                f"Could not save playlist:\n\n{e}",
            )
            return

        self.status_label.setText(f"Playlist saved to: {path}")

    def load_playlist(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Playlist",
            "",
            "Playlists (*.json)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error Loading Playlist",
                f"Could not load playlist:\n\n{e}",
            )
            return

        tracks = data.get("tracks", [])
        if not isinstance(tracks, list):
            QtWidgets.QMessageBox.critical(
                self,
                "Error Loading Playlist",
                "Playlist file format is invalid.",
            )
            return

        # Stop current playback & clear existing state
        self.stop_playback()
        self.playlist.clear()
        self.macro_cache.clear()
        self.current_midi_path = None
        self.current_macro = None
        self.play_button.setEnabled(False)
        self.play_playlist_button.setEnabled(False)
        self.file_label.setText("No MIDI loaded.")
        self.status_label.setText("Loaded playlist (processing tracks on demand).")

        missing = []
        first_valid = True
        for p in tracks:
            if not isinstance(p, str):
                continue
            if not os.path.isfile(p):
                missing.append(p)
                continue
            # Reuse existing helper; this will also select the last added track
            self.add_to_playlist(p, auto_select=first_valid)
            first_valid = False

        if missing:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Files",
                "Some files in the playlist could not be found:\n\n"
                + "\n".join(missing),
            )

    # ==========================
    #  Playlist Helpers
    # ==========================

    def add_to_playlist(self, path: str, auto_select: bool = True):
        path = os.path.abspath(path)

        # Avoid duplicates
        for i in range(self.playlist.count()):
            existing = self.playlist.item(i)
            if existing.data(QtCore.Qt.UserRole) == path:
                if auto_select:
                    self.playlist.setCurrentRow(i)
                return

        item = QtWidgets.QListWidgetItem(os.path.basename(path))
        item.setToolTip(path)
        item.setData(QtCore.Qt.UserRole, path)
        self.playlist.addItem(item)

        if auto_select:
            self.playlist.setCurrentItem(item)

        if self.playlist.count() > 0:
            self.play_playlist_button.setEnabled(True)

    def on_open_clicked(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select MIDI files",
            "",
            "MIDI Files (*.mid *.midi)",
        )
        if not paths:
            return

        first = True
        for p in paths:
            self.add_to_playlist(p, auto_select=first)
            first = False

    def on_playlist_selection_changed(self):
        item = self.playlist.currentItem()
        if item:
            self.load_midi(item.data(QtCore.Qt.UserRole))

    def on_playlist_item_double_clicked(self, item):
        self.load_midi(item.data(QtCore.Qt.UserRole))
        self.on_play_clicked()

    # ==========================
    #  Load + Build Macro
    # ==========================

    def load_midi(self, path):
        self.stop_playback()

        self.current_midi_path = path
        self.file_label.setText(f"Loaded: {path}")

        # Cached?
        if path in self.macro_cache:
            self.current_macro = self.macro_cache[path]
            if self.current_macro:
                self.play_button.setEnabled(True)
            self.status_label.setText("Ready (cached).")
            return

        # Build in background
        self.status_label.setText("Processing MIDI…")
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        def worker():
            try:
                macro = build_macro_from_midi(path)
            except Exception as e:
                traceback.print_exc()
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "_load_failed",
                    QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(str, str(e)),
                )
                return

            QtCore.QMetaObject.invokeMethod(
                self,
                "_load_success",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(object, macro),
            )

        threading.Thread(target=worker, daemon=True).start()

    @QtCore.pyqtSlot(object)
    def _load_success(self, macro):
        self.macro_cache[self.current_midi_path] = macro
        self.current_macro = macro
        self.play_button.setEnabled(bool(macro))
        if macro:
            self.status_label.setText("Ready.")
        else:
            self.status_label.setText(
                "This MIDI produced an empty macro (no playable notes in range)."
            )

    @QtCore.pyqtSlot(str)
    def _load_failed(self, msg):
        self.status_label.setText("Error loading MIDI.")
        QtWidgets.QMessageBox.critical(self, "Error", msg)

    # ==========================
    #  Playback: Single Track
    # ==========================

    def on_play_clicked(self):
        if not self.current_macro:
            return
        if self.play_thread and self.play_thread.is_alive():
            return

        time.sleep(SLEEP_TIME)
        self.playlist_mode = False
        self.status_label.setText(f"Playing… ({STOP_HOTKEY} to stop)")
        self.stop_event.clear()
        self.stop_button.setEnabled(True)
        self.play_button.setEnabled(False)
        self.play_playlist_button.setEnabled(False)

        def worker():
            play_macro(self.current_macro, self.stop_event)
            QtCore.QMetaObject.invokeMethod(
                self, "_playback_done", QtCore.Qt.QueuedConnection
            )

        self.play_thread = threading.Thread(target=worker, daemon=True)
        self.play_thread.start()

    # ==========================
    #  Playback: Playlist
    # ==========================

    def on_play_playlist_clicked(self):
        if self.playlist.count() == 0:
            return
        if self.play_thread and self.play_thread.is_alive():
            return

        time.sleep(SLEEP_TIME)
        self.playlist_mode = True
        start_row = self.playlist.currentRow()
        if start_row < 0:
            start_row = 0

        self.status_label.setText(f"Playing playlist… ({STOP_HOTKEY} to stop)")
        self.stop_event.clear()
        self.stop_button.setEnabled(True)
        self.play_button.setEnabled(False)
        self.play_playlist_button.setEnabled(False)

        def worker():
            self._playlist_worker(start_row)
            QtCore.QMetaObject.invokeMethod(
                self, "_playback_done", QtCore.Qt.QueuedConnection
            )

        self.play_thread = threading.Thread(target=worker, daemon=True)
        self.play_thread.start()

    def _playlist_worker(self, start_index):
        count = self.playlist.count()
        for i in range(start_index, count):
            if self.stop_event.is_set():
                return

            item = self.playlist.item(i)
            if not item:
                continue
            path = item.data(QtCore.Qt.UserRole)

            # Get or build macro
            if path in self.macro_cache:
                macro = self.macro_cache[path]
            else:
                try:
                    macro = build_macro_from_midi(path)
                    self.macro_cache[path] = macro
                except (Exception,):
                    continue

            self.current_midi_path = path
            self.current_macro = macro

            QtCore.QMetaObject.invokeMethod(
                self,
                "_set_now_playing",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(int, i),
                QtCore.Q_ARG(str, path),
            )

            play_macro(macro, self.stop_event)
            if self.stop_event.is_set():
                return

            if i < count - 1:
                if self.stop_event.wait(PLAYLIST_GAP_SECONDS):
                    return

    # @QtCore.pyqtSlot(int, str)
    # def _set_now_playing(self, row: int, path: str):
    #     if 0 <= row < self.playlist.count():
    #         self.playlist.setCurrentRow(row)
    #     self.file_label.setText(f"Playing: {path}")
    #     self.status_label.setText("Playing playlist…")
    @QtCore.pyqtSlot(int, str)
    def _set_now_playing(self, row: int, path: str):
        if 0 <= row < self.playlist.count():
            # Prevent selectionChanged from firing while we move the row programmatically
            self.playlist.blockSignals(True)
            self.playlist.setCurrentRow(row)
            self.playlist.blockSignals(False)

        self.file_label.setText(f"Playing: {path}")
        self.status_label.setText(f"Playing playlist… ({STOP_HOTKEY} to stop)")

    # ==========================
    #  Playback Finished
    # ==========================

    @QtCore.pyqtSlot()
    def _playback_done(self):
        self.stop_button.setEnabled(False)

        if self.current_macro:
            self.play_button.setEnabled(True)
        else:
            self.play_button.setEnabled(False)

        if self.playlist.count() > 0:
            self.play_playlist_button.setEnabled(True)
        else:
            self.play_playlist_button.setEnabled(False)

        if self.playlist_mode:
            self.status_label.setText("Playlist finished or stopped.")
        else:
            self.status_label.setText("Ready.")

        self.playlist_mode = False

    # ==========================
    #  Stop / Panic Hotkey
    # ==========================

    def on_stop_clicked(self):
        self.stop_playback()
        self.status_label.setText("Stopped.")

    def stop_playback(self):
        if self.play_thread and self.play_thread.is_alive():
            self.stop_event.set()
            self.play_thread.join(timeout=1.0)

        self.stop_button.setEnabled(False)
        if self.playlist.count() > 0:
            self.play_playlist_button.setEnabled(True)
        if self.current_macro:
            self.play_button.setEnabled(True)

    def _on_global_hotkey(self):
        QtCore.QMetaObject.invokeMethod(
            self, "_global_stop", QtCore.Qt.QueuedConnection
        )

    @QtCore.pyqtSlot()
    def _global_stop(self):
        if self.play_thread and self.play_thread.is_alive():
            self.stop_playback()
            self.status_label.setText(f"Stopped via {STOP_HOTKEY}.")

    # ==========================
    #  Close Event
    # ==========================

    def closeEvent(self, event):
        self.stop_playback()
        event.accept()


# ==========================
#  Main
# ==========================

# def main():
#     app = QtWidgets.QApplication(sys.argv)
#     w = MainWindow()
#     w.show()
#     sys.exit(app.exec_())

# def main():
#     app = QtWidgets.QApplication(sys.argv)
#
#     # Apply dark Nord theme before creating any windows
#     apply_nord_theme(app)
#
#     w = MainWindow()
#     w.show()
#     sys.exit(app.exec_())
# def main():
#     app = QtWidgets.QApplication(sys.argv)
#
#     # Apply dark Nord theme before creating any windows
#     apply_nord_theme(app)
#
#     w = MainWindow()
#
#     # Try to make the native title bar dark on Windows
#     enable_windows_dark_titlebar(w)
#
#     w.show()
#     sys.exit(app.exec_())

# def main():
#     app = QtWidgets.QApplication(sys.argv)
#
#     # Apply dark Nord theme before creating any windows
#     apply_nord_theme(app)
#
#     # Set app/window icon
#     app.setWindowIcon(QtGui.QIcon(resource_path("music-therapy.ico")))
#
#     w = MainWindow()
#
#     # Try to make the native title bar dark on Windows
#     enable_windows_dark_titlebar(w)
#
#     w.show()
#     sys.exit(app.exec_())
#
# if __name__ == "__main__":
#     main()

# def main():
#     app = QtWidgets.QApplication(sys.argv)
#
#     # Apply dark Nord theme before creating any windows
#     apply_nord_theme(app)
#
#     # Set app/window icon (using your resource_path helper)
#     icon_path = resource_path("music-therapy.ico")
#     app.setWindowIcon(QtGui.QIcon(icon_path))
#
#     w = MainWindow()
#
#     # Try to make the native title bar dark on Windows
#     enable_windows_dark_titlebar(w)
#
#     # (Optional but nice) also set the window-specific icon:
#     w.setWindowIcon(QtGui.QIcon(icon_path))
#
#     w.show()
#     sys.exit(app.exec_())
def main():
    app = QtWidgets.QApplication(sys.argv)

    # Apply dark Nord theme before creating any windows
    apply_nord_theme(app)

    # Use the .ico and resource_path
    icon_path = resource_path("music-therapy.ico")
    app.setWindowIcon(QtGui.QIcon(icon_path))

    w = MainWindow()

    # Try to make the native title bar dark on Windows
    enable_windows_dark_titlebar(w)

    # Explicitly set the window icon too
    w.setWindowIcon(QtGui.QIcon(icon_path))

    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
     main()
## python "C:\Users\miria\PycharmProjects\MIDIMacroEfforts\wind_instrument_gui.py"

## TO PACKAGE
# cd path\to\your\project
# cd C:\Users\miria\PycharmProjects\MIDIMacroEfforts\
#
# Then run this EXACT command in pycharm terminal
#

# python -m PyInstaller --onefile --noconsole --icon "music-therapy.ico" --add-data "music-therapy.ico;." --hidden-import PyQt5 --hidden-import PyQt5.QtCore --hidden-import PyQt5.QtGui --hidden-import PyQt5.QtWidgets --collect-all PyQt5 wind_instrument_gui.py
