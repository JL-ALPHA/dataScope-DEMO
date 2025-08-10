import logging
import subprocess
from pathlib import Path
import shutil
import os

def main():
    logging.basicConfig(level=logging.INFO)
    project_root = Path(__file__).parent.resolve()
    entry = project_root / "src" / "datascope_UI.py"

    if not entry.exists():
        raise FileNotFoundError(f"Cannot find entry script: {entry}")

    # Clean previous builds
    dist = project_root / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    logging.info("Cleaned old dist folder.")

    # Full path to the Flet CLI
    flet_cli = (
        Path(os.environ["LOCALAPPDATA"]) /
        "Packages" /
        "PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0" /
        "LocalCache" /
        "local-packages" /
        "Python313" /
        "Scripts" /
        "flet.exe"
    )

    cmd = [
        str(flet_cli),
        "pack",
        str(entry),
        "--name", "datascope_app",
        "--yes",
        # tell PyInstaller to look in src/ for imports
        "--paths", str(project_root / "src"),
        # bundle local module and its deps
        "--hidden-import", "data_handler",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        # bundle your assets folder
        "--add-data", f"{project_root/'assets'};assets",
    ]

    logging.info("Running: %s", " ".join(cmd))
    print("🚀 Packaging Datascope…")
    subprocess.check_call(cmd)

    print(f"✅ Done! Your standalone app is in:\n   {dist/'datascope_app'}")

if __name__ == "__main__":
    main()
