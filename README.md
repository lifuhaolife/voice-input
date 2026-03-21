# Voice Input

🎤 **流式语音输入工具** - Linux 上的实时语音转文字输入工具，支持讯飞/腾讯/百度语音识别，边说边出文字。

**版本**: v1.0.0

## 快速开始

```bash
# 1. 安装系统依赖
sudo apt update
sudo apt install -y python3 python3-pip python3-venv portaudio19-dev libevdev2 xdotool wtype xclip wl-clipboard

# 2. 克隆并安装
git clone https://github.com/lifuhaolife/lb-voice.git
cd lb-voice
./scripts/install.sh

# 3. 配置 API（填入讯飞密钥）
nano config.yaml

# 4. 重新登录系统后运行
lb-voice
```

## 功能特性

- 🎙️ **快捷键触发** - 按住快捷键录音，松开自动识别并输入到光标位置
- 🔄 **流式识别** - 支持讯飞流式语音识别，边说边显示，支持动态修正
- 🔌 **多后端支持** - 支持讯飞（推荐）、腾讯、百度云语音识别
- ⚡ **低延迟** - 流式传输，实时返回识别结果
- ⌨️ **自动输入** - 识别结果自动输入到当前光标位置（支持 X11/Wayland）
- 🔒 **单例运行** - 自动防止重复启动
- 🔔 **通知提示** - 可选的桌面通知反馈
- 🔧 **后台运行** - 支持后台守护进程模式运行
- 📝 **调试日志** - 可配置日志级别，便于调试

## 系统要求

- **操作系统**: Ubuntu 20.04+ / Debian 11+ 或其他 Linux 发行版
- **Python**: 3.10+
- **桌面环境**: X11 或 Wayland
- **硬件**: 麦克风设备
- **API**: 讯飞/腾讯/百度开放平台账号（免费额度充足）

## 安装

### 1. 安装系统依赖

**Ubuntu/Debian:**

```bash
# 更新软件源
sudo apt update

# 安装基础依赖
sudo apt install -y python3 python3-pip python3-venv portaudio19-dev libevdev2

# 安装输入工具（根据桌面环境选择）
# X11 用户
sudo apt install -y xdotool

# Wayland 用户（推荐 wtype）
sudo apt install -y wtype
# 或者使用 ydotool
# sudo apt install -y ydotool

# 可选：剪贴板工具（推荐，最稳定的输入方式）
sudo apt install -y xclip wl-clipboard
```

**其他发行版:**

- **Arch Linux**: `sudo pacman -S python portaudio libevdev xdotool wtype`
- **Fedora**: `sudo dnf install python3 portaudio-devel libevdev xdotool wtype`

### 2. 克隆仓库

```bash
git clone https://github.com/lifuhaolife/lb-voice.git
cd lb-voice
```

### 3. 运行安装脚本

```bash
./scripts/install.sh
```

安装脚本会自动：
- 创建 Python 虚拟环境
- 安装 Python 依赖
- 创建系统命令链接到 `/usr/local/bin/lb-voice`
- 安装桌面启动项
- 将当前用户添加到 `input` 组（需要重新登录生效）

或手动安装：

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 4. 配置语音识别 API

#### 讯飞语音（推荐）

1. 访问 [讯飞开放平台](https://console.xfyun.cn/) 创建应用
2. 开通"语音听写（流式版）"服务
3. 获取 `APPID`、`APIKey`、`APISecret`

#### 腾讯云语音（备选）

1. 访问 [腾讯云语音识别](https://console.cloud.tencent.com/asr)
2. 开通"实时语音识别"服务
3. 获取 `AppID`、`SecretId`、`SecretKey`

#### 百度云语音（备选）

1. 访问 [百度 AI 开放平台](https://console.bce.baidu.com/ai/#/ai/speech/)
2. 创建应用并开通"短语音识别"
3. 获取 `AppID`、`API Key`、`Secret Key`

### 5. 创建配置文件

```bash
# 复制配置模板
cp config.yaml.example config.yaml

# 编辑配置文件
nano config.yaml  # 或使用你喜欢的编辑器
```

填入你的 API 密钥：

```yaml
# 选择后端: xunfei / tencent / baidu
backend: xunfei

# 讯飞配置
xunfei:
  app_id: "你的APPID"
  api_key: "你的APIKey"
  api_secret: "你的APISecret"
```

配置文件查找顺序：
1. `~/.config/lb-voice/config.yaml`（推荐）
2. `~/.lb-voice/config.yaml`
3. 项目目录下的 `config.yaml`

## 使用方法

### 首次使用

**重要**: 安装后需要重新登录系统，以使 `input` 组权限生效。

### 启动程序

```bash
# 前台运行（推荐调试时使用）
lb-voice

# 后台运行
./scripts/lb-voice.sh --background
# 或简写
./scripts/lb-voice.sh -b

# 查看后台日志
tail -f ~/.local/share/lb-voice/logs/lb-voice.log
```

### 快捷键操作

- **按住** `Alt+M`（默认）开始录音
- **松开** 自动停止录音并输入文字
- 识别结果会自动输入到当前光标位置

### 停止程序

```bash
# 前台运行：按 Ctrl+C

# 后台运行：查找并终止进程
ps aux | grep lb-voice
kill <PID>
```

### 命令行选项

```bash
# 查看帮助
lb-voice --help

# 列出音频设备
lb-voice --list-devices

# 使用自定义配置
lb-voice --config /path/to/config.yaml

# 详细日志（调试模式）
lb-voice -v

# 查看版本
lb-voice --version
```

## 配置说明

配置文件位于 `~/.config/lb-voice/config.yaml` 或项目目录 `config.yaml`：

```yaml
# 语音识别后端
backend: xunfei  # xunfei / tencent / baidu

# 快捷键设置
hotkey:
  trigger: "alt_r"    # 支持: alt, alt_l, alt_r, ctrl, shift, super 或组合键
  mode: "hold"        # hold(按住) 或 toggle(切换)

# 录音设置
recording:
  sample_rate: 16000
  channels: 1
  chunk_ms: 80        # 每块音频时长(毫秒)，80-160ms 可降低 CPU 占用
  max_duration: 30    # 最长录音时长(秒)

# 讯飞语音识别配置
xunfei:
  app_id: ""
  api_key: ""
  api_secret: ""
  language: "zh_cn"   # zh_cn(中文), en_us(英文)
  accent: "mandarin"  # mandarin(普通话), cantonese(粤语)
  vad_eos: 5000       # 语音结束静默时长(毫秒)
  max_audio_queue_size: 400  # 流式识别发送队列最大长度
  batch_chunks: 4     # 每次发送的音频块数量（4-8 可减少 CPU 负载）

# 腾讯语音识别配置
tencent:
  app_id: ""
  secret_id: ""
  secret_key: ""

# 百度语音识别配置
baidu:
  app_id: ""
  api_key: ""
  secret_key: ""

# 音效反馈
sound:
  enabled: false

# 文本输入设置
input:
  method: "clipboard"  # clipboard(推荐) / xdotool / wtype / ydotool / type
  type_delay: 0.005

# 通知设置
notification:
  enabled: false       # 是否启用桌面通知
  show_status: false   # 显示录音状态通知
  show_result: false   # 显示识别结果通知

# 日志设置
logging:
  level: "info"       # debug, info, warning, error
  show_audio_chunks: false    # 打印音频块信息（debug 级别）
  show_recognized_text: false # 打印识别的文本内容（debug 级别）
```

### 输入方式说明

- **clipboard**（推荐）: 通过剪贴板粘贴，最稳定，支持所有桌面环境
- **xdotool**: X11 环境下模拟按键输入
- **wtype**: Wayland 环境下模拟按键输入（推荐）
- **ydotool**: Wayland 环境备选方案（仅支持 ASCII）
- **type**: 自动检测并选择合适的输入方式

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
lb-voice -v
```

## 开机自启动

```bash
# 启用开机自启动
./scripts/enable-autostart.sh

# 禁用开机自启动
./scripts/disable-autostart.sh
```

## 故障排除

### 麦克风无法使用

```bash
# 检查麦克风设备
arecord -l

# 测试录音
arecord -d 3 test.wav
aplay test.wav

# 列出 lb-voice 识别的设备
lb-voice --list-devices
```

### 快捷键不响应

1. **权限问题**: 确保已将用户添加到 `input` 组并重新登录
   ```bash
   groups  # 检查是否包含 input 组
   sudo usermod -a -G input $USER  # 添加到 input 组
   ```

2. **快捷键冲突**: 尝试使用其他快捷键组合
   ```yaml
   hotkey:
     trigger: "ctrl+alt+v"  # 或其他组合
   ```

3. **设备权限**: 检查 `/dev/input/` 权限
   ```bash
   ls -l /dev/input/event*
   ```

### 文字没有输入到光标位置

1. **Wayland 用户**: 确保安装了输入工具
   ```bash
   # 推荐使用 wtype
   sudo apt install wtype
   
   # 配置文件中设置
   input:
     method: "wtype"
   ```

2. **X11 用户**: 确保安装了 xdotool
   ```bash
   sudo apt install xdotool
   
   # 配置文件中设置
   input:
     method: "xdotool"
   ```

3. **通用方案**: 使用剪贴板方式（最稳定）
   ```yaml
   input:
     method: "clipboard"
   ```

### 程序已在运行错误

```bash
# 查找进程
ps aux | grep lb-voice

# 终止进程
kill <PID>

# 或删除锁文件
rm -f ~/.local/share/lb-voice/lb-voice.lock
```

### 语音识别 API 错误

1. **检查配置**: 确认 `config.yaml` 中的 API 密钥正确
2. **检查网络**: 确保能访问对应的 API 服务
3. **查看日志**: 使用 `-v` 参数查看详细错误信息
   ```bash
   lb-voice -v
   ```
4. **检查额度**: 登录对应平台查看 API 调用额度

### CPU 占用过高

调整配置文件中的参数：

```yaml
recording:
  chunk_ms: 160  # 增大音频块时长

xunfei:
  batch_chunks: 8  # 增大批量发送数量
```

## 项目结构

```
lb-voice/
├── src/voice_input/
│   ├── run.py               # 启动入口（处理日志和单例）
│   ├── main.py              # 主程序逻辑
│   ├── config.py            # 配置管理
│   ├── recorder.py          # 录音模块（流式）
│   ├── hotkey.py            # 快捷键监听
│   ├── typer.py             # 文本输入（支持X11/Wayland）
│   ├── sound.py             # 音效反馈
│   ├── notify.py            # 桌面通知
│   ├── process_lock.py      # 进程单例锁
│   ├── logger_config.py     # 日志配置
│   └── recognizer/          # 语音识别后端
│       ├── base.py          # 基类接口
│       ├── xunfei.py        # 讯飞流式识别
│       └── whisper_backend.py  # Whisper 本地识别（实验性）
├── scripts/
│   ├── install.sh           # 安装脚本
│   ├── lb-voice.sh       # 启动脚本（支持后台运行）
│   ├── enable-autostart.sh  # 启用开机自启动
│   ├── disable-autostart.sh # 禁用开机自启动
│   ├── uninstall.sh         # 卸载脚本
│   └── lb-voice.desktop  # 桌面启动项
├── config.yaml.example      # 配置模板
├── pyproject.toml           # Python 项目配置
└── README.md
```

## 常见问题

**Q: 支持哪些语言？**  
A: 取决于选择的后端。讯飞支持中文（普通话、粤语）和英文。

**Q: 免费额度够用吗？**  
A: 讯飞每日 500 次免费调用，个人使用完全足够。

**Q: 可以离线使用吗？**  
A: 目前主要依赖云端 API。本地 Whisper 支持正在开发中（实验性功能）。

**Q: 支持 macOS 或 Windows 吗？**  
A: 目前仅支持 Linux。其他平台支持计划中。

**Q: 识别准确率如何？**  
A: 讯飞识别准确率较高，普通话环境下可达 95%+。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (2026-03-22)

- 🎉 首个稳定版本发布
- ✨ 支持讯飞/腾讯/百度三种语音识别后端
- ✨ 支持 X11 和 Wayland 桌面环境
- ✨ 流式语音识别，实时返回结果
- ✨ 多种文本输入方式（剪贴板/xdotool/wtype/ydotool）
- ✨ 进程单例锁，防止重复运行
- ✨ 可选的桌面通知功能
- ✨ 完善的日志系统
- 📝 完整的文档和配置说明

## 致谢

- [讯飞开放平台](https://www.xfyun.cn/) - 提供优质的语音识别服务
- 所有贡献者和用户的支持
