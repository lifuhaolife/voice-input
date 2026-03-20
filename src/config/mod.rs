//! 配置模块 - 管理应用配置

use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::PathBuf;

/// 应用配置
#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    /// 语音识别后端
    pub backend: String,
    
    /// 快捷键配置
    pub hotkey: HotkeyConfig,
    
    /// 录音配置
    pub recording: RecordingConfig,
    
    /// 讯飞配置
    pub xunfei: XunfeiConfig,
    
    /// 音效配置
    pub sound: SoundConfig,
    
    /// 输入配置
    pub input: InputConfig,
    
    /// 日志配置
    pub logging: LoggingConfig,
}

/// 快捷键配置
#[derive(Debug, Clone, Deserialize)]
pub struct HotkeyConfig {
    /// 触发键
    pub trigger: String,
    /// 模式：hold 或 toggle
    pub mode: String,
}

/// 录音配置
#[derive(Debug, Clone, Deserialize)]
pub struct RecordingConfig {
    /// 采样率
    pub sample_rate: u32,
    /// 声道数
    pub channels: u16,
    /// 每块时长 (毫秒)
    pub chunk_ms: u32,
    /// 最长录音时长 (秒)
    pub max_duration: u32,
}

/// 讯飞配置
#[derive(Debug, Clone, Deserialize)]
pub struct XunfeiConfig {
    /// 应用 ID
    pub app_id: String,
    /// API Key
    pub api_key: String,
    /// API Secret
    pub api_secret: String,
    /// 语言
    pub language: String,
    /// 方言
    pub accent: String,
    /// VAD 结束静默时长 (毫秒)
    pub vad_eos: u64,
}

/// 音效配置
#[derive(Debug, Clone, Deserialize)]
pub struct SoundConfig {
    /// 是否启用
    pub enabled: bool,
}

/// 输入配置
#[derive(Debug, Clone, Deserialize)]
pub struct InputConfig {
    /// 输入方式
    pub method: String,
    /// 按键间隔 (秒)
    pub type_delay: f64,
}

/// 日志配置
#[derive(Debug, Clone, Deserialize)]
pub struct LoggingConfig {
    /// 日志级别
    pub level: String,
    /// 显示音频块信息
    pub show_audio_chunks: bool,
    /// 显示识别文本
    pub show_recognized_text: bool,
}

impl Config {
    /// 从默认路径加载配置
    pub fn load() -> Result<Self> {
        let config_path = Self::get_config_path();
        Self::load_from_path(&config_path)
    }
    
    /// 从指定路径加载配置
    pub fn load_from_path(path: &PathBuf) -> Result<Self> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("无法读取配置文件：{:?}", path))?;
        
        let config: Config = serde_yaml::from_str(&content)
            .with_context(|| "解析配置文件失败")?;
        
        Ok(config)
    }
    
    /// 获取默认配置路径
    pub fn get_config_path() -> PathBuf {
        // 优先检查当前目录
        let local_path = PathBuf::from("config.yaml");
        if local_path.exists() {
            return local_path;
        }
        
        // 检查用户配置目录
        if let Some(config_dir) = dirs::config_dir() {
            let user_path = config_dir.join("voice-input").join("config.yaml");
            if user_path.exists() {
                return user_path;
            }
        }
        
        // 默认返回当前目录
        local_path
    }
}
