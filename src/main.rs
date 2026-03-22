//! Voice Input - 流式语音输入工具

mod config;
mod logger;
mod process_lock;
mod audio;
mod hotkey;
mod recognizer;

use anyhow::Result;
use log::{error, info};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

fn main() -> Result<()> {
    // 初始化日志
    logger::Logger::init(
        Some(logger::Logger::get_default_log_file()),
        "info"
    )?;
    
    info!("============================================================");
    info!("Voice Input Rust 版启动");
    info!("进程 PID: {}", std::process::id());
    info!("============================================================");
    
    // 单例检查
    let mut process_lock = process_lock::ProcessLock::new(None);
    if !process_lock.acquire()? {
        if let Some(pid) = process_lock::ProcessLock::check_existing() {
            error!("❌ 语音输入已在运行 (PID: {})", pid);
            error!("   如需重启，请先运行：kill {}", pid);
            return Err(anyhow::anyhow!("已有实例运行"));
        }
    }
    info!("✅ 进程锁已获取");
    
    // 加载配置
    let config = config::Config::load()?;
    info!("配置已加载");
    
    // 创建识别器
    let xunfei_config = config.xunfei.clone();
    let mut streamer = recognizer::xunfei::XunfeiStreamer::new(
        xunfei_config.app_id,
        xunfei_config.api_key,
        xunfei_config.api_secret,
        xunfei_config.language,
        xunfei_config.accent,
        xunfei_config.vad_eos,
        |result| {
            if result.is_final {
                info!("🎤 识别结果：{}", result.text);
            }
        }
    );
    
    // 创建录音器
    let recording_config = config.recording.clone();
    let mut recorder = audio::StreamingRecorder::new(
        recording_config.sample_rate,
        recording_config.channels,
        recording_config.chunk_ms,
    );
    
    // 创建快捷键监听器
    let hotkey_config = config.hotkey.clone();
    let mut hotkey_listener = hotkey::HotkeyListener::new(&hotkey_config.trigger)?;
    hotkey_listener.start()?;
    
    // 获取事件接收器
    let event_rx = hotkey_listener.get_event_receiver().unwrap();
    
    info!("语音输入已就绪，按住 {} 开始录音", hotkey_config.trigger);
    
    // 运行状态
    let is_running = Arc::new(AtomicBool::new(true));
    let is_recognizing = Arc::new(AtomicBool::new(false));
    
    // 事件循环
    while is_running.load(Ordering::SeqCst) {
        match event_rx.recv_timeout(Duration::from_millis(100)) {
            Ok(hotkey::HotkeyEvent::Pressed) => {
                info!("🔴 开始录音，请说话...");
                if !is_recognizing.load(Ordering::SeqCst) {
                    if let Err(e) = streamer.start() {
                        error!("启动识别器失败：{}", e);
                    } else {
                        is_recognizing.store(true, Ordering::SeqCst);
                    }
                }
                if let Err(e) = recorder.start() {
                    error!("启动录音失败：{}", e);
                }
            }
            Ok(hotkey::HotkeyEvent::Released) => {
                info!("⏹️ 停止录音");
                recorder.stop();
                streamer.stop();
                is_recognizing.store(false, Ordering::SeqCst);
            }
            Err(_) => {
                // 超时，继续循环
            }
        }
    }
    
    // 清理
    drop(hotkey_listener);
    drop(process_lock);
    
    info!("语音输入已停止");
    
    Ok(())
}
