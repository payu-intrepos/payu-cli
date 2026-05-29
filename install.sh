#!/usr/bin/env bash
# Quick installer for payu-cli.
#
# Usage:
#   curl -fsSL https://payu.in/cli/install.sh | bash
#
# Or download manually:
#   curl -fsSL https://payu.in/cli/latest/payu_mac-os_arm64.tar.gz | tar -xz
#   sudo mv payu /usr/local/bin/

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────
CLI_NAME="payu"
GITHUB_REPO="${PAYU_CLI_REPO:-payu-intrepos/payu-cli}"
BASE_URL="${PAYU_CLI_BASE_URL:-https://github.com/${GITHUB_REPO}/releases/latest/download}"
INSTALL_DIR="${PAYU_CLI_INSTALL_DIR:-$HOME/.local/bin}"

# ── Detect platform ───────────────────────────────────────────────
detect_os() {
    case "$(uname -s)" in
        Darwin) echo "mac-os" ;;
        Linux)  echo "linux"  ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *) echo "unsupported" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64) echo "x86_64" ;;
        aarch64|arm64) echo "arm64"  ;;
        *) echo "unsupported" ;;
    esac
}

OS="$(detect_os)"
ARCH="$(detect_arch)"

if [ "$OS" = "unsupported" ] || [ "$ARCH" = "unsupported" ]; then
    echo "Error: Unsupported platform — $(uname -s) $(uname -m)" >&2
    echo "Supported: macOS (arm64, x86_64), Linux (arm64, x86_64)" >&2
    exit 1
fi

if [ "$OS" = "windows" ]; then
    echo "On Windows, run this in PowerShell instead:" >&2
    echo "" >&2
    echo "  irm https://raw.githubusercontent.com/payu-intrepos/payu-cli/main/install.ps1 | iex" >&2
    echo "" >&2
    echo "Or download manually: ${BASE_URL}/payu_windows_x86_64.zip" >&2
    exit 1
fi

TARBALL="${CLI_NAME}_${OS}_${ARCH}.tar.gz"
URL="${BASE_URL}/${TARBALL}"

# ── Download & install ────────────────────────────────────────────
echo "Downloading ${CLI_NAME} for ${OS}/${ARCH}..."
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

if ! curl -fsSL "$URL" -o "$TMPDIR/$TARBALL"; then
    echo "Error: Failed to download $URL" >&2
    echo "Check your network or try downloading manually." >&2
    exit 1
fi

echo "Extracting..."
tar -xzf "$TMPDIR/$TARBALL" -C "$TMPDIR"
chmod +x "$TMPDIR/$CLI_NAME"

# Remove macOS quarantine if present
if [ "$OS" = "mac-os" ] && command -v xattr &>/dev/null; then
    xattr -d com.apple.quarantine "$TMPDIR/$CLI_NAME" 2>/dev/null || true
fi

echo "Installing to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
mv "$TMPDIR/$CLI_NAME" "$INSTALL_DIR/$CLI_NAME"

# ── PATH check ────────────────────────────────────────────────────
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    SHELL_NAME="$(basename "$SHELL")"
    case "$SHELL_NAME" in
        zsh)  RC_FILE="$HOME/.zshrc" ;;
        bash) RC_FILE="$HOME/.bashrc" ;;
        fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
        *)    RC_FILE="$HOME/.profile" ;;
    esac

    echo ""
    echo "⚠  ${INSTALL_DIR} is not in your PATH."
    echo "   Add it by running:"
    echo ""
    if [ "$SHELL_NAME" = "fish" ]; then
        echo "   fish_add_path ${INSTALL_DIR}"
    else
        echo "   echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ${RC_FILE}"
    fi
    echo ""
    echo "   Then restart your terminal or run: source ${RC_FILE}"
fi

echo ""
echo "✓ ${CLI_NAME} installed successfully!"
echo ""
echo "Get started:"
echo "  ${CLI_NAME} version              # verify installation"
echo "  ${CLI_NAME} config set            # configure credentials"
echo "  ${CLI_NAME} --help                # see all commands"
