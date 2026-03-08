#!/bin/bash
# Setup voice-input to start automatically on login

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "设置开机自启动..."

# Create autostart directory
mkdir -p ~/.config/autostart

# Create autostart desktop entry
cat > ~/.config/autostart/voice-input.desktop << EOF
[Desktop Entry]
Version=1.0
Name=Voice Input (Autostart)
Comment=Voice-to-text input tool
Exec=$PROJECT_DIR/scripts/voice-input.sh
Icon=audio-input-microphone
Terminal=false
Type=Application
X-GNOME-Autostart-enabled=true
EOF

echo "✅ 已设置开机自启动"
echo ""
echo "管理自启动:"
echo "  禁用: rm ~/.config/autostart/voice-input.desktop"
echo "  或在 '启动应用程序' 中管理"