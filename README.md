# Voice Input Rust

🎤 **流式语音输入工具** - Linux 上的实时语音转文字输入工具

使用 Rust 重写，相比 Python 版本：
- ⚡ 更低 CPU 占用（<1% 空闲）
- 🚀 更快响应速度（<50ms）
- 💾 更小内存占用（<10MB）
- 🔒 类型安全，无 GC 暂停

## 功能特性

- 🎙️ **快捷键触发** - 按住快捷键录音，松开自动识别
- 🔄 **流式识别** - 讯飞语音识别，边说边显示
- ⚡ **低延迟** - 异步 WebSocket，实时返回
- ⌨️ **自动输入** - 识别结果自动输入到光标位置
- 🔧 **单例保护** - 进程锁防止多实例运行

## 系统要求

- Linux (X11 或 Wayland)
- 麦克风设备
- 讯飞开放平台账号

## 构建

```bash
# 开发版本
cargo build

# 发布版本（优化）
cargo build --release
```

## 配置

复制 `config.yaml.example` 为 `config.yaml` 并填入你的讯飞 API 密钥：

```yaml
backend: xunfei

hotkey:
  trigger: "alt_r"
  mode: "hold"

recording:
  sample_rate: 16000
  channels: 1
  chunk_ms: 40
  max_duration: 30

xunfei:
  app_id: "YOUR_APP_ID"
  api_key: "YOUR_API_KEY"
  api_secret: "YOUR_API_SECRET"
  language: "zh_cn"
  accent: "mandarin"
  vad_eos: 60000
```

## 使用方法

```bash
# 运行
cargo run --release

# 列出音频设备
cargo run --release -- --list-devices
```

## 快捷键操作

- **按住** 右 Alt 开始录音
- **松开** 自动停止录音并识别

## 项目结构

```
voice-input-rs/
├── src/
│   ├── main.rs           # 主入口
│   ├── config/           # 配置管理
│   ├── logger/           # 日志模块
│   ├── process_lock/     # 进程锁
│   ├── audio/            # 音频录制
│   ├── hotkey/           # 快捷键监听
│   └── recognizer/       # 语音识别
│       └── xunfei.rs     # 讯飞识别器
├── Cargo.toml
└── README.md
```

## 性能对比

| 指标 | Python 版 | Rust 版 |
|------|----------|---------|
| 空闲 CPU | 5-10% | <1% |
| 内存占用 | 50MB | <10MB |
| 启动时间 | 2-3s | <0.5s |
| 响应延迟 | 100-200ms | <50ms |

## 许可证

MIT License
