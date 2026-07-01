# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_dpg.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Only icon.ico needs to be in datas — the .py modules are
        # bundled automatically by PyInstaller as frozen modules and
        # must NOT also be listed here or numpy gets double-loaded.
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'dearpygui',
        'dearpygui.dearpygui',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        'numpy.core.umath',
        'numpy.lib',
        'numpy.lib.stride_tricks',
        'numpy.linalg',
        'numpy.fft',
        'numpy.random',
        'pandas',
        'pandas.core',
        'pandas.core.frame',
        'pandas.core.series',
        'pandas.core.indexes',
        'pandas.io',
        'pandas.io.excel',
        'pandas.io.excel._openpyxl',
        'pandas.io.parsers',
        'pandas.io.parsers.readers',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'sqlite3',
        '_sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'customtkinter', 'PIL', 'test', 'unittest'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BeerCount',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='BeerCount',
)
