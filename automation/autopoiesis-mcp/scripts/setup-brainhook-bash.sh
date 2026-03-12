#!/bin/bash
# Setup brainhook bash command for external toggle
# Installs to /usr/local/bin (requires sudo) or ~/.local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAINHOOK_SCRIPT="$SCRIPT_DIR/brainhook.sh"

# Check if script exists
if [[ ! -f "$BRAINHOOK_SCRIPT" ]]; then
    echo "Error: brainhook.sh not found at $BRAINHOOK_SCRIPT" >&2
    exit 1
fi

# Try /usr/local/bin first (preferred, in PATH by default)
if [[ -w /usr/local/bin ]] || sudo -n true 2>/dev/null; then
    echo "Installing brainhook to /usr/local/bin..."
    if [[ -w /usr/local/bin ]]; then
        cp "$BRAINHOOK_SCRIPT" /usr/local/bin/brainhook
        chmod 755 /usr/local/bin/brainhook
    else
        sudo cp "$BRAINHOOK_SCRIPT" /usr/local/bin/brainhook
        sudo chmod 755 /usr/local/bin/brainhook
    fi
    echo "✅ Installed to /usr/local/bin/brainhook"
else
    # Fall back to ~/.local/bin
    mkdir -p ~/.local/bin
    cp "$BRAINHOOK_SCRIPT" ~/.local/bin/brainhook
    chmod 755 ~/.local/bin/brainhook
    echo "✅ Installed to ~/.local/bin/brainhook"

    # Check if ~/.local/bin is in PATH
    if ! echo "$PATH" | tr ':' '\n' | grep -q "^$HOME/.local/bin$"; then
        echo ""
        echo "⚠️  ~/.local/bin is not in your PATH"
        echo "   Add this to your ~/.bashrc or ~/.zshrc:"
        echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

echo ""
echo "Usage in Claude Code: !brainhook"
echo "This toggles the brainhook on/off externally."
