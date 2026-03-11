#!/bin/bash
# Voice Input Launcher
# This script starts the voice input tool

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 解析参数
BACKGROUND=false
ARGS=()

for arg in "$@"; do
    case $arg in
        --background|-b)
            BACKGROUND=true
            ;;
        *)
            ARGS+=("$arg")
            ;;
    esac
done

# 检查 xdotool 依赖
if ! command -v xdotool &>/dev/null; then
    echo "安装 xdotool（用于直接文字输入）..."
    sudo apt install -y xdotool
fi

# Activate virtual environment and run
source venv/bin/activate

# Check if user is in input group
if ! groups | grep -q input; then
    echo "警告: 用户不在 input 组中，可能需要 sudo 权限"
    echo "请运行: sudo usermod -a -G input \$USER && 重新登录"
    echo ""
fi

# 构建运行命令
if [ -r /dev/input/event0 ]; then
    CMD="venv/bin/voice-input ${ARGS[*]}"
else
    echo "需要 sudo 权限访问输入设备..."
    CMD="sudo -E venv/bin/voice-input ${ARGS[*]}"
fi

# 根据参数决定前台或后台运行
if [ "$BACKGROUND" = true ]; then
    echo "启动语音输入（后台模式）..."
    nohup bash -c "$CMD" > /tmp/voice-input.log 2>&1 &
    echo $! > /tmp/voice-input.pid
    echo "语音输入已在后台启动，PID: $!"
    echo "日志输出: /tmp/voice-input.log"
else
    exec bash -c "$CMD"
fi