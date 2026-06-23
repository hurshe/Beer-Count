# -*- mode: python ; coding: utf-8 -*-
import os, sys

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.'), ('pos_import.py', '.')],
    hiddenimports=[
        'tkinter',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.ttk',
        '_tkinter',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'sqlite3',
        '_sqlite3',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pandas',
        'pandas.core',
        'pandas.io.excel',
        'pandas.io.parsers',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BeerCount_HRC',
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
    name='BeerCount_HRC',
)
