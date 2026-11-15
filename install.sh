#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== Installing Whistle Assistant ==="
echo "Repository: ${REPO_DIR}"

# Check required system utilities
DEPENDENCIES=("python3" "alsa-utils" "wl-copy" "wtype")
MISSING=()
for dep in "${DEPENDENCIES[@]}"; do
    if ! command -v "$dep" &>/dev/null; then
        MISSING+=("$dep")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Warning: The following recommended system utilities were not found:"
    for m in "${MISSING[@]}"; do
        echo "  - $m"
    done
    echo "On Ubuntu / Debian, install them with:"
    echo "  sudo apt update && sudo apt install -y python3-venv alsa-utils wl-clipboard wtype libglib2.0-bin xdg-utils"
fi

# Set up Python virtual environment
if [ ! -d "${REPO_DIR}/.venv" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv "${REPO_DIR}/.venv"
fi

echo "Installing Python dependencies and packaging..."
"${REPO_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${REPO_DIR}/.venv/bin/python" -m pip install -e "${REPO_DIR}"

# Install desktop icons
echo "Installing application icons..."
ICON_DIR="${HOME}/.local/share/icons/hicolor"
mkdir -p "${ICON_DIR}/scalable/apps"
mkdir -p "${ICON_DIR}/128x128/apps"
mkdir -p "${ICON_DIR}/64x64/apps"
mkdir -p "${ICON_DIR}/48x48/apps"

if [ -f "${REPO_DIR}/assets/whistle.svg" ]; then
    cp "${REPO_DIR}/assets/whistle.svg" "${ICON_DIR}/scalable/apps/whistle.svg"
fi

# Render PNG icons if inkscape or rsvg-convert is present
if command -v rsvg-convert &>/dev/null; then
    rsvg-convert -w 128 -h 128 "${REPO_DIR}/assets/whistle.svg" -o "${ICON_DIR}/128x128/apps/whistle.png"
    rsvg-convert -w 64 -h 64 "${REPO_DIR}/assets/whistle.svg" -o "${ICON_DIR}/64x64/apps/whistle.png"
    rsvg-convert -w 48 -h 48 "${REPO_DIR}/assets/whistle.svg" -o "${ICON_DIR}/48x48/apps/whistle.png"
fi

# Register desktop entry
echo "Configuring GNOME desktop launcher..."
DESKTOP_DIR="${HOME}/.local/share/applications"
mkdir -p "${DESKTOP_DIR}"

cat <<EOF > "${DESKTOP_DIR}/whistle.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Whistle
GenericName=Voice Dictation & Assistant
Comment=Ultra-fast, privacy-first local voice dictation with technical WhisperFlow auto-correction
Exec="${REPO_DIR}/launch.sh"
Icon=whistle
Terminal=false
Categories=Utility;AudioVideo;Audio;
StartupWMClass=WhistleApp
Keywords=whistle;jarvis;voice;dictation;whisper;groq;speech;
EOF

chmod +x "${DESKTOP_DIR}/whistle.desktop"
chmod +x "${REPO_DIR}/launch.sh"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "${ICON_DIR}" 2>/dev/null || true
fi

echo "=== Whistle Assistant Installed Successfully! ==="
echo "You can launch Whistle from your applications menu or via:"
echo "  ${REPO_DIR}/launch.sh"
echo "CLI Commands:"
echo "  ${REPO_DIR}/.venv/bin/whistle       # Start web desktop interface"
echo "  ${REPO_DIR}/.venv/bin/whistle-hud   # Launch voice dictation HUD"
