# Datascope.spec
# Works with Python 3.12 + PyInstaller
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import os

# Pull in pandas/numpy fully (data files, binaries, etc.)
pandas_datas, pandas_bins, pandas_hooks = collect_all("pandas")
numpy_datas, numpy_bins, numpy_hooks   = collect_all("numpy")

# If your app has other local modules, list them here so PyInstaller
# won't miss them even if they are dynamically imported somewhere.
hiddenimports = [
    "data_handler",
    "data_view",
    "enhanced_data_view",
    "recommendation_engine",
    "recommendation_ui",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
]

block_cipher = None

a = Analysis(
    ["src/datascope_UI.py"],
    pathex=["./src"],                     # <<— make src importable
    binaries=pandas_bins + numpy_bins,
    datas=[("assets", "assets")] + pandas_datas + numpy_datas,
    hiddenimports=hiddenimports,
    hookspath=pandas_hooks + numpy_hooks,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Datascope",
    icon="assets/app.ico",                # omit or change if you want
    console=False,                         # set False later if you want no console
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Datascope",
)
