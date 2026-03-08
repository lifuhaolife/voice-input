#!/bin/bash
# Install voice-input as a system-wide command

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "安装语音输入工具..."

# 1. 创建符号链接到 /usr/local/bin
sudo ln -sf "$PROJECT_DIR/scripts/voice-input.sh" /usr/local/bin/voice-input

# 2. 安装桌面快捷方式
mkdir -p ~/.local/share/applications
cp "$SCRIPT_DIR/voice-input.desktop" ~/.local/share/applications/

# 3. 添加用户到 input 组（如果还没有）
if ! groups | grep -q input; then
    echo "将用户添加到 input 组..."
    sudo usermod -a -G input $USER
    echo "注意: 需要重新登录才能生效 input 组权限"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方法:"
echo "  1. 命令行运行: voice-input"
echo "  2. 应用菜单搜索: 语音输入"
echo "  3. 快捷键: 按住 Alt 键录音，松开识别"
echo ""
echo "首次使用请重新登录以获取 input 组权限"