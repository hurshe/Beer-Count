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
        # DearPyGui
        'dearpygui',
        'dearpygui.dearpygui',
        # Numpy — must be fully specified for PyInstaller to bundle correctly
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        'numpy.core.umath',
        'numpy.core._dtype_ctypes',
        'numpy.lib',
        'numpy.lib.stride_tricks',
        'numpy.linalg',
        'numpy.fft',
        'numpy.random',
        'numpy.distutils',
        # Pandas
        'pandas',
        'pandas.core',
        'pandas.core.arrays',
        'pandas.core.arrays.integer',
        'pandas.core.arrays.floating',
        'pandas.core.arrays.string_',
        'pandas.core.arrays.boolean',
        'pandas.core.frame',
        'pandas.core.series',
        'pandas.core.indexes',
        'pandas.core.indexes.base',
        'pandas.core.indexes.range',
        'pandas.core.indexes.multi',
        'pandas.io',
        'pandas.io.excel',
        'pandas.io.excel._xlrd',
        'pandas.io.excel._openpyxl',
        'pandas.io.parsers',
        'pandas.io.parsers.readers',
        # Openpyxl
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        # SQLite
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
