# Voice Input

🎤 **语音输入工具** - Linux 上的语音转文字输入工具，支持多种语音识别后端。

## 功能特性

- 🎙️ **快捷键触发** - 按住快捷键录音，松开自动识别并输入
- 🔄 **多后端支持** - 支持 Whisper（本地）、百度、讯飞、腾讯云语音识别
- ⌨️ **自动输入** - 识别结果自动输入到当前光标位置
- 🔔 **系统通知** - 录音状态和识别结果通知
- ⚙️ **灵活配置** - YAML 配置文件，支持多种参数调整

## 系统要求

- Python 3.10+
- Linux (X11 或 Wayland)
- 麦克风设备

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/lifuhaolife/voice-input.git
cd voice-input
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate

# 安装包
pip install -e .
```

### 3. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt install libportaudio2 portaudio19-dev

# 可选：用于通知功能
sudo apt install libnotify-bin
```

### 4. 下载 Whisper 模型（首次运行自动下载）

模型会自动下载到 `~/.cache/whisper/` 目录。

## 使用方法

### 启动程序

```bash
voice-input
```

### 快捷键操作

- **按住** `Ctrl+Alt+V` 开始录音
- **松开** 自动停止录音并识别
- 识别结果会自动输入到当前光标位置

### 命令行选项

```bash
# 查看帮助
voice-input --help

# 列出音频设备
voice-input --list-devices

# 使用自定义配置
voice-input --config my-config.yaml

# 指定 Whisper 模型
voice-input --model small

# 自定义快捷键
voice-input --hotkey "ctrl+shift+v"

# 详细日志
voice-input -v
```

## 配置

配置文件位于 `~/.config/voice-input/config.yaml`：

```yaml
# 语音识别后端
backend: whisper

# 快捷键设置
hotkey:
  trigger: "ctrl+alt+v"
  mode: "hold"  # hold 或 toggle

# 录音设置
recording:
  sample_rate: 16000
  channels: 1
  max_duration: 60

# Whisper 设置
whisper:
  model: "small"      # tiny, base, small, medium, large
  language: "zh"      # 语言代码，留空自动检测
  device: "auto"      # auto, cuda, cpu

# 通知设置
notification:
  enabled: true
  show_status: true
  show_result: true

# 输入设置
input:
  method: "type"      # type 或 clipboard
  type_delay: 0.01
```

## 后端对比

| 后端 | 离线 | 中文支持 | 准确率 | 费用 |
|------|------|----------|--------|------|
| Whisper | ✅ | ✅ 优秀 | 高 | 免费 |
| 百度 | ❌ | ✅ 优秀 | 高 | 按量收费 |
| 讯飞 | ❌ | ✅ 优秀 | 高 | 按量收费 |
| 腾讯云 | ❌ | ✅ 优秀 | 高 | 按量收费 |

## 硬件要求

### Whisper 模型选择

| 模型 | 参数量 | 内存需求 | 速度 | 准确率 |
|------|--------|----------|------|--------|
| tiny | 39M | ~1GB | 极快 | 一般 |
| base | 74M | ~1GB | 快 | 较好 |
| small | 244M | ~2GB | 中等 | 好 |
| medium | 769M | ~5GB | 较慢 | 很好 |
| large | 1550M | ~10GB | 慢 | 最好 |

**推荐**：
- CPU: `small` 或 `base`
- GPU: `medium` 或 `large`

## 开发

### 项目结构

```
voice-input/
├── src/voice_input/
│   ├── main.py              # 主入口
│   ├── config.py            # 配置管理
│   ├── recorder.py          # 录音模块
│   ├── hotkey.py            # 快捷键监听
│   ├── typer.py             # 文本输入
│   ├── notify.py            # 系统通知
│   └── recognizer/          # 语音识别后端
│       ├── base.py          # 抽象基类
│       └── whisper_backend.py
├── config.yaml
├── pyproject.toml
└── README.md
```

### 添加新的识别后端

1. 在 `recognizer/` 目录创建新文件，如 `baidu_backend.py`
2. 继承 `Recognizer` 基类并实现接口
3. 在 `main.py` 中注册新后端

```python
# recognizer/baidu_backend.py
from voice_input.recognizer.base import Recognizer

class BaiduRecognizer(Recognizer):
    @property
    def name(self) -> str:
        return "baidu"

    def is_available(self) -> bool:
        # 检查配置和依赖
        pass

    def transcribe(self, audio_data) -> str:
        # 调用百度 API
        pass
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
- 尝试使用其他快捷键组合

### Whisper 模型下载慢

可以手动下载模型到 `~/.cache/whisper/`：
- [模型下载地址](https://github.com/openai/whisper/blob/main/whisper/__init__.py#L17-L30)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！