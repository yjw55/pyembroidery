#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller build script for Institch Embroidery Viewer
"""

import subprocess
import sys
import os

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully.")

def build_exe():
    """Build the executable using PyInstaller with optimization"""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    main_script = os.path.join(current_dir, "main.py")
    icon_path = os.path.join(current_dir, "te9wb-dqd91-001.ico")
    loading_gif = os.path.join(current_dir, "loading.gif")
    
    # Check if files exist
    if not os.path.exists(main_script):
        print(f"Error: {main_script} not found!")
        return False
    
    if not os.path.exists(icon_path):
        print(f"Warning: {icon_path} not found! Building without icon.")
        icon_path = None
    
    # Build PyInstaller command with optimization
    cmd = [
        "pyinstaller",
        "--onefile",  # Create a single executable file
        "--windowed",  # No console window (GUI app)
        "--name", "Institch Embroidery Viewer",  # Executable name
        "--optimize", "2",  # Python optimization level
        "--strip",  # Strip debug symbols (Linux/Mac)
        "--noupx",  # Disable UPX compression (can cause issues)
        # Exclude unnecessary modules to reduce size
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "sklearn",
        "--exclude-module", "tensorflow",
        "--exclude-module", "torch",
        "--exclude-module", "jupyter",
        "--exclude-module", "IPython",
        "--exclude-module", "test",
        "--exclude-module", "unittest",
        "--exclude-module", "doctest",
        "--exclude-module", "pdb",
        "--exclude-module", "sqlite3",
        "--exclude-module", "xml",
        "--exclude-module", "email",
        "--exclude-module", "http",
        "--exclude-module", "urllib",
        "--exclude-module", "multiprocessing",
        "--exclude-module", "concurrent",
    ]
    
    # Add icon if available
    if icon_path:
        cmd.extend(["--icon", icon_path])
    
    # Add data files
    if os.path.exists(loading_gif):
        cmd.extend(["--add-data", f"{loading_gif};."])
    
    # Add the main script
    cmd.append(main_script)
    
    print(f"Building optimized executable...")
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        
        # Get file size
        exe_path = os.path.join(current_dir, 'dist', 'Institch Embroidery Viewer.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Executable size: {size_mb:.2f} MB")
        
        print(f"Executable created in: {os.path.join(current_dir, 'dist')}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    print("Building optimized Institch Embroidery Viewer executable...")
    
    # Install PyInstaller if needed
    install_pyinstaller()
    
    # Build the executable
    success = build_exe()
    
    if success:
        print("\nOptimized build completed! You can find the executable in the 'dist' folder.")
    else:
        print("\nBuild failed. Please check the error messages above.")
    
    input("Press Enter to exit...")