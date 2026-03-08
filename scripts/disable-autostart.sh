#!/bin/bash
# Disable voice-input autostart

echo "取消开机自启动..."

rm -f ~/.config/autostart/voice-input.desktop

echo "✅ 已取消开机自启动"