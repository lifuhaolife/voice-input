#!/bin/bash
# Voice Input Launcher
# This script starts the voice input tool

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment and run
source venv/bin/activate

# Check if user is in input group
if ! groups | grep -q input; then
    echo "警告: 用户不在 input 组中，可能需要 sudo 权限"
    echo "请运行: sudo usermod -a -G input \$USER && 重新登录"
    echo ""
fi

# Run with sudo if needed for device access
if [ -r /dev/input/event0 ]; then
    exec venv/bin/voice-input "$@"
else
    echo "需要 sudo 权限访问输入设备..."
    exec sudo -E venv/bin/voice-input "$@"
fi