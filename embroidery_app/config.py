from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt # For Qt.GlobalColor

# --- Default Colors ---
DEFAULT_BACKGROUND_COLOR = QColor("#E0E0E0")
DEFAULT_STITCH_COLOR = QColor(Qt.GlobalColor.black) # Fallback if no thread info

# --- UI Settings ---
MAX_LEFT_PANEL_WIDTH = 320 # Adjusted for a bit more space
INITIAL_WINDOW_WIDTH = 1280 # Slightly wider default
INITIAL_WINDOW_HEIGHT = 800
# Render Engine settings
RENDER_PADDING = 50  # Pixels of padding around the pattern in the base image
MIN_RENDER_IMAGE_SIZE = 100 # Minimum width/height for the base_image
INITIAL_RENDER_SCALE = 8.0 # Factor to scale the initial rendering for better quality

# 快速预览模式设置 - 降低质量以提高速度
FAST_PREVIEW_MODE = True  # 启用快速预览模式
FAST_PREVIEW_TARGET_PIXELS = 1000  # 快速模式下的目标像素数（降低质量）
FAST_PREVIEW_MAX_SCALE = 20.0  # 快速模式下的最大缩放比例
FAST_PREVIEW_MIN_SCALE = 1.0   # 快速模式下的最小缩放比例
FAST_PREVIEW_LINE_WIDTH_FACTOR = 0.5  # 快速模式下线宽因子（更细的线条）

# --- Zoom/Scale Settings ---
MIN_ZOOM_SCALE = 0.05 # Allow more zoom out
MAX_ZOOM_SCALE = 20.0  # Allow more zoom in
ZOOM_IN_FACTOR = 1.15  # 更平滑的缩放步长，减少性能负担
ZOOM_OUT_FACTOR = 1 / ZOOM_IN_FACTOR # Symmetric zoom out

# --- Rotation Settings ---
ROTATION_STEP = 15 # Degrees for each rotation button click

# --- Learn More Link ---
LEARN_MORE_URL = "https://m.me/ch/AbaHiKA9Y1uonpBZ/"

# --- Application Info ---
APP_NAME = "Institch Embroidery Viewer"
APP_VERSION = "0.1.0"

# --- Styling (can be expanded or moved to a QSS file) ---
# Using a more modern, flat style approach
MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #ECEFF1; /* Light Grey Blue */
    }
    QWidget#LeftPanel {
        background-color: #FFFFFF;
        border-right: 1px solid #CFD8DC; /* Light Border */
    }
    QPushButton {
        background-color: #546E7A; /* Blue Grey */
        color: white;
        border: none;
        padding: 10px 15px;
        border-radius: 4px;
        font-size: 10pt;
        min-height: 22px;
    }
    QPushButton:hover {
        background-color: #607D8B; /* Lighter Blue Grey */
    }
    QPushButton:pressed {
        background-color: #455A64; /* Darker Blue Grey */
    }
    QPushButton:disabled {
        background-color: #B0BEC5; /* Light Grey for disabled */
        color: #78909C;
    }
    QLabel {
        font-size: 10pt;
        color: #37474F; /* Dark Grey Blue text */
        margin-bottom: 6px;
        margin-top: 6px;
    }
    QLabel#FileNameLabel {
        font-weight: bold;
        font-size: 11pt;
    }
    QGraphicsView {
        border: 1px solid #CFD8DC; /* Light Border */
        background-color: #FFFFFF; /* Default view background, can be overridden */
    }
    #LearnMoreButton {
        background-color: #00796B; /* Teal */
        color: white;
        font-weight: bold;
        padding: 12px;
    }
    #LearnMoreButton:hover {
        background-color: #00897B; /* Lighter Teal */
    }
    #LearnMoreButton:pressed {
        background-color: #00695C; /* Darker Teal */
    }
    /* Styling for QScrollArea if used, or other specific widgets */
"""