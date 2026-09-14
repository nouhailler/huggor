#!/usr/bin/env python3
"""Construire le paquet Debian sans inclure de données utilisateur."""

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("La version doit respecter le format X.Y.Z")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hf-explorer-deb-") as temp:
        package = Path(temp)
        app = package / "usr/share/hf-explorer"
        app.mkdir(parents=True)
        for filename in ("app.py", "requirements.txt", "README.md"):
            shutil.copy2(ROOT / filename, app / filename)
        shutil.copytree(ROOT / "src", app / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        binary = package / "usr/bin/hf-explorer"
        binary.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/hf-explorer", binary)
        binary.chmod(0o755)
        desktop = package / "usr/share/applications"
        desktop.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/hf-explorer.desktop", desktop)
        control = package / "DEBIAN"
        control.mkdir()
        installed_size = (sum(p.stat().st_size for p in package.rglob("*") if p.is_file()) + 1023) // 1024
        (control / "control").write_text(
            f"Package: hf-explorer\nVersion: {args.version}\nSection: science\nPriority: optional\n"
            "Architecture: all\nMaintainer: Huggor contributors <nouhailler@users.noreply.github.com>\n"
            "Depends: python3 (>= 3.10), python3-venv, ca-certificates, util-linux\n"
            f"Installed-Size: {installed_size}\n"
            "Homepage: https://github.com/nouhailler/huggor\n"
            "Description: Interface locale pour explorer les modeles Hugging Face\n"
            " Recherche, fiches techniques, comparaison et statistiques avec Gradio.\n"
            " Internet est necessaire au premier lancement pour installer les\n"
            " dependances Python dans un environnement isole par utilisateur.\n",
            encoding="utf-8",
        )
        package.chmod(0o755)
        for path in package.rglob("*"):
            path.chmod(0o755 if path.is_dir() or path == binary else 0o644)
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(package),
                        str(output / f"hf-explorer_{args.version}_all.deb")], check=True)


if __name__ == "__main__":
    main()
