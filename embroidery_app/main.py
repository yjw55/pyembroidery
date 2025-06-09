import sys
import os

# Add the parent directory (pyembroidery) to sys.path to find the pyembroidery library
# This is necessary if running main.py directly and pyembroidery is not installed as a package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # This should be the 'pyembroidery' directory
# Add the directory containing the 'pyembroidery' package (i.e., the grandparent 'pyembroidery0530')
# if the 'pyembroidery' library itself is in 'e:\program\pyembroidery0530\pyembroidery\pyembroidery'
# sys.path.insert(0, os.path.dirname(parent_dir)) # To find the 'pyembroidery' package
# If 'pyembroidery' is directly importable because 'e:\program\pyembroidery0530\pyembroidery' is the package root:
sys.path.insert(0, parent_dir)

print("DEBUG: sys.path modified. Current sys.path:")
for p_idx, p_val in enumerate(sys.path):
    print(f"  sys.path[{p_idx}]: {p_val}")

try:
    print("DEBUG: Attempting to import EmbPattern from pyembroidery...")
    from pyembroidery import EmbPattern
    print("DEBUG: Successfully imported EmbPattern from pyembroidery.")
except ImportError as e:
    print(f"DEBUG: Failed to import EmbPattern from pyembroidery. Error: {e}")
    print("DEBUG: Traceback for pyembroidery import failure:")
    import traceback
    traceback.print_exc()
except Exception as e_gen:
    print(f"DEBUG: An unexpected error occurred during pyembroidery import: {e_gen}")
    import traceback
    traceback.print_exc()


from PyQt6.QtWidgets import QApplication, QStyleFactory
# Assuming main_window.py is in the same directory (embroidery_app)
from main_window import MainWindow
import config # Import config to make its constants available early if needed

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    # Set a nicer style if available (e.g., 'Fusion')
    if 'Fusion' in QStyleFactory.keys():
        QApplication.setStyle('Fusion')

    window = MainWindow()
    window.show()
    sys.exit(app.exec())