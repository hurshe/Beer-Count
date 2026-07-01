# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_dpg.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('pos_import.py', '.'),
        ('database.py', '.'),
        ('export_excel.py', '.'),
    ],
    hiddenimports=[
        'dearpygui',
        'dearpygui.dearpygui',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'sqlite3',
        '_sqlite3',
        'pandas',
        'pandas.core',
        'pandas.io.excel',
        'pandas.io.parsers',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'customtkinter', 'PIL'],
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
