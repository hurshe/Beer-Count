# -*- mode: python ; coding: utf-8 -*-
import os, sys

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')],
    hiddenimports=[
        'customtkinter',
        'customtkinter.windows',
        'customtkinter.windows.widgets',
        'customtkinter.windows.widgets.appearance_mode',
        'customtkinter.windows.widgets.color_manager',
        'customtkinter.windows.widgets.font',
        'customtkinter.windows.widgets.image',
        'customtkinter.windows.widgets.scaling',
        'customtkinter.windows.widgets.theme',
        'customtkinter.windows.widgets.utility',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'sqlite3',
        '_sqlite3',
        'tkinter',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

import customtkinter
ctk_dir = os.path.dirname(customtkinter.__file__)
a.datas += Tree(ctk_dir, prefix='customtkinter', excludes=['*.pyc'])

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
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BeerCount_HRC',
)
