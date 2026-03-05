#!/usr/bin/env python3
"""
Build helper — wraps PyInstaller and optionally zips the result.

Usage
-----
    python build.py            Build only
    python build.py --zip      Build + create distributable zip
    python build.py --clean    Remove previous build artifacts first
"""

import argparse
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / 'music_analysis.spec'
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'
APP_NAME = 'MusicAnalysis'


def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print('ERROR: PyInstaller is not installed.')
        print('  Install it with:  pip install pyinstaller')
        sys.exit(1)


def clean():
    for d in (DIST, BUILD):
        if d.exists():
            print(f'Removing {d} ...')
            shutil.rmtree(d)


def build():
    cmd = [sys.executable, '-m', 'PyInstaller', str(SPEC), '--noconfirm']
    print(f'Running: {" ".join(cmd)}\n')
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f'\nBuild FAILED (exit code {result.returncode}).')
        sys.exit(result.returncode)
    print('\nBuild succeeded.')


def folder_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    return total / (1024 * 1024)


def make_zip():
    os_tag = {
        'Windows': 'windows',
        'Darwin': 'macos',
        'Linux': 'linux',
    }.get(platform.system(), platform.system().lower())

    app_dir = DIST / APP_NAME
    if not app_dir.exists():
        print(f'ERROR: {app_dir} not found. Did the build succeed?')
        sys.exit(1)

    zip_name = f'{APP_NAME}-{os_tag}.zip'
    zip_path = DIST / zip_name
    print(f'\nCreating {zip_path} ...')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in app_dir.rglob('*'):
            if file.is_file():
                arcname = f'{APP_NAME}/{file.relative_to(app_dir)}'
                zf.write(file, arcname)

    zip_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f'  {zip_name}: {zip_mb:.1f} MB')
    return zip_path


def main():
    parser = argparse.ArgumentParser(description='Build MusicAnalysis executable')
    parser.add_argument('--zip', action='store_true',
                        help='Create a distributable zip after building')
    parser.add_argument('--clean', action='store_true',
                        help='Remove build/ and dist/ before building')
    args = parser.parse_args()

    check_pyinstaller()

    if args.clean:
        clean()

    build()

    app_dir = DIST / APP_NAME
    if app_dir.exists():
        size = folder_size_mb(app_dir)
        print(f'\nOutput:  {app_dir}')
        print(f'Size:    {size:.0f} MB')

        if platform.system() == 'Windows':
            print(f'Run:     {app_dir / (APP_NAME + ".exe")}')
        elif platform.system() == 'Darwin':
            mac_app = DIST / f'{APP_NAME}.app'
            if mac_app.exists():
                print(f'Run:     open {mac_app}')
            else:
                print(f'Run:     {app_dir / APP_NAME}')
        else:
            print(f'Run:     {app_dir / APP_NAME}')

    if args.zip:
        make_zip()


if __name__ == '__main__':
    main()
