import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QColorDialog, QFrame, QSpacerItem, QSizePolicy, QGraphicsItem, QApplication)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QBrush, QPen, QTransform, QMovie, QWheelEvent, QImageReader, QIcon
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSize, QUrl, QTime, QTimer
from PyQt6.QtGui import QDesktopServices # For opening web links

# Add parent dir to sys.path to import pyembroidery if not installed
# current_script_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_script_dir) # This is 'embroidery_app', need to go one more up
# sys.path.insert(0, os.path.dirname(project_root)) # This adds 'pyembroidery0530' to path
# Corrected path addition assuming this file is in embroidery_app
# and pyembroidery package is in the parent of embroidery_app
# This should be handled in main.py primarily
import pyembroidery
from file_handler import FileHandler
from render_engine import RenderEngine
from unit_converter import UnitConverter
import config

class CustomGraphicsView(QGraphicsView):
    # Signal to notify when view is panned or zoomed, carrying the new view rect
    viewTransformed = pyqtSignal(QRectF)
    wheel_scrolled = pyqtSignal(QWheelEvent)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._is_panning = False
        self._last_pan_point = QPointF()

    def wheelEvent(self, event: QWheelEvent):
        self.wheel_scrolled.emit(event)
        # Prevent default scrollbar behavior if we are handling zoom
        event.accept() 

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            self._is_panning = True
            self._last_pan_point = event.pos()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._last_pan_point
            self._last_pan_point = event.pos()
            # self.translate(delta.x(), delta.y()) # This moves the view's content
            hs = self.horizontalScrollBar()
            vs = self.verticalScrollBar()
            hs.setValue(hs.value() - delta.x())
            vs.setValue(vs.value() - delta.y())
            event.accept()
            self.viewTransformed.emit(self.mapToScene(self.viewport().rect()).boundingRect())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_panning:
            self._is_panning = False
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            self.viewTransformed.emit(self.mapToScene(self.viewport().rect()).boundingRect())
        else:
            super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.original_file_name_stem = None # To store the original filename without extension
        self.setWindowTitle(config.APP_NAME)
        self.setGeometry(100, 100, config.INITIAL_WINDOW_WIDTH, config.INITIAL_WINDOW_HEIGHT)
        self.setStyleSheet(config.MAIN_WINDOW_STYLE)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "te9wb-dqd91-001.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.current_pattern = None
        self.current_pixmap_item = None
        self.current_bg_color = config.DEFAULT_BACKGROUND_COLOR

        self.file_handler = FileHandler()
        self.render_engine = RenderEngine()
        self.render_engine.set_background_color(self.current_bg_color)
        # Loading animation will be initialized in _init_ui after preview_view is created
        self.loading_movie = None 
        self.lbl_loading_movie = None

        self._init_ui()
        self._connect_signals()
        self.update_button_states()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0,0,0,0) # No margin for the main layout
        main_layout.setSpacing(0) # No spacing between panels

        # --- Left Panel (Controls and Info) --- 
        left_panel_widget = QWidget()
        left_panel_widget.setObjectName("LeftPanel") # For QSS styling
        left_panel_widget.setMaximumWidth(config.MAX_LEFT_PANEL_WIDTH)
        left_layout = QVBoxLayout(left_panel_widget)
        left_layout.setContentsMargins(15, 15, 15, 15) # Padding inside the left panel
        left_layout.setSpacing(10)

        self.btn_import = QPushButton("Import File") # Icon can be set later
        left_layout.addWidget(self.btn_import)

        # Info Section
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel) # Optional: add a frame around info
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(5,5,5,5)
        self.lbl_file_name = QLabel("File: None")
        self.lbl_file_name.setObjectName("FileNameLabel")
        self.lbl_file_name.setWordWrap(True)
        
        # 信息标签
        self.lbl_stitch_count = QLabel("Stitches: N/A")
        self.lbl_color_count = QLabel("Colors: N/A")
        self.lbl_size_cm = QLabel("Size (cm): N/A")
        
        # 添加所有信息标签到布局
        info_layout.addWidget(self.lbl_file_name)
        info_layout.addWidget(self.lbl_stitch_count)
        info_layout.addWidget(self.lbl_color_count)
        info_layout.addWidget(self.lbl_size_cm)
        left_layout.addWidget(info_frame)
        
        left_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Preview Controls
        self.btn_rotate_left = QPushButton("Rotate Left")
        self.btn_rotate_right = QPushButton("Rotate Right")
        self.btn_reset_preview = QPushButton("Reset Preview")
        self.btn_change_bg = QPushButton("Background Color")
        self.btn_change_bg.setToolTip("Change the background color of the preview")
        self.btn_change_bg.setFixedHeight(35)
        
        # PNG缓存机制
        self.cached_png_image = None  # 缓存的PNG图像
        self.cached_png_pattern_hash = None  # 缓存的图案哈希值
        
        preview_controls_layout = QHBoxLayout()
        preview_controls_layout.addWidget(self.btn_rotate_left)
        preview_controls_layout.addWidget(self.btn_rotate_right)
        left_layout.addLayout(preview_controls_layout)
        left_layout.addWidget(self.btn_reset_preview)
        left_layout.addWidget(self.btn_change_bg)

        left_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.btn_export = QPushButton("Export As...")
        left_layout.addWidget(self.btn_export)

        left_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        self.btn_learn_more = QPushButton("Learn more")
        self.btn_learn_more.setObjectName("LearnMoreButton")
        self.btn_learn_more.setStyleSheet("QPushButton { background-color: #8A2BE2; color: white; border: none; padding: 8px; border-radius: 4px; } QPushButton:hover { background-color: #9932CC; }")
        left_layout.addWidget(self.btn_learn_more)

        main_layout.addWidget(left_panel_widget)

        # --- Right Panel (Preview Area) --- 
        self.preview_scene = QGraphicsScene(self)
        self.preview_view = CustomGraphicsView(self.preview_scene, self)
        # Enhanced rendering hints for better image quality
        self.preview_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.preview_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.preview_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.preview_view.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        # Set viewport update mode for better performance - use minimal updates
        self.preview_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        # Optimize for performance over quality during interactions
        self.preview_view.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.preview_view.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.preview_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.preview_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.preview_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.preview_view.setBackgroundBrush(QBrush(self.current_bg_color))

        # Loading animation with GIF
        # Ensure the path to loading.gif is correct. Assuming it's in the same directory as main_window.py or a sub-directory.
        # If main.py is in the root and runs embroidery_app.main_window, then 'embroidery_app/loading.gif' is correct from root.
        

        main_layout.addWidget(self.preview_view) # Add preview_view to the main layout

        # Initialize loading animation here, after preview_view is created
        self.lbl_loading_movie = QLabel(self.preview_view) # Parent to preview_view for overlay
        self.lbl_loading_movie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_loading_movie.setMinimumSize(50, 50) # Set a minimum size for the QLabel
        self.lbl_loading_movie.setStyleSheet("background-color: transparent;")
        # Correct path to loading.gif, assuming it's in the same directory as this script (main_window.py)
        gif_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loading.gif')
        if os.path.exists(gif_path):
            self.loading_movie = QMovie(gif_path) # Remove explicit format specification
            # Check supported formats by QMovie
            supported_movie_formats = QMovie.supportedFormats()
            print(f"Debug: QMovie.supportedFormats(): {[bytes(fmt).decode() for fmt in supported_movie_formats]}")
            if not supported_movie_formats:
                print("Warning: QMovie.supportedFormats() returned empty list - this is a known issue on some Windows systems")
            self.loading_movie.setCacheMode(QMovie.CacheMode.CacheAll) # Cache all frames
            self.lbl_loading_movie.setMovie(self.loading_movie)
            # Additional check after setMovie
            if not self.loading_movie.isValid():
                print(f"Debug: QMovie became invalid after setMovie. Error: {self.loading_movie.lastError()}, String: {self.loading_movie.lastErrorString()}")
            elif self.loading_movie.lastError() != 0:
                 print(f"Debug: QMovie has error after setMovie (but still valid). Error: {self.loading_movie.lastError()}, String: {self.loading_movie.lastErrorString()}")

            # 打印支持的图像格式
            supported_formats = QImageReader.supportedImageFormats()
            print(f"Debug: Supported image formats by QImageReader: {[bytes(fmt).decode() for fmt in supported_formats]}")
            print(f"Debug: Checking if 'gif' is supported by QImageReader: {'gif' in [bytes(fmt).decode() for fmt in supported_formats]}")

            # Check if QMovie is valid and print error if not
            if self.loading_movie.isValid():
                print(f"Debug: QMovie isValid after init: True, format: {self.loading_movie.format()}, lastError: {self.loading_movie.lastError()}, lastErrorString: {self.loading_movie.lastErrorString()}")
                if self.loading_movie.lastError() != 0: # QImageReader.ImageReaderError.NoError is 0
                    print(f"Debug: QMovie error details after init: error={self.loading_movie.lastError()}, string='{self.loading_movie.lastErrorString()}'")
                # Connect frame change signal
                self.loading_movie.frameChanged.connect(self._on_loading_frame_changed)
            else:
                print(f"Debug: QMovie isValid after init: False, format: {self.loading_movie.format()}, lastError: {self.loading_movie.lastError()}, lastErrorString: {self.loading_movie.lastErrorString()}")
                if self.loading_movie.lastError() != 0: # QImageReader.ImageReaderError.NoError is 0
                    print(f"Debug: QMovie error details after init (isValid=False): error={self.loading_movie.lastError()}, string='{self.loading_movie.lastErrorString()}'")
                # If QMovie is invalid, fall back to text
                print("Warning: QMovie is invalid, falling back to text loading indicator")
                self.loading_movie = None
                self.lbl_loading_movie.setText("Loading...")
                self.lbl_loading_movie.setStyleSheet("background-color: rgba(200, 200, 200, 180); color: black; padding: 10px; border-radius: 5px;")
            
            # Do not start the movie here, only when importing a file
        else:
            self.loading_movie = None # Ensure it's None if not loaded
            self.lbl_loading_movie.setText("Loading...") # Fallback text
            self.lbl_loading_movie.setStyleSheet("background-color: rgba(200, 200, 200, 180); color: black; padding: 10px; border-radius: 5px;")
            print(f"Warning: loading.gif not found at {gif_path}. Using text label.")
        self.lbl_loading_movie.adjustSize()
        self.lbl_loading_movie.hide() # Initially hidden

    def _on_loading_frame_changed(self, frame_number):
        print(f"Debug: _on_loading_frame_changed called, frame: {frame_number}")
        self.lbl_loading_movie.repaint() # Try repaint for immediate effect

        # No separate preview_layout needed if preview_view is directly in main_layout

    def _connect_signals(self):
        self.btn_import.clicked.connect(self.import_file)
        self.btn_rotate_left.clicked.connect(self.rotate_preview_left)
        self.btn_rotate_right.clicked.connect(self.rotate_preview_right)
        self.btn_reset_preview.clicked.connect(self.reset_preview)
        self.btn_change_bg.clicked.connect(self.change_background_color)
        self.btn_export.clicked.connect(self.export_file)
        self.btn_learn_more.clicked.connect(self.open_learn_more_link)
        self.preview_view.wheel_scrolled.connect(self.zoom_preview_at_mouse)

    def update_button_states(self):
        has_pattern = self.current_pattern is not None
        self.btn_rotate_left.setEnabled(has_pattern)
        self.btn_rotate_right.setEnabled(has_pattern)
        self.btn_reset_preview.setEnabled(has_pattern)
        self.btn_export.setEnabled(has_pattern)

    def open_learn_more_link(self):
        QDesktopServices.openUrl(QUrl(config.LEARN_MORE_URL))

    def import_file(self):
        # Get a dictionary of descriptions to lists of extensions
        supported_formats_dict = self.file_handler.get_supported_read_formats(as_dict=True) 
        all_extensions = []
        if supported_formats_dict:
            for ext_list in supported_formats_dict.values():
                all_extensions.extend(ext_list)
        
        unique_extensions = sorted(list(set(all_extensions)))
        
        if not unique_extensions: # Fallback if no extensions found
            filter_string = "All Files (*)"
        else:
            filter_string = f"All Supported Embroidery Files ({' '.join(['*.' + ext.lower() for ext in unique_extensions])});;All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(self, "Import Embroidery File", "", filter_string)
        if file_path:
            # Show loading animation
            if self.lbl_loading_movie:
                # Adjust size and position before showing
                parent_size = self.preview_view.size()
                # Use a fixed size or ensure sizeHint() is reasonable
                fixed_label_size = QSize(100, 100) # Example fixed size, adjust as needed
                self.lbl_loading_movie.resize(fixed_label_size)
                self.lbl_loading_movie.move(int((parent_size.width() - fixed_label_size.width()) / 2),
                                            int((parent_size.height() - fixed_label_size.height()) / 2))
                self.lbl_loading_movie.setStyleSheet("background-color: transparent;") # Reset to transparent background
                if self.loading_movie: # If QMovie is used (GIF)
                    self.lbl_loading_movie.setScaledContents(True) # Ensure content scales
                self.lbl_loading_movie.raise_() # Bring to front
                self.lbl_loading_movie.show()
                print(f"Debug: lbl_loading_movie geometry after show: {self.lbl_loading_movie.geometry()}")
                print(f"Debug: preview_view geometry: {self.preview_view.geometry()}")
                if self.loading_movie: # If QMovie is used (GIF)
                    # 打印支持的图像格式
                    supported_formats = QImageReader.supportedImageFormats()
                    print(f"Debug: Supported image formats by QImageReader: {[bytes(fmt).decode() for fmt in supported_formats]}")
                    print(f"Debug: Checking if 'gif' is supported: {'gif' in [bytes(fmt).decode() for fmt in supported_formats]}")

                    if self.loading_movie.isValid():
                        print(f"Debug: QMovie isValid: True, format: {self.loading_movie.format()}, lastError: {self.loading_movie.lastError()}, lastErrorString: {self.loading_movie.lastErrorString()}")
                        if self.loading_movie.lastError() != 0: # QImageReader.ImageReaderError.NoError is 0
                            print(f"Debug: QMovie error details: error={self.loading_movie.lastError()}, string='{self.loading_movie.lastErrorString()}'")
                    else:
                        print(f"Debug: QMovie isValid: False, format: {self.loading_movie.format()}, lastError: {self.loading_movie.lastError()}, lastErrorString: {self.loading_movie.lastErrorString()}")
                        if self.loading_movie.lastError() != 0: # QImageReader.ImageReaderError.NoError is 0
                            print(f"Debug: QMovie error details (isValid=False): error={self.loading_movie.lastError()}, string='{self.loading_movie.lastErrorString()}'")
                    
                    self.loading_movie.stop() # Stop previous animation if any
                    self.loading_movie.start()
                    QApplication.processEvents() # Process events immediately after starting
                    print(f"Debug: Loading movie state after start and processEvents: {self.loading_movie.state()}")
                    print(f"Debug: QMovie loop count: {self.loading_movie.loopCount()}")
                    print(f"Debug: QMovie current frame: {self.loading_movie.currentFrameNumber()}")
                    if self.loading_movie.state() == QMovie.MovieState.NotRunning and self.loading_movie.lastError() != 0: # QImageReader.ImageReaderError.NoError is 0
                         print(f"Debug: QMovie failed to start. Error: {self.loading_movie.lastErrorString()}")
                else: # If text label is used
                    print("Debug: Using text label for loading indicator.")
                    QApplication.processEvents() # Also process events for text label case

            self.current_pattern = self.file_handler.read_pattern(file_path)
            if self.current_pattern:
                # 清除PNG缓存（新文件加载时）
                self.cached_png_image = None
                self.cached_png_pattern_hash = None
                print("已清除PNG缓存（新文件加载）")
                
                # PNG预览模式：使用缓存机制
                self.render_engine.create_base_image(self.current_pattern, 
                                                     self.preview_view.viewport().width(), 
                                                     self.preview_view.viewport().height())
                # 缓存新生成的PNG图像
                if self.render_engine.base_image and not self.render_engine.base_image.isNull():
                    current_hash = self.get_pattern_hash(self.current_pattern)
                    self.cached_png_image = self.render_engine.base_image.copy()
                    self.cached_png_pattern_hash = current_hash
                    print(f"新PNG图像已缓存，哈希值: {current_hash}")
                
                self.original_file_name_stem = os.path.splitext(os.path.basename(file_path))[0]
                self.update_file_info(file_path, self.current_pattern)
                self.display_rendered_image()
                self.reset_preview() # Fit to view
                # Ensure loading animation is hidden AFTER rendering and preview reset
                if self.lbl_loading_movie and self.lbl_loading_movie.isVisible():
                    if self.loading_movie:
                        self.loading_movie.stop()
                        print("Debug: Stopped loading movie")
                    self.lbl_loading_movie.hide()
                    print("Debug: Hid loading label after displaying image")
            else:
                self.lbl_file_name.setText("File: Error loading")
                self.clear_file_info()
                self.preview_scene.clear()
                self.current_pixmap_item = None
                if self.lbl_loading_movie:
                    if self.loading_movie:
                        self.loading_movie.stop()
                    self.lbl_loading_movie.hide()
            self.update_button_states()

    def clear_file_info(self):
        self.lbl_stitch_count.setText("Stitches: N/A")
        self.lbl_color_count.setText("Colors: N/A")
        self.lbl_size_cm.setText("Size (cm): N/A")

    # 在update_file_info方法添加备用颜色统计逻辑
    def update_file_info(self, file_path, pattern):
        if pattern is None:
            self.lbl_file_name.setText("File: None")
            self.clear_file_info()
            return

        self.lbl_file_name.setText(f"File: {os.path.basename(file_path)}")
        stitch_count = len(pattern.stitches) if pattern.stitches else 0
        self.lbl_stitch_count.setText(f"Stitches: {stitch_count}")
        if pattern:
            if hasattr(pattern, 'threadlist') and pattern.threadlist:
                num_colors = len(pattern.threadlist)
                self.lbl_color_count.setText(f"Colors: {num_colors}")
            elif hasattr(pattern, 'stitches'):
                # Fallback: Count color changes from stitches if threadlist is empty
                  try:
                      print(f"Debug: Attempting fallback color count. pyembroidery.COLOR_CHANGE = {pyembroidery.COLOR_CHANGE}")
                      if not pattern.stitches:
                          num_colors = 0
                          color_changes = 0
                          print("Debug: pattern.stitches is empty.")
                      else:
                          print(f"Debug: pattern.stitches has {len(pattern.stitches)} items. First 5 stitch commands (s[2]):")
                          for i, stitch_cmd in enumerate(pattern.stitches[:5]):
                              if len(stitch_cmd) > 2:
                                  print(f"  stitch_cmd[{i}][2] = {stitch_cmd[2]} (type: {type(stitch_cmd[2])}), s[2] == COLOR_CHANGE = {stitch_cmd[2] == pyembroidery.COLOR_CHANGE}")
                              else:
                                  print(f"  stitch_cmd[{i}] = {stitch_cmd} (length < 3)")
                          
                          color_changes = sum(1 for stitch_command in pattern.stitches if len(stitch_command) > 2 and (stitch_command[2] == pyembroidery.COLOR_CHANGE))
                          num_colors = color_changes + 1
                      
                      self.lbl_color_count.setText(f"Colors: {num_colors}")
                      threadlist_debug = pattern.threadlist if hasattr(pattern, 'threadlist') else 'N/A'
                      stitches_len_debug = len(pattern.stitches) if hasattr(pattern, 'stitches') and pattern.stitches is not None else 0
                      print(f"Debug: Fallback color count result. Threadlist: {threadlist_debug}, Stitches: {stitches_len_debug}, Color Changes Detected: {color_changes}, Calculated Colors (fallback): {num_colors}")
                  except Exception as e:
                      print(f"Error calculating fallback colors: {e}")
                      self.lbl_color_count.setText("Colors: Error")
            else:
                self.lbl_color_count.setText("Colors: N/A")
        else:
            self.lbl_color_count.setText("Colors: N/A")
        
        # Get bounds from render_engine as it calculates them for rendering
        # Ensure render_engine.pattern_bounds_mm10 is updated before calling this
        size_info = UnitConverter.get_pattern_size_cm(self.render_engine.pattern_bounds_mm10)
        if size_info:
            width_cm, height_cm = size_info
            self.lbl_size_cm.setText(f"Size: {width_cm:.2f} x {height_cm:.2f} cm")
        else:
            self.lbl_size_cm.setText("Size (cm): N/A")
        
        # 更新信息面板完成

    def display_rendered_image(self):
        self.preview_scene.clear()
        self.current_pixmap_item = None
        if self.render_engine.base_image and not self.render_engine.base_image.isNull():
            # Create background rectangle to support transparent PNG preview
            image_rect = QRectF(self.render_engine.base_image.rect())
            background_rect = self.preview_scene.addRect(
                image_rect, 
                QPen(Qt.PenStyle.NoPen), 
                QBrush(self.render_engine.background_color)
            )
            
            # Create high-quality pixmap with proper format conversion
            pixmap = QPixmap.fromImage(self.render_engine.base_image, Qt.ImageConversionFlag.ColorOnly)
            self.current_pixmap_item = QGraphicsPixmapItem(pixmap)
            # Enable smooth transformation for the pixmap item
            self.current_pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            # Add item to scene first, then set its properties.
            self.preview_scene.addItem(self.current_pixmap_item)
            
            # Ensure PNG image is above background
            self.current_pixmap_item.setZValue(1)
            background_rect.setZValue(0)
            
            # Position the item at the scene's origin (0,0) before setting transform origin and scene rect.
            self.current_pixmap_item.setPos(0, 0)
            # Set the transform origin to the center of the pixmap item for correct rotation.
            # boundingRect() is in item's local coordinates (top-left is 0,0).
            self.current_pixmap_item.setTransformOriginPoint(self.current_pixmap_item.boundingRect().center())
            # The scene's rectangle should be based on this single item, now positioned at (0,0).
            # mapToScene().boundingRect() will give its extent in scene coordinates.
            self.preview_scene.setSceneRect(self.current_pixmap_item.mapToScene(self.current_pixmap_item.boundingRect()).boundingRect())
        else:
            self.preview_scene.setSceneRect(QRectF()) # Clear scene rect if no image

    def zoom_preview_at_mouse(self, event: QWheelEvent):
        """在鼠标位置缩放预览 - 性能优化版本"""
        if not self.current_pixmap_item:
            return
        
        # 性能优化：限制缩放频率
        current_time = QTime.currentTime()
        if hasattr(self, '_last_zoom_time'):
            if self._last_zoom_time.msecsTo(current_time) < 50:  # 限制缩放频率为20fps
                return
        self._last_zoom_time = current_time
        
        # 获取当前缩放级别
        current_scale = self.preview_view.transform().m11()
        
        zoom_factor = config.ZOOM_IN_FACTOR if event.angleDelta().y() > 0 else config.ZOOM_OUT_FACTOR
        new_scale = current_scale * zoom_factor
        
        # 性能优化：限制缩放范围
        if new_scale < config.MIN_ZOOM_SCALE or new_scale > config.MAX_ZOOM_SCALE:
            return
            
        self.preview_view.scale(zoom_factor, zoom_factor)

    def rotate_preview_left(self):
        if self.current_pixmap_item:
            self.current_pixmap_item.setRotation(self.current_pixmap_item.rotation() - config.ROTATION_STEP)
            # Update scene rect after rotation to ensure correct interaction boundaries
            if self.current_pixmap_item.scene():
                 self.preview_scene.setSceneRect(self.preview_scene.itemsBoundingRect())

    def rotate_preview_right(self):
        if self.current_pixmap_item:
            self.current_pixmap_item.setRotation(self.current_pixmap_item.rotation() + config.ROTATION_STEP)
            # Update scene rect after rotation
            if self.current_pixmap_item.scene():
                self.preview_scene.setSceneRect(self.preview_scene.itemsBoundingRect())

    def reset_preview(self):
        if self.current_pixmap_item and self.current_pixmap_item.scene() == self.preview_scene:
            self.preview_view.resetTransform() # Resets scale and pan to identity
            self.current_pixmap_item.setRotation(0) # Reset item's rotation
            self.current_pixmap_item.setPos(0, 0) # Position item at scene origin
            # Set transform origin AFTER positioning and BEFORE any scaling/fitting that might rely on it.
            # boundingRect() is in item's local coordinates, so its center is always relative to its own 0,0.
            self.current_pixmap_item.setTransformOriginPoint(self.current_pixmap_item.boundingRect().center())

            # The scene rect should encompass the item. mapToScene gives the item's rect in scene coordinates.
            item_scene_rect = self.current_pixmap_item.mapToScene(self.current_pixmap_item.boundingRect()).boundingRect()
            
            # For better dragging experience, especially when zoomed out, make scene rect slightly larger.
            padding = 50 # Adjust as needed
            padded_scene_rect = item_scene_rect.adjusted(-padding, -padding, padding, padding)
            self.preview_scene.setSceneRect(padded_scene_rect)
            
            # Fit the original item's scene rect (without padding) into view to keep it centered and appropriately sized.
            self.preview_view.fitInView(item_scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

        else:
            self.preview_view.resetTransform()
            self.preview_scene.setSceneRect(QRectF())
        self.update_button_states()

    def change_background_color(self):
        color = QColorDialog.getColor(self.current_bg_color, self, "Select Background Color")
        if color.isValid():
            self.current_bg_color = color
            # 直接更改预览视图的背景颜色，不重新生成针迹预览
            self.preview_view.setBackgroundBrush(QBrush(self.current_bg_color))
            # 更新render_engine的背景颜色设置，但不触发重新渲染
            self.render_engine.set_background_color(self.current_bg_color)
            # 重新显示图像以更新背景矩形的颜色
            self.display_rendered_image()


    

    
    def get_pattern_hash(self, pattern):
        """生成图案的哈希值用于缓存判断"""
        try:
            # 使用图案的关键属性生成哈希
            import hashlib
            hash_data = f"{len(pattern.stitches)}_{pattern.bounds()}_{len(pattern.threadlist)}"
            return hashlib.md5(hash_data.encode()).hexdigest()
        except Exception as e:
            print(f"生成图案哈希失败: {e}")
            return None
    
    def render_png_with_cache(self):
        """使用缓存机制渲染PNG预览"""
        if not self.current_pattern:
            return
        
        try:
            # 生成当前图案的哈希值
            current_hash = self.get_pattern_hash(self.current_pattern)
            
            # 检查是否可以使用缓存
            if (self.cached_png_image is not None and 
                self.cached_png_pattern_hash == current_hash and
                current_hash is not None):
                print("使用缓存的PNG图像")
                # 直接使用缓存的图像
                self.render_engine.base_image = self.cached_png_image
                self.display_rendered_image()
            else:
                print("生成新的PNG图像并缓存")
                # 生成新的PNG图像
                self.render_engine.create_base_image(self.current_pattern, 
                                                     self.preview_view.viewport().width(), 
                                                     self.preview_view.viewport().height())
                
                # 缓存生成的图像
                if self.render_engine.base_image and not self.render_engine.base_image.isNull():
                    self.cached_png_image = self.render_engine.base_image.copy()
                    self.cached_png_pattern_hash = current_hash
                    print(f"PNG图像已缓存，哈希值: {current_hash}")
                
                self.display_rendered_image()
                
        except Exception as e:
            print(f"PNG缓存渲染失败: {e}")
            # 回退到直接渲染
            self.render_engine.create_base_image(self.current_pattern, 
                                                 self.preview_view.viewport().width(), 
                                                 self.preview_view.viewport().height())
            self.display_rendered_image()
    

    

    

    


    def export_file(self):
        if not self.current_pattern:
            print("No pattern loaded to export.")
            return

        supported_write_formats = self.file_handler.get_supported_write_formats()
        if not supported_write_formats:
            print("No supported write formats available.")
            return
            
        filter_list = []
        for desc, ext in supported_write_formats.items():
            filter_list.append(f"{desc} (*.{ext.lower()})")
        filter_string = " ;; ".join(filter_list)

        # Use original filename as initial suggestion, format will be added dynamically
        initial_filename = self.original_file_name_stem if self.original_file_name_stem else "pattern"
        
        dialog = QFileDialog(self, "Export Embroidery File", initial_filename, filter_string)
        
        # Create a function to update filename based on selected filter
        def update_filename_for_format():
            selected_filter = dialog.selectedNameFilter()
            if not selected_filter or not self.original_file_name_stem:
                return
            
            # Parse the selected format extension from filter
            target_format_extension = None
            for desc, ext in supported_write_formats.items():
                if f"{desc} (*.{ext.lower()})" == selected_filter:
                    target_format_extension = ext
                    break
            
            if target_format_extension:
                # Generate dynamic filename: original_FORMAT.ext
                format_name_part = target_format_extension.upper()
                new_filename = f"{self.original_file_name_stem}_{format_name_part}.{target_format_extension.lower()}"
                dialog.selectFile(new_filename)
        
        # Connect the filter change signal to update filename dynamically
        dialog.filterSelected.connect(update_filename_for_format)
        
        # Set initial filename for first format
        if supported_write_formats and self.original_file_name_stem:
            first_format_desc = next(iter(supported_write_formats.keys()), None)
            if first_format_desc:
                first_format_ext = supported_write_formats[first_format_desc]
                format_name_part = first_format_ext.upper()
                initial_suggested = f"{self.original_file_name_stem}_{format_name_part}.{first_format_ext.lower()}"
                dialog.selectFile(initial_suggested)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        # Set default suffix based on the first filter if possible, or let user/dialog handle it.
        if filter_list:
            # Extract extension from the first filter, e.g., "DST Files (*.dst)" -> "dst"
            try:
                default_ext_candidate = filter_list[0].split('(*.')[-1][:-1]
                if default_ext_candidate and default_ext_candidate != '*':
                    dialog.setDefaultSuffix(default_ext_candidate.lower())
            except IndexError:
                pass # Could not parse default extension from filter string

        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            selected_filter_description = dialog.selectedNameFilter()
            
            # Fix: Parse the selected filter to get the correct format extension
            target_format_extension = None
            
            # First try direct lookup
            for desc, ext in supported_write_formats.items():
                if f"{desc} (*.{ext.lower()})" == selected_filter_description:
                    target_format_extension = ext
                    break
            
            if not target_format_extension:
                # Fallback: try to infer extension from selected filter string if it's like "Description (*.ext)"
                try:
                    if '(*.' in selected_filter_description and ')' in selected_filter_description:
                        ext_from_filter = selected_filter_description.split('(*.')[-1].split(')')[0]
                        if ext_from_filter and ext_from_filter != '*':
                            target_format_extension = ext_from_filter
                except Exception: # Broad catch if string splitting fails
                    pass

            if file_path and target_format_extension:
                # Ensure the file path has the correct extension based on the selected format
                # QFileDialog with setDefaultSuffix usually handles this, but good to double check or enforce.
                name, current_ext = os.path.splitext(file_path)
                expected_ext = f".{target_format_extension.lower()}"
                if current_ext.lower() != expected_ext:
                    file_path = name + expected_ext
                
                success = self.file_handler.write_pattern(self.current_pattern, file_path, target_format_extension)
                if success:
                    print(f"File exported successfully to {file_path}")
                    # Show success message to user
                    from PyQt6.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("Success")
                    msg.setText(f"The file was successfully exported to:\n{file_path}")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()
                else:
                    print(f"Failed to export file to {file_path}")
                    # Show error message to user
                    from PyQt6.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setWindowTitle("导出失败")
                    msg.setText(f"文件导出失败:\n{file_path}")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()
            elif file_path and not target_format_extension:
                print(f"Could not determine target format from selected filter: {selected_filter_description}. Please select a valid format.")
            # If file_path is empty, user cancelled, do nothing.


    def resizeEvent(self, event):
        super().resizeEvent(event)
        # When window resizes, we might want to re-fit the content if it's not zoomed/panned significantly
        # Or, if we want it to always fit unless user has interacted, call reset_preview()
        # For now, let QGraphicsView handle it with its anchors, or call fitInView if item exists.
        if self.current_pixmap_item and self.preview_view.transform().isIdentity():
             self.preview_view.fitInView(self.current_pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        elif self.current_pixmap_item: # If transformed, at least ensure scene rect is good
            self.preview_scene.setSceneRect(self.preview_scene.itemsBoundingRect())
        
        if self.lbl_loading_movie and self.lbl_loading_movie.isVisible():
            self.lbl_loading_movie.move(
                (self.preview_view.width() - self.lbl_loading_movie.width()) // 2,
                (self.preview_view.height() - self.lbl_loading_movie.height()) // 2
            )
            self.lbl_loading_movie.raise_()