import ctypes
import json
import os
import platform
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import keyboard  # global key sender
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg

# --- Your existing tools ---
from midi_tools.io_midicsv import midi_to_csv
from midi_tools.macro import csv_to_keystroke_macro
from midi_tools.pipeline import process_file

if platform.system() == "Windows":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("aiyes.instrument.player")

# ==========================
#  CONFIG
# ==========================

def resource_path(relative_name: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS  # type: ignore[attr-defined]
    elif getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, relative_name)

def create_play_icon(size: int = 60) -> QtGui.QIcon:
    """Create a play icon using SVG."""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512">
    <path d="M361 215C375.3 223.8 384 239.3 384 256C384 272.7 375.3 288.2 361 296.1L73.03 472.1C58.21 482 39.51 482.4 24.65 473.9C9.694 465.4 0 449.4 0 432V80C0 62.64 9.694 46.63 24.65 38.13C39.51 29.64 58.21 29.99 73.03 39.04L361 215z" fill="black"/>
    </svg>'''
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode()))
    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QtGui.QIcon(pixmap)

def create_pause_icon(size: int = 60) -> QtGui.QIcon:
    """Create a pause icon using SVG."""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512">
    <path d="M287.1 447.1c17.67 0 31.1-14.33 31.1-32V96.03c0-17.67-14.33-32-32-32c-17.67 0-31.1 14.33-31.1 32v319.1C255.1 433.6 270.3 447.1 287.1 447.1zM52.51 447.1c17.67 0 31.1-14.33 31.1-32V96.03c0-17.67-14.33-32-32-32C34.84 64.03 20.5 78.35 20.5 96.03v319.1C20.5 433.6 34.84 447.1 52.51 447.1z" fill="black"/>
    </svg>'''
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode()))
    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QtGui.QIcon(pixmap)

class NumericTableItem(QtWidgets.QTableWidgetItem):
    """Custom table item that sorts numerically instead of alphabetically."""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except (ValueError, TypeError):
            return self.text() < other.text()

class LoadingIndicator(QtWidgets.QWidget):
    """Loading indicator widget with animated text."""
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(resource_path("Player.ico")))
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # Loading label
        self.label = QtWidgets.QLabel("Loading...")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setStyleSheet("color: #2ECC71; font-size: 10pt; font-weight: bold;")
        self.label.setFixedHeight(16)
        
        # Loading bar with padding
        bar_container = QtWidgets.QHBoxLayout()
        bar_container.setContentsMargins(15, 0, 15, 0)
        
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate progress
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        
        bar_container.addWidget(self.progress)
        
        layout.addWidget(self.label)
        layout.addLayout(bar_container)

STOP_HOTKEY = "F11"
SLEEP_TIME = 0.5

WINDOW_MIN_PITCH = 48
WINDOW_MAX_PITCH = 83
PLAYLIST_GAP_SECONDS = 5.0

# Playlist persistence - save to exe directory (not temporary _MEIPASS)
def get_playlist_file():
    if getattr(sys, "frozen", False):
        # When frozen as exe, save to the exe's directory (not temporary _MEIPASS)
        base_dir = os.path.dirname(sys.executable)
    else:
        # When running as script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "playlist.json")

PLAYLIST_FILE = get_playlist_file()

# ==========================
#  Nord Color Theme with Green/Black
# ==========================

# Nord palette colors
NORD_BG = "#1A1A1A"          # main window background - darker black
NORD_SURFACE = "#2D2D2D"     # panels / controls - dark gray
NORD_SURFACE_ALT = "#3A3A3A" # hover / subtle contrast
NORD_BORDER = "#4A4A4A"      # borders - gray

NORD_TEXT = "#ECEFF4"
NORD_TEXT_MUTED = "#D8DEE9"
NORD_HEADER = "#E5E9F0"

NORD_ACCENT = "#2ECC71"      # primary accent - green
NORD_ACCENT_POS = "#27AE60"  # positive action - darker green
NORD_ERROR = "#BF616A"
NORD_WARNING = "#EBCB8B"

def enable_windows_dark_titlebar(window: QtWidgets.QWidget):
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
            padding: 6px 12px;
            color: {NORD_TEXT};
            font-weight: bold;
        }}
        QPushButton:hover:!disabled {{
            background-color: {NORD_SURFACE_ALT};
            border: 1px solid {NORD_ACCENT};
        }}
        QPushButton:pressed {{
            background-color: {NORD_ACCENT_POS};
            color: white;
        }}
        QPushButton:disabled {{
            color: {NORD_TEXT_MUTED};
            border-color: {NORD_SURFACE};
        }}
        
        /* Music player buttons special styling */
        #playButton, #stopButton {{
            background-color: {NORD_ACCENT};
            color: black;
            border: 2px solid {NORD_ACCENT_POS};
            font-size: 24pt;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
            min-width: 45px;
            min-height: 45px;
            max-width: 45px;
            max-height: 45px;
            border-radius: 22px;
        }}
        #playButton:hover, #stopButton:hover {{
            background-color: {NORD_ACCENT_POS};
            color: white;
            border: 2px solid white;
            box-shadow: 0 0 10px rgba(46, 204, 113, 0.5);
        }}
        #playButton:pressed, #stopButton:pressed {{
            background-color: {NORD_ACCENT_POS};
            color: white;
            border: 2px solid white;
        }}
        #playButton:disabled {{
            background-color: {NORD_ACCENT};
            color: black;
            border: 2px solid {NORD_ACCENT_POS};
            opacity: 0.5;
        }}
        #prevButton, #nextButton, #playPlaylistButton {{
            background-color: transparent;
            color: {NORD_ACCENT};
            border: none;
            font-size: 12pt;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
            min-width: 40px;
            min-height: 40px;
            max-width: 40px;
            max-height: 40px;
            border-radius: 20px;
        }}
        #prevButton:hover, #nextButton:hover {{
            color: {NORD_ACCENT_POS};
            font-size: 16pt;
        }}
        #prevButton:pressed, #nextButton:pressed, #playPlaylistButton:pressed {{
            background-color: transparent;
            color: {NORD_ACCENT_POS};
            font-size: 16pt;
        }}
        #prevButton:disabled, #nextButton:disabled {{
            color: {NORD_ACCENT};
            opacity: 0.5;
        }}
        #playPlaylistButton:hover {{
            background-color: {NORD_ACCENT_POS};
            color: white;
            border: 2px solid white;
        }}
        
        /* Progress bar styling */
        QProgressBar {{
            border: 1px solid {NORD_BORDER};
            border-radius: 3px;
            background-color: {NORD_SURFACE};
        }}
        QProgressBar::chunk {{
            background-color: {NORD_ACCENT};
            border-radius: 2px;
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

def extract_bpm_from_midi(midi_path: str) -> int:
    """Extract BPM (tempo) from MIDI file."""
    try:
        try:
            import mido
        except ImportError:
            print(f"[BPM] mido not installed, skipping BPM extraction for {midi_path}")
            return 0
        
        mid = mido.MidiFile(midi_path)
        for msg in mid.tracks[0]:
            if msg.type == 'set_tempo':
                # Convert microseconds per beat to BPM
                bpm = int(60_000_000 / msg.tempo)
                print(f"[BPM] Extracted BPM {bpm} from {midi_path}")
                return bpm
        # Default to 120 if no tempo found
        print(f"[BPM] No tempo found in {midi_path}, using default 120")
        return 120
    except Exception as e:
        print(f"[BPM] Error extracting BPM from {midi_path}: {e}")
        return 0  # Return 0 if unable to extract


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

def play_macro(macro, stop_event: threading.Event, progress_callback=None):
    if not macro:
        print("Macro is empty.")
        return

    print(f"[DEBUG] play_macro called with {len(macro)} events, total duration: {macro[-1]['time']}")
    # Calculate total duration from the last event
    total_duration = macro[-1]["time"] if macro else 0
    
    start = time.time()
    for i, event in enumerate(macro):
        if stop_event.is_set():
            print(f"[DEBUG] Stopped at event {i}")
            break

        delay = event["time"] - (time.time() - start)
        if delay > 0:
            if stop_event.wait(delay):
                print(f"[DEBUG] Stopped while waiting at event {i}")
                break

        if stop_event.is_set():
            break

        print(f"[DEBUG] Sending key: {event['key']} at time {event['time']}")
        keyboard.send(event["key"])
        
        # Update progress bar with elapsed time and total duration
        if progress_callback:
            elapsed = time.time() - start
            progress = int((i + 1) / len(macro) * 1000)  # Range 0-1000
            progress_callback(progress, elapsed, total_duration)


# ==========================
#  Main Window
# ==========================

class MainWindow(QtWidgets.QWidget):
    # Signal for progress updates (can be emitted from worker threads)
    progress_updated = QtCore.pyqtSignal(int, float, float)  # progress, elapsed, total_duration
    duration_loaded = QtCore.pyqtSignal(str, float)  # path, duration - for updating playlist as macros load
    bpm_loaded = QtCore.pyqtSignal(str, int)  # path, bpm - for updating BPM column
    
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
        self.is_paused = False  # Track pause state
        self.current_song_duration = 0  # Store current song duration
        self.macro_loader_pool = ThreadPoolExecutor(max_workers=3)  # Load up to 3 macros in parallel
        self.macros_loading = 0  # Track number of macros currently loading
        self.macros_loading_lock = threading.Lock()  # Thread-safe counter
        
        # Connect progress signal to progress bar
        self.progress_updated.connect(self._on_progress_updated)
        # Connect duration loading signal
        self.duration_loaded.connect(self._on_duration_loaded)
        # Connect BPM loading signal
        self.bpm_loaded.connect(self._on_bpm_loaded)

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
        playlist_label = QtWidgets.QLabel("Playlist")
        playlist_label.setObjectName("sectionLabel")

        self.playlist = QtWidgets.QTableWidget()
        self.playlist.setColumnCount(3)
        self.playlist.setHorizontalHeaderLabels(["Song Name", "Duration", "BPM"])
        self.playlist.horizontalHeader().setStretchLastSection(False)
        # Make column 0 (Song Name) stretchable and wider
        self.playlist.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        # Make columns 1 and 2 resizable
        self.playlist.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.playlist.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)
        # Set minimum widths for Duration and BPM columns
        self.playlist.setColumnWidth(1, 80)
        self.playlist.setColumnWidth(2, 60)
        self.playlist.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.playlist.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        # Enable sorting by clicking column headers
        self.playlist.horizontalHeader().setSectionsClickable(True)
        self.playlist.setSortingEnabled(True)
        
        self.playlist.selectionModel().selectionChanged.connect(self.on_playlist_selection_changed)
        self.playlist.cellDoubleClicked.connect(self.on_playlist_item_double_clicked)

        # Allow drag-drop for quick loading
        self.playlist.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.playlist.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.playlist.setAcceptDrops(True)

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

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)   # smoother than 0–100
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)

        # Time labels for music player style
        self.time_label = QtWidgets.QLabel("0:00")
        self.time_label.setFixedWidth(50)
        self.time_label.setAlignment(QtCore.Qt.AlignRight)
        
        self.duration_label = QtWidgets.QLabel("0:00")
        self.duration_label.setFixedWidth(50)
        self.duration_label.setAlignment(QtCore.Qt.AlignLeft)
        
        # Progress bar layout (time - bar - duration)
        progress_layout = QtWidgets.QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.duration_label)

        # === BUTTONS ===
        # Open button at top
        self.open_button = QtWidgets.QPushButton("📁 Open MIDI")
        self.open_button.setFixedWidth(130)
        self.open_button.clicked.connect(self.on_open_clicked)
        
        # Save button at top
        self.save_button = QtWidgets.QPushButton("💾 Save")
        self.save_button.setFixedWidth(100)
        self.save_button.clicked.connect(self._save_playlist_to_file)

        # Music player control buttons - icons only
        self.prev_button = QtWidgets.QPushButton("◄◄")
        self.prev_button.setObjectName("prevButton")
        self.prev_button.setEnabled(False)
        self.prev_button.setFixedSize(40, 40)
        self.prev_button.clicked.connect(self.on_prev_clicked)
        
        self.play_button = QtWidgets.QPushButton()
        self.play_button.setIcon(create_play_icon(30))
        self.play_button.setIconSize(QtCore.QSize(24, 24))
        self.play_button.setObjectName("playButton")
        self.play_button.setEnabled(False)
        self.play_button.setFixedSize(45, 45)
        self.play_button.setFlat(True)
        self.play_button.clicked.connect(self.on_play_clicked)

        self.next_button = QtWidgets.QPushButton("►►")
        self.next_button.setObjectName("nextButton")
        self.next_button.setEnabled(False)
        self.next_button.setFixedSize(40, 40)
        self.next_button.clicked.connect(self.on_next_clicked)

        self.play_playlist_button = QtWidgets.QPushButton("Play Playlist")
        self.play_playlist_button.setObjectName("playPlaylistButton")
        self.play_playlist_button.setEnabled(False)
        self.play_playlist_button.clicked.connect(self.on_play_playlist_clicked)

        self.stop_button = QtWidgets.QPushButton("⏹ Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_stop_clicked)

        # Music player style button row - centered (just play controls)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.prev_button)
        button_row.addWidget(self.play_button)
        button_row.addWidget(self.next_button)
        button_row.addStretch()
        
        # Center the buttons
        button_container = QtWidgets.QWidget()
        button_container.setLayout(button_row)
        
        # Create loading indicator
        self.loading_indicator = LoadingIndicator()
        
        # Create stacked widget to switch between loading and buttons
        self.button_stack = QtWidgets.QStackedWidget()
        self.button_stack.addWidget(self.loading_indicator)
        self.button_stack.addWidget(button_container)
        self.button_stack.setCurrentWidget(self.loading_indicator)
        # Don't let stacked widget expand vertically
        self.button_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.button_stack.setFixedHeight(60)

        # === BUILD LAYOUT ===
        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(self.open_button)
        top_row.addWidget(self.save_button)
        top_row.addStretch()
        
        layout.addLayout(top_row)
        layout.addWidget(self.playlist)
        layout.addLayout(progress_layout)
        layout.addWidget(self.button_stack)

        # === GLOBAL PANIC HOTKEY ===
        keyboard.add_hotkey(STOP_HOTKEY, self._on_global_hotkey)
        
        # === LOAD SAVED PLAYLIST ===
        self.load_playlist_from_file()
        
        # === POSITION ON SECOND MONITOR (right split) ===
        self._position_on_secondary_monitor()

    def _position_on_secondary_monitor(self):
        """Position window on secondary monitor (right split) at half width if available."""
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        
        screens = app.screens()
        if len(screens) < 2:
            # No secondary monitor, position on primary at half width
            primary_screen = screens[0]
            screen_geometry = primary_screen.geometry()
            window_width = screen_geometry.width() // 2
            window_height = int(screen_geometry.height() * 0.85)  # 85% of height for titlebar visibility
            x = screen_geometry.left()
            y = screen_geometry.top() + 50  # Add top margin to show toolbar
            self.setGeometry(x, y, window_width, window_height)
            self.show()
            return
        
        # Get secondary (right) monitor
        secondary_screen = screens[1]
        screen_geometry = secondary_screen.geometry()
        
        # Position window at half width on secondary monitor
        window_width = screen_geometry.width() // 2
        window_height = int(screen_geometry.height() * 0.85)  # 85% of height for titlebar visibility
        
        # Right side of monitor at half width, with top margin to show toolbar
        x = screen_geometry.right() - window_width
        y = screen_geometry.top() + 50
        
        self.setGeometry(x, y, window_width, window_height)
        self.show()

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
        path_item = self.playlist.item(row, 0)
        path = path_item.data(QtCore.Qt.UserRole) if path_item else None
        
        if not path:
            return

        # Remove from widget
        self.playlist.removeRow(row)

        # Drop cached macro
        if path in self.macro_cache:
            del self.macro_cache[path]

        # If it was the current track, clear state
        if self.current_midi_path == path:
            self.current_midi_path = None
            self.current_macro = None
            self.stop_playback()
            self.play_button.setEnabled(False)

        # Adjust playlist button
        if self.playlist.rowCount() == 0:
            self.play_playlist_button.setEnabled(False)
        else:
            new_row = min(row, self.playlist.rowCount() - 1)
            if new_row >= 0:
                self.playlist.setCurrentCell(new_row, 0)

    # ==========================
    #  Save / Load Playlist
    # ==========================

    def save_playlist(self):
        if self.playlist.rowCount() == 0:
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
        for i in range(self.playlist.rowCount()):
            item = self.playlist.item(i, 0)
            p = item.data(QtCore.Qt.UserRole) if item else None
            if p:
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
        self.file_label.setText("")
        self.status_label.setText("Ready.")

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
        for i in range(self.playlist.rowCount()):
            item = self.playlist.item(i, 0)
            if item and item.data(QtCore.Qt.UserRole) == path:
                if auto_select:
                    self.playlist.selectRow(i)
                return

        # Add row to table immediately (without waiting for macro to load)
        row_pos = self.playlist.rowCount()
        self.playlist.insertRow(row_pos)
        
        # Column 0: Song name
        name_item = QtWidgets.QTableWidgetItem(os.path.basename(path))
        name_item.setToolTip(path)
        name_item.setData(QtCore.Qt.UserRole, path)
        name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.playlist.setItem(row_pos, 0, name_item)
        
        # Column 1: Duration - show loading initially
        duration_item = QtWidgets.QTableWidgetItem("Loading...")
        duration_item.setFlags(duration_item.flags() & ~QtCore.Qt.ItemIsEditable)
        duration_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.playlist.setItem(row_pos, 1, duration_item)
        
        # Column 2: BPM (empty for now)
        bpm_item = NumericTableItem("")
        bpm_item.setFlags(bpm_item.flags() & ~QtCore.Qt.ItemIsEditable)
        bpm_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.playlist.setItem(row_pos, 2, bpm_item)
        
        # Load macro and BPM in background if not already cached
        if path not in self.macro_cache:
            self.macro_loader_pool.submit(self._load_macro_background, path)
        else:
            # Already cached, update duration immediately
            macro = self.macro_cache[path]
            duration = macro[-1]["time"] if macro else 0
            self.duration_loaded.emit(path, duration)

        if auto_select:
            self.playlist.selectRow(row_pos)

        if self.playlist.rowCount() > 0:
            self.play_playlist_button.setEnabled(True)
            # Update prev/next button states
            current_row = self.playlist.currentRow()
            self.prev_button.setEnabled(current_row > 0)
            self.next_button.setEnabled(current_row < self.playlist.rowCount() - 1)
    
    def _load_macro_background(self, path: str):
        """Load macro in background thread and emit signal when done."""
        # Mark as loading
        with self.macros_loading_lock:
            self.macros_loading += 1
        self._update_play_button_state()
        
        try:
            if path not in self.macro_cache:
                macro = build_macro_from_midi(path)
                self.macro_cache[path] = macro
                duration = macro[-1]["time"] if macro else 0
            else:
                macro = self.macro_cache[path]
                duration = macro[-1]["time"] if macro else 0
            
            # Extract BPM from MIDI
            bpm = extract_bpm_from_midi(path)
            
            self.duration_loaded.emit(path, duration)
            print(f"[Loader] Emitting BPM signal: path={path}, bpm={bpm}")
            self.bpm_loaded.emit(path, bpm)
        except Exception as e:
            print(f"Error loading macro for {path}: {e}")
            self.duration_loaded.emit(path, 0)
            self.bpm_loaded.emit(path, 0)
        finally:
            # Mark as done loading
            with self.macros_loading_lock:
                self.macros_loading = max(0, self.macros_loading - 1)
            self._update_play_button_state()
    
    @QtCore.pyqtSlot(str, float)
    def _on_duration_loaded(self, path: str, duration: float):
        """Update playlist with loaded duration."""
        for i in range(self.playlist.rowCount()):
            item = self.playlist.item(i, 0)
            if item and item.data(QtCore.Qt.UserRole) == path:
                duration_item = self.playlist.item(i, 1)
                duration_str = self._format_time(duration)
                duration_item.setText(duration_str)
                break

    @QtCore.pyqtSlot(str, int)
    def _on_bpm_loaded(self, path: str, bpm: int):
        """Update playlist with loaded BPM."""
        print(f"[BPM Slot] Received BPM signal: path={path}, bpm={bpm}")
        for i in range(self.playlist.rowCount()):
            item = self.playlist.item(i, 0)
            if item and item.data(QtCore.Qt.UserRole) == path:
                print(f"[BPM Slot] Found matching row {i}")
                bpm_item = self.playlist.item(i, 2)
                bpm_str = str(bpm) if bpm > 0 else ""
                bpm_item.setText(bpm_str)
                print(f"[BPM Slot] Set BPM cell text to '{bpm_str}'")
                break
        else:
            print(f"[BPM Slot] No matching row found for path: {path}")

    # ==========================
    #  Progress Update
    # ==========================
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS format."""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins}:{secs:02d}"
    
    @QtCore.pyqtSlot(int, float, float)
    def _on_progress_updated(self, progress_value: int, elapsed: float, total_duration: float):
        """Update progress bar and time labels from worker thread."""
        self.progress.setValue(progress_value)
        self.time_label.setText(self._format_time(elapsed))
        self.duration_label.setText(self._format_time(total_duration))

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
        current_row = self.playlist.currentRow()
        if current_row >= 0:
            item = self.playlist.item(current_row, 0)
            if item:
                self.load_midi(item.data(QtCore.Qt.UserRole))
        
        # Update prev/next button states
        self.prev_button.setEnabled(current_row > 0)
        self.next_button.setEnabled(current_row >= 0 and current_row < self.playlist.rowCount() - 1)

    def on_playlist_item_double_clicked(self, row: int, col: int):
        path_item = self.playlist.item(row, 0)
        if path_item:
            self.load_midi(path_item.data(QtCore.Qt.UserRole))
            self.on_play_clicked()

    # ==========================
    #  Load + Build Macro
    # ==========================

    def load_midi(self, path):
        self.stop_playback()

        self.current_midi_path = path
        self.file_label.setText("")

        # Cached?
        if path in self.macro_cache:
            self.current_macro = self.macro_cache[path]
            if self.current_macro:
                self.play_button.setEnabled(True)
                # Update duration label
                self.current_song_duration = self.current_macro[-1]["time"] if self.current_macro else 0
                self.duration_label.setText(self._format_time(self.current_song_duration))
            self.status_label.setText("Ready.")
            return

        # Build in background
        self.status_label.setText("Processing MIDI…")
        self.play_button.setEnabled(False)

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
            # Update duration label
            self.current_song_duration = macro[-1]["time"] if macro else 0
            self.duration_label.setText(self._format_time(self.current_song_duration))
            self.status_label.setText("Ready.")
        else:
            self.status_label.setText(
                "This MIDI produced an empty macro (no playable notes in range)."
            )

    def _update_play_button_state(self):
        """Update play button enabled state based on loading status."""
        with self.macros_loading_lock:
            is_loading = self.macros_loading > 0
        
        # Show buttons if not loading anymore
        if not is_loading:
            self._show_buttons()
        
        # Disable play button if loading, enable if we have a macro and not loading
        should_enable = bool(self.current_macro) and not is_loading
        if self.play_button.isEnabled() != should_enable:
            self.play_button.setEnabled(should_enable)

    @QtCore.pyqtSlot(str)
    def _load_failed(self, msg):
        self.status_label.setText("Error loading MIDI.")
        QtWidgets.QMessageBox.critical(self, "Error", msg)

    # ==========================
    #  Playlist Navigation
    # ==========================

    def on_prev_clicked(self):
        """Move to previous track in playlist."""
        current_row = self.playlist.currentRow()
        if current_row > 0:
            self.playlist.selectRow(current_row - 1)

    def on_next_clicked(self):
        """Move to next track in playlist."""
        current_row = self.playlist.currentRow()
        if current_row < self.playlist.rowCount() - 1:
            self.playlist.selectRow(current_row + 1)

    # ==========================
    #  Playback: Single Track
    # ==========================

    def on_play_clicked(self):
        if not self.current_macro:
            return
        
        # Check if macros are still loading
        with self.macros_loading_lock:
            if self.macros_loading > 0:
                self.status_label.setText(f"Still loading {self.macros_loading} songs… please wait.")
                return
        
        # Handle pause/resume
        if self.play_thread and self.play_thread.is_alive():
            if self.is_paused:
                # Resume
                self.is_paused = False
                self.stop_event.clear()
                self.play_button.setIcon(create_pause_icon(40))
                self.status_label.setText(f"Playing… ({STOP_HOTKEY} to stop)")
            else:
                # Pause
                self.is_paused = True
                self.stop_event.set()
                self.play_button.setIcon(create_play_icon(40))
                self.status_label.setText("Paused")
            return

        # Start playback
        time.sleep(SLEEP_TIME)
        self.playlist_mode = False
        self.is_paused = False
        self.play_button.setIcon(create_pause_icon(40))
        self.status_label.setText(f"Playing… ({STOP_HOTKEY} to stop)")
        self.stop_event.clear()
        self.progress.setValue(0)
        self.time_label.setText("0:00")
        # Set duration label
        if self.current_macro:
            total_duration = self.current_macro[-1]["time"] if self.current_macro else 0
            self.duration_label.setText(self._format_time(total_duration))
        self.play_button.setEnabled(True)
        self.play_playlist_button.setEnabled(False)

        def worker():
            print(f"[DEBUG] Worker started. Current macro has {len(self.current_macro)} events")
            play_macro(self.current_macro, self.stop_event, self.progress_updated.emit)
            print("[DEBUG] Worker finished playback")
            QtCore.QMetaObject.invokeMethod(
                self, "_playback_done", QtCore.Qt.QueuedConnection
            )

        self.play_thread = threading.Thread(target=worker, daemon=True)
        self.play_thread.start()

    # ==========================
    #  Playback: Playlist
    # ==========================

    def on_play_playlist_clicked(self):
        if self.playlist.rowCount() == 0:
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
        self.progress.setValue(0)
        self.time_label.setText("0:00")
        self.duration_label.setText("0:00")
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
        count = self.playlist.rowCount()
        for i in range(start_index, count):
            if self.stop_event.is_set():
                return

            item = self.playlist.item(i, 0)
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
                QtCore.Q_ARG(object, macro),
            )

            play_macro(macro, self.stop_event, self.progress_updated.emit)
            if self.stop_event.is_set():
                return

            if i < count - 1:
                if self.stop_event.wait(PLAYLIST_GAP_SECONDS):
                    return

    @QtCore.pyqtSlot(int, str, object)
    def _set_now_playing(self, row: int, path: str, macro):
        if 0 <= row < self.playlist.rowCount():
            # Prevent selectionChanged from firing while we move the row programmatically
            self.playlist.blockSignals(True)
            self.playlist.setCurrentCell(row, 0)
            self.playlist.blockSignals(False)

        self.file_label.setText(f"Playing: {path}")
        self.status_label.setText(f"Playing playlist… ({STOP_HOTKEY} to stop)")
        
        # Set duration for this track
        self.time_label.setText("0:00")
        if macro:
            total_duration = macro[-1]["time"] if macro else 0
            self.duration_label.setText(self._format_time(total_duration))
        else:
            self.duration_label.setText("0:00")

    # ==========================
    #  Playback Finished
    # ==========================

    @QtCore.pyqtSlot()
    @QtCore.pyqtSlot()
    def _playback_done(self):
        self.progress.setValue(0)
        self.time_label.setText("0:00")
        self.duration_label.setText("0:00")
        self.is_paused = False

        if self.current_macro:
            self.play_button.setEnabled(True)
            self.play_button.setIcon(create_play_icon(40))
        else:
            self.play_button.setEnabled(False)

        if self.playlist.rowCount() > 0:
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
        self.play_button.setIcon(create_play_icon(40))
        self.status_label.setText("Stopped.")

    def stop_playback(self):
        if self.play_thread and self.play_thread.is_alive():
            self.stop_event.set()
            self.play_thread.join(timeout=1.0)

        if self.playlist.rowCount() > 0:
            self.play_playlist_button.setEnabled(True)
        if self.current_macro:
            self.play_button.setEnabled(True)

    def _on_global_hotkey(self):
        QtCore.QMetaObject.invokeMethod(
            self, "_global_stop", QtCore.Qt.QueuedConnection
        )

    @QtCore.pyqtSlot()
    def _global_stop(self):
        # F11 now plays/pauses instead of stopping
        # If a macro is loaded, call on_play_clicked to start or toggle pause
        if self.current_macro:
            self.on_play_clicked()
        else:
            # If no macro loaded, show message
            self.status_label.setText("No song selected. Click a song in the playlist first.")

    # ==========================
    #  Close Event
    # ==========================

    # ==========================
    #  Playlist Persistence
    # ==========================
    
    def _save_playlist_to_file(self):
        """Save current playlist to JSON file."""
        playlist_data = []
        for i in range(self.playlist.rowCount()):
            item = self.playlist.item(i, 0)
            path = item.data(QtCore.Qt.UserRole) if item else None
            if path:
                playlist_data.append(path)
        
        try:
            with open(PLAYLIST_FILE, 'w') as f:
                json.dump(playlist_data, f, indent=2)
            self.status_label.setText(f"✓ Playlist saved ({len(playlist_data)} songs)")
            print(f"[Playlist] Saved {len(playlist_data)} songs to {PLAYLIST_FILE}")
        except Exception as e:
            print(f"Error saving playlist: {e}")
            self.status_label.setText(f"✗ Error saving playlist: {e}")
    
    def load_playlist_from_file(self):
        """Load playlist from JSON file."""
        if not os.path.exists(PLAYLIST_FILE):
            self._show_buttons()
            return
        
        try:
            with open(PLAYLIST_FILE, 'r') as f:
                playlist_data = json.load(f)
            
            if not playlist_data:
                self._show_buttons()
                return
            
            for path in playlist_data:
                if os.path.exists(path):
                    self.add_to_playlist(path, auto_select=False)
        except Exception as e:
            print(f"Error loading playlist: {e}")
            self._show_buttons()
    
    def _show_buttons(self):
        """Show the play buttons and hide the loading indicator."""
        self.button_stack.setCurrentIndex(1)  # Show button_container
    
    def closeEvent(self, event):
        self.stop_playback()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Apply dark Nord theme before creating any windows
    apply_nord_theme(app)

    # Use the .ico and resource_path
    icon_path = resource_path("Player.ico")
    app.setWindowIcon(QtGui.QIcon(icon_path))

    w = MainWindow()

    # Try to make the native title bar dark on Windows
    enable_windows_dark_titlebar(w)

    # Explicitly set the window icon too
    w.setWindowIcon(QtGui.QIcon(icon_path))

    # Window positioning is handled in MainWindow.__init__ via _position_on_secondary_monitor()
    sys.exit(app.exec_())

if __name__ == "__main__":
     main()
