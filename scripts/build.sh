#!/usr/bin/env bash
# Build standalone payu binary for the current platform.
# Usage: ./scripts/build.sh
#
# Prerequisites (one-time):
#   pip install pyinstaller
#
# Output: dist/payu  (single file, no Python needed to run it)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Installing dependencies..."
pip install -q . pyinstaller

echo "==> Building standalone binary..."
pyinstaller payu.spec --clean --noconfirm

# Detect OS and arch for the tarball name
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$OS" in
    darwin) OS="mac-os" ;;
    linux)  OS="linux"  ;;
    *)      OS="$OS"    ;;
esac
case "$ARCH" in
    x86_64)  ARCH="x86_64"  ;;
    aarch64|arm64) ARCH="arm64" ;;
esac

VERSION="$(python -c 'from payu_cli import __version__; print(__version__)')"
TARBALL="payu_${OS}_${ARCH}.tar.gz"

echo "==> Packaging dist/payu → dist/${TARBALL}"
cd dist
tar -czf "$TARBALL" payu
cd ..

echo ""
echo "✓ Built: dist/payu  ($(du -h dist/payu | cut -f1) standalone binary)"
echo "✓ Archive: dist/${TARBALL}"
echo ""
echo "Test it:  ./dist/payu version"
