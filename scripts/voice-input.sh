#!/bin/bash
# Voice Input Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 解析参数
BACKGROUND=false
for arg in "$@"; do
    case $arg in
        --background|-b) BACKGROUND=true ;;
    esac
done

# 激活虚拟环境
source venv/bin/activate

# 单例检查
if [ -f /tmp/voice-input.lock ]; then
    EXISTING_PID=$(cat /tmp/voice-input.lock 2>/dev/null)
    if [ -n "$EXISTING_PID" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        echo "❌ 语音输入已在运行 (PID: $EXISTING_PID)"
        echo "   如需重启，请先运行：kill $EXISTING_PID"
        exit 1
    fi
    rm -f /tmp/voice-input.lock
fi

# 构建命令
if [ -r /dev/input/event0 ]; then
    CMD="venv/bin/voice-input"
else
    CMD="sudo -E venv/bin/voice-input"
fi

# 后台运行
if [ "$BACKGROUND" = true ]; then
    echo "启动语音输入（后台模式）..."
    nohup bash -c "$CMD" > /tmp/voice-input.log 2>&1 &
    echo "语音输入已在后台启动，PID: $!"
    echo "日志输出：/tmp/voice-input.log"
else
    exec bash -c "$CMD"
fi
