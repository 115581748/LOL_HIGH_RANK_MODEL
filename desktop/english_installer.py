"""Per-user Windows installer for the English RiftScale desktop build."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "RiftScale"
SOURCE_EXE = "LOLHighRankComparator-English.exe"


def bundled_path(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def destination() -> tuple[Path, Path]:
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    roaming = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    return local / "Programs" / APP_NAME, roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"


def create_shortcut(shortcut: Path, target: Path) -> None:
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        "$link = $shell.CreateShortcut($env:RIFTSCALE_SHORTCUT); "
        "$link.TargetPath = $env:RIFTSCALE_TARGET; "
        "$link.WorkingDirectory = $env:RIFTSCALE_DIRECTORY; "
        "$link.Description = 'RiftScale - League of Legends match review'; "
        "$link.IconLocation = $env:RIFTSCALE_TARGET; "
        "$link.Save()"
    )
    env = dict(os.environ, RIFTSCALE_SHORTCUT=str(shortcut), RIFTSCALE_TARGET=str(target), RIFTSCALE_DIRECTORY=str(target.parent))
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=env, check=True, timeout=20, capture_output=True,
    )


def install() -> Path:
    source = bundled_path(SOURCE_EXE)
    readme = bundled_path("README-English.txt")
    if not source.is_file() or not readme.is_file():
        raise FileNotFoundError("Installer payload is incomplete.")
    directory, shortcut = destination()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "RiftScale.exe"
    staging = directory / "RiftScale.exe.next"
    try:
        shutil.copy2(source, staging)
        os.replace(staging, target)
        shutil.copy2(readme, directory / "README.txt")
        create_shortcut(shortcut, target)
    finally:
        staging.unlink(missing_ok=True)
    return target


def main() -> int:
    if "--smoke-check" in sys.argv:
        import tkinter as tk
        window = tk.Tk()
        window.withdraw()
        window.update()
        window.destroy()
        return 0
    if "--quiet" in sys.argv:
        try:
            print(install())
            return 0
        except Exception as exc:
            print(f"Installation failed: {exc}", file=sys.stderr)
            return 1

    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("RiftScale · English Setup")
    root.geometry("470x270")
    root.resizable(False, False)
    root.configure(bg="#081217")
    app_dir, _shortcut = destination()
    tk.Label(root, text="RiftScale", bg="#081217", fg="#e9bd59", font=("Segoe UI", 25, "bold")).pack(anchor="w", padx=28, pady=(22, 3))
    tk.Label(root, text="League of Legends match review · English test build", bg="#081217", fg="#8ba6ae", font=("Segoe UI", 10)).pack(anchor="w", padx=28)
    tk.Label(root, text=f"Install for this Windows user:\n{app_dir}", bg="#081217", fg="#dbe8ed", justify="left", wraplength=410, font=("Segoe UI", 9)).pack(anchor="w", padx=28, pady=(26, 4))
    status = tk.StringVar(value="No administrator access is required.")
    tk.Label(root, textvariable=status, bg="#081217", fg="#67ded7", font=("Segoe UI", 9)).pack(anchor="w", padx=28, pady=(2, 16))

    def on_install() -> None:
        button.configure(state="disabled")
        status.set("Installing…")
        root.update_idletasks()
        try:
            target = install()
        except Exception as exc:
            status.set("Installation failed.")
            button.configure(state="normal")
            messagebox.showerror("RiftScale Setup", str(exc), parent=root)
            return
        status.set("Installed. Open RiftScale from the Start menu.")
        button.configure(text="Launch RiftScale", command=lambda: subprocess.Popen([str(target)], cwd=target.parent))

    row = ttk.Frame(root)
    row.pack(anchor="e", padx=28)
    button = ttk.Button(row, text="Install", command=on_install)
    button.pack(side="left", padx=(0, 8))
    ttk.Button(row, text="Close", command=root.destroy).pack(side="left")
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
