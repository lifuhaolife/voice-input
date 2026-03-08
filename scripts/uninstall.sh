#!/bin/bash
# Uninstall voice-input system integration

echo "卸载语音输入工具..."

# Remove symbolic link
sudo rm -f /usr/local/bin/voice-input

# Remove desktop entry
rm -f ~/.local/share/applications/voice-input.desktop

# Remove autostart entry
rm -f ~/.config/autostart/voice-input.desktop

echo "✅ 卸载完成"