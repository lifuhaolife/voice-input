# Voice Input

🎤 **流式语音输入工具** - Linux 上的实时语音转文字输入工具，支持讯飞流式语音识别，边说边出文字。

## 功能特性

- 🎙️ **快捷键触发** - 按住快捷键录音，松开自动识别并输入到光标位置
- 🔄 **流式识别** - 讯飞语音识别，边说边显示，支持动态修正
- ⚡ **低延迟** - 流式传输，实时返回识别结果
- ⌨️ **自动输入** - 识别结果自动输入到当前光标位置（支持 X11/Wayland）
- 🔧 **后台运行** - 支持后台守护进程模式运行
- 📝 **调试日志** - 可配置日志级别，便于调试

## 系统要求

- Python 3.10+
- Linux (X11 或 Wayland)
- 麦克风设备
- 讯飞开放平台账号（免费额度充足）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/lifuhaolife/voice-input.git
cd voice-input
```

### 2. 运行安装脚本

```bash
./scripts/install.sh
```

或手动安装：

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 3. 配置讯飞 API

1. 访问 [讯飞开放平台](https://console.xfyun.cn/) 创建应用
2. 开通"语音听写"服务
3. 复制 `config.yaml.example` 为 `config.yaml`：
   ```bash
   cp config.yaml.example config.yaml
   ```
4. 编辑 `config.yaml`，填入你的 API 密钥：
   ```yaml
   xunfei:
     app_id: "你的appid"
     api_key: "你的apikey"
     api_secret: "你的apisecret"
   ```

## 使用方法

### 启动程序

```bash
# 前台运行
voice-input

# 后台运行
./scripts/voice-input.sh --background
# 或
./scripts/voice-input.sh -b
```

### 快捷键操作

- **按住** `Alt+M`（默认）开始录音
- **松开** 自动停止录音并输入文字
- 识别结果会自动输入到当前光标位置

### 命令行选项

```bash
# 查看帮助
voice-input --help

# 列出音频设备
voice-input --list-devices

# 使用自定义配置
voice-input --config my-config.yaml

# 详细日志
voice-input -v
```

## 配置

配置文件位于 `~/.config/voice-input/config.yaml` 或项目目录 `config.yaml`：

```yaml
# 语音识别后端
backend: xunfei

# 快捷键设置
hotkey:
  trigger: "alt+m"    # 支持: alt, ctrl, shift, super 或组合键
  mode: "hold"        # hold(按住) 或 toggle(切换)

# 录音设置
recording:
  sample_rate: 16000
  channels: 1
  chunk_ms: 40        # 每块音频时长(毫秒)
  max_duration: 30    # 最长录音时长(秒)

# 讯飞语音识别配置
xunfei:
  app_id: ""
  api_key: ""
  api_secret: ""
  language: "zh_cn"   # zh_cn(中文), en_us(英文)
  accent: "mandarin"  # mandarin(普通话), cantonese(粤语)

# 音效反馈
sound:
  enabled: false

# 文本输入设置
input:
  method: "type"      # type(模拟按键) 或 clipboard(剪贴板)
  type_delay: 0.005

# 日志设置
logging:
  level: "info"       # debug, info, warning, error
  show_audio_chunks: false    # 打印音频块信息
  show_recognized_text: false # 打印识别的文本内容
```

### 调试模式

在 `config.yaml` 中设置：

```yaml
logging:
  level: "debug"
  show_audio_chunks: true      # 查看音频块处理
  show_recognized_text: true   # 查看识别文本内容
```

或使用命令行参数：

```bash
voice-input -v
```

## 后台运行

使用启动脚本的后台模式：

```bash
# 启动后台服务
./scripts/voice-input.sh --background

# 查看日志
tail -f /tmp/voice-input.log

# 停止服务
kill $(cat /tmp/voice-input.pid)
```

## 故障排除

### 麦克风无法使用

```bash
# 检查麦克风设备
arecord -l

# 测试录音
arecord -d 3 test.wav
```

### 快捷键不响应

- 确保没有其他程序占用该快捷键
- 尝试使用其他快捷键组合，如 `ctrl+alt+v`
- 检查是否有权限访问输入设备

### 文字没有输入到光标位置

- **Wayland 用户**：确保安装了 `wtype` 或 `ydotool`
  ```bash
  # Ubuntu/Debian
  sudo apt install wtype
  # 或
  sudo apt install ydotool
  ```
- **X11 用户**：确保安装了 `xdotool`
  ```bash
  sudo apt install xdotool
  ```

### 讯飞 API 错误

- 检查 `config.yaml` 中的 API 密钥是否正确
- 确认讯飞控制台中已开通"语音听写"服务
- 查看日志获取详细错误信息

## 项目结构

```
voice-input/
├── src/voice_input/
│   ├── main.py              # 主入口
│   ├── config.py            # 配置管理
│   ├── recorder.py          # 录音模块（流式）
│   ├── hotkey.py            # 快捷键监听
│   ├── typer.py             # 文本输入（支持X11/Wayland）
│   ├── sound.py             # 音效反馈
│   └── recognizer/          # 语音识别后端
│       └── xunfei.py        # 讯飞流式识别
├── scripts/
│   ├── install.sh           # 安装脚本
│   ├── voice-input.sh       # 启动脚本（支持后台运行）
│   └── voice-input.desktop  # 桌面启动项
├── config.yaml.example      # 配置模板
├── pyproject.toml
└── README.md
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
