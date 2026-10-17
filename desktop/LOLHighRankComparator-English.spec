# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

root = Path(SPECPATH).parent
runtime_bin = Path(sys.prefix) / "Library" / "bin"
tk_binaries = [(str(runtime_bin / name), ".") for name in ("tcl86t.dll", "tk86t.dll") if (runtime_bin / name).exists()]

a = Analysis(
    [str(root / "desktop" / "lol_high_rank_comparator_en.py")],
    pathex=[str(root)], binaries=tk_binaries,
    datas=[
        (str(root / "desktop" / "all-champion-baselines.json"), "desktop"),
        (str(root / "assets" / "map11.png"), "assets"),
        (str(root / "assets" / "item-data.json"), "assets"),
        (str(root / "assets" / "summoner-spells.json"), "assets"),
        (str(root / "assets" / "ddragon"), "assets/ddragon"),
        (str(root / "config" / "model-parameters.json"), "config"),
        (str(Path(sys.prefix) / "Library" / "lib" / "tcl8.6"), "_tcl_data"),
        (str(Path(sys.prefix) / "Library" / "lib" / "tk8.6"), "_tk_data"),
    ],
    hiddenimports=["tkinter", "tkinter.ttk", "tkinter.messagebox", "desktop.english_ui"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="LOLHighRankComparator-English", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          disable_windowed_traceback=False, argv_emulation=False, target_arch=None,
          codesign_identity=None, entitlements_file=None, icon=None)
