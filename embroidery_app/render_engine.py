from PyQt6.QtGui import QImage, QColor, QPainter
from PyQt6.QtCore import QRectF, QPointF
import io

# Attempt to import pyembroidery components.
# Import core components first
try:
    from pyembroidery import EmbPattern, STITCH, JUMP, END, COLOR_CHANGE, SEQUENCE_BREAK, TRIM, STOP
except ImportError as e_core_render:
    print(f"RenderEngine: Critical Warning - pyembroidery core components (EmbPattern, etc.) not found. Error: {e_core_render}")
    import traceback
    traceback.print_exc()
    class EmbPattern: pass # Dummy EmbPattern
    STITCH, JUMP, END, COLOR_CHANGE, SEQUENCE_BREAK, TRIM, STOP = 0,1,2,3,4,5,6 # Dummy constants

# Attempt to import PngWriter_write separately
try:
    from pyembroidery.PngWriter import write as PngWriter_write
except ImportError:
    PngWriter_write = None

import config # Application specific configuration

class RenderEngine:
    def __init__(self):
        self.base_image: QImage | None = None
        self.pattern_bounds_mm10: QRectF = QRectF() # Bounds in 1/10mm units
        self.background_color: QColor = config.DEFAULT_BACKGROUND_COLOR
        self.default_stitch_color: QColor = config.DEFAULT_STITCH_COLOR # Keep for potential fallback or other uses

    def create_base_image(self, pattern: EmbPattern, view_width_hint: int, view_height_hint: int):
        """Renders the full pattern to an off-screen QImage using PngWriter for efficient previewing."""
        if not pattern or (not pattern.stitches and not pattern.threadlist): # Check threadlist too, as some patterns might only have color info
            self.base_image = QImage(max(1, view_width_hint), max(1, view_height_hint), QImage.Format.Format_ARGB32_Premultiplied)
            self.base_image.fill(self.background_color)
            self.pattern_bounds_mm10 = QRectF()
            return

        self.pattern_bounds_mm10 = self._get_pattern_bounds_mm10(pattern)
        if not self.pattern_bounds_mm10.isValid() or self.pattern_bounds_mm10.isEmpty():
            self.base_image = QImage(max(1, view_width_hint), max(1, view_height_hint), QImage.Format.Format_ARGB32_Premultiplied)
            self.base_image.fill(self.background_color)
            return
        
        # Calculate optimal rendering parameters based on preview mode
        # Determine the scale factor based on pattern size and view size
        pattern_width_mm10 = self.pattern_bounds_mm10.width()
        pattern_height_mm10 = self.pattern_bounds_mm10.height()
        
        # 优化PNG预览设置 - 平衡质量和加载速度
        target_pixels = max(2000, view_width_hint * 2, view_height_hint * 2)  # 适中的目标像素数
        min_scale = 2.0  # 适中的最小缩放比例
        max_scale = 60.0  # 适中的最大缩放比例
            
        if pattern_width_mm10 > 0 and pattern_height_mm10 > 0:
            scale_x = target_pixels / pattern_width_mm10 if pattern_width_mm10 > 0 else 1.0
            scale_y = target_pixels / pattern_height_mm10 if pattern_height_mm10 > 0 else 1.0
            optimal_scale = min(scale_x, scale_y)
            # Ensure minimum scale for very large patterns
            optimal_scale = max(optimal_scale, min_scale)
            # Cap maximum scale for very small patterns to avoid excessive memory usage
            optimal_scale = min(optimal_scale, max_scale)
        else:
            optimal_scale = config.INITIAL_RENDER_SCALE
        
        # Use a copy of the pattern for rendering to avoid modifying the original
        pattern_copy = pattern.copy()
        
        # Scale the pattern copy for high-resolution rendering using transform matrix
        if optimal_scale != 1.0:
            try:
                from pyembroidery.EmbMatrix import EmbMatrix
                scale_matrix = EmbMatrix(EmbMatrix.get_scale(optimal_scale, optimal_scale))
                pattern_copy.transform(scale_matrix)
            except (ImportError, AttributeError):
                # Fallback to scale method if EmbMatrix is not available
                pattern_copy.scale(optimal_scale)
        
        # 优化线宽计算 - 平衡视觉效果和性能
        line_width = max(2, int(optimal_scale * 0.8))  # 减少线宽因子
        
        # 优化PNG设置 - 支持渐变效果
        png_settings = {
            "linewidth": line_width,
            "fancy": True,  # Enable gradient effect
            "background": None,  # 透明背景
        }
        
        print(f"RenderEngine: [create_base_image] Optimal scale: {optimal_scale:.2f}, Line width: {line_width}")
        print(f"RenderEngine: [create_base_image] Pattern size: {pattern_width_mm10:.1f}x{pattern_height_mm10:.1f} mm/10")
        print(f"RenderEngine: [create_base_image] View hint: {view_width_hint}x{view_height_hint}")
        # If PngWriter doesn't support transparent background, we might need to render on white
        # and then make white pixels transparent, or fill a QImage with background_color first
        # and then draw the PngWriter output (if it has alpha) on top.

        try:
            if PngWriter_write is None:
                return
            
            print("RenderEngine: [create_base_image] Attempting PngWriter.write...")
            img_buffer = io.BytesIO()
            PngWriter_write(pattern_copy, img_buffer, settings=png_settings)
            print("RenderEngine: [create_base_image] PngWriter.write completed.")
            img_buffer.seek(0)
            
            self.base_image = QImage()
            print("RenderEngine: [create_base_image] Attempting QImage.loadFromData...")
            buffer_value = img_buffer.getvalue()
            print(f"RenderEngine: [create_base_image] Buffer size for loadFromData: {len(buffer_value)} bytes")
            load_success = self.base_image.loadFromData(buffer_value, "PNG")
            print(f"RenderEngine: [create_base_image] QImage.loadFromData success: {load_success}")
            
            if load_success:
                print(f"RenderEngine: [create_base_image] Image loaded successfully: {self.base_image.width()}x{self.base_image.height()}, format: {self.base_image.format()}")
                # 保持PNG的透明背景，让背景颜色变化能够更好地融入环境
                # 如果PNG有透明背景，我们保持它；如果没有，我们创建一个带透明背景的版本
                if self.base_image.hasAlphaChannel():
                    # PNG已经有透明背景，直接使用
                    print("RenderEngine: PNG has alpha channel, keeping transparent background")
                else:
                    # 将白色背景转换为透明背景
                    print("RenderEngine: Converting white background to transparent")
                    final_image = QImage(self.base_image.size(), QImage.Format.Format_ARGB32_Premultiplied)
                    final_image.fill(QColor(0, 0, 0, 0))  # 透明背景
                    
                    painter = QPainter(final_image)
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                    
                    # 遍历每个像素，将白色或接近白色的像素设为透明
                    for y in range(self.base_image.height()):
                        for x in range(self.base_image.width()):
                            pixel = self.base_image.pixel(x, y)
                            color = QColor(pixel)
                            # 如果像素接近白色（RGB值都大于240），设为透明
                            if color.red() > 240 and color.green() > 240 and color.blue() > 240:
                                continue  # 跳过白色像素（保持透明）
                            else:
                                painter.setPen(color)
                                painter.drawPoint(x, y)
                    
                    painter.end()
                    self.base_image = final_image
            else:
                print("RenderEngine: Error - Could not load image from PngWriter buffer.")
                self.base_image = QImage(max(1, view_width_hint), max(1, view_height_hint), QImage.Format.Format_ARGB32_Premultiplied)
                self.base_image.fill(self.background_color) # Use configured background
                self.pattern_bounds_mm10 = QRectF()

        except Exception as e:
            print(f"RenderEngine: Error during PngWriter rendering or QImage loading: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for Python exceptions
            self.base_image = QImage(max(1, view_width_hint), max(1, view_height_hint), QImage.Format.Format_ARGB32_Premultiplied)
            self.base_image.fill(self.background_color) # Use configured background
            self.pattern_bounds_mm10 = QRectF()

    def _get_pattern_bounds_mm10(self, pattern: EmbPattern) -> QRectF:
        """Calculates the bounding box of the pattern stitches in 1/10mm units."""
        if not pattern or not hasattr(pattern, 'bounds') or not pattern.stitches:
            return QRectF() # Invalid or empty pattern
        
        b = pattern.bounds()
        min_x, min_y, max_x, max_y = b[0], b[1], b[2], b[3]
        return QRectF(QPointF(min_x, min_y), QPointF(max_x, max_y))

    def set_background_color(self, color: QColor):
        self.background_color = color
        # Re-render should be triggered by the caller (e.g., main_window)

    # The get_next_random_color method is no longer needed here as PngWriter handles colors.
    # If PngWriter fails to find colors in a pattern, it usually defaults to black or its own scheme.

    # get_rendered_image and transform methods are removed as QGraphicsView/QGraphicsItem handle this.

if __name__ == '__main__':
    # This part is for basic testing of RenderEngine if run directly.
    # Requires QApplication for QImage/QPainter to work correctly.
    from PyQt6.QtWidgets import QApplication
    app = QApplication([]) # Dummy app for Qt resources

    engine = RenderEngine()
    
    # --- Mock EmbPattern for testing --- 
    try:
        mock_pattern = EmbPattern()
        mock_pattern.add_thread({"color": 0xFF0000, "description": "Red", "catalog_number": "R1"})
        mock_pattern.add_thread({"color": 0x00FF00, "description": "Green", "catalog_number": "G1"})
        mock_pattern.add_thread({"color": 0x0000FF, "description": "Blue", "catalog_number": "B1"})

        mock_pattern.add_stitch_absolute(0, 0, STITCH)
        mock_pattern.add_stitch_absolute(100, 0, STITCH)
        mock_pattern.add_stitch_absolute(100, 100, STITCH)
        mock_pattern.add_stitch_absolute(0, 100, STITCH)
        mock_pattern.add_stitch_absolute(0, 0, STITCH)
        
        mock_pattern.add_stitch_absolute(0,0, COLOR_CHANGE) 

        mock_pattern.add_stitch_absolute(50, 50, JUMP)
        mock_pattern.add_stitch_absolute(150, 50, STITCH)
        mock_pattern.add_stitch_absolute(150, 150, STITCH)
        mock_pattern.add_stitch_absolute(50, 150, STITCH)
        mock_pattern.add_stitch_absolute(50, 50, STITCH)
        mock_pattern.add_stitch_absolute(0,0, END)

        print(f"Pattern bounds (mm/10): {engine._get_pattern_bounds_mm10(mock_pattern)}")

        engine.create_base_image(mock_pattern, 500, 400)
        if engine.base_image:
            print(f"Base image created: {engine.base_image.width()}x{engine.base_image.height()}")
            # For testing, save the image
            # engine.base_image.save("test_render_engine_base_image.png")
            # print("Saved test_render_engine_base_image.png")
        else:
            print("Failed to create base image.")

    except NameError: # If EmbPattern etc. were not defined due to import error
        print("Mock pattern test skipped: pyembroidery constants not available.")
    except Exception as e:
        print(f"Error during RenderEngine test: {e}")
    
    # app.exec() # Keep event loop running if needed for more complex Qt tests