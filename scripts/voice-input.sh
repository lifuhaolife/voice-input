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

# 锁文件路径（与 process_lock.py 保持一致）
LOCK_FILE="$HOME/.local/share/voice-input/voice-input.lock"

# 单例检查
if [ -f "$LOCK_FILE" ]; then
    EXISTING_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$EXISTING_PID" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        echo "❌ 语音输入已在运行 (PID: $EXISTING_PID)"
        echo "   如需重启，请先运行：kill $EXISTING_PID"
        exit 1
    fi
    rm -f "$LOCK_FILE"
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
