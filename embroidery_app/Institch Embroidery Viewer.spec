# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\program\\pyembroidery0530\\pyembroidery\\embroidery_app\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\program\\pyembroidery0530\\pyembroidery\\embroidery_app\\loading.gif', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL', 'cv2', 'sklearn', 'tensorflow', 'torch', 'jupyter', 'IPython', 'test', 'unittest', 'doctest', 'pdb', 'sqlite3', 'xml', 'email', 'http', 'urllib', 'multiprocessing', 'concurrent'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    name='Institch Embroidery Viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['E:\\program\\pyembroidery0530\\pyembroidery\\embroidery_app\\te9wb-dqd91-001.ico'],
)
