//! 日志模块 - 统一管理日志输出

use chrono::Local;
use log::{LevelFilter, Metadata, Record};
use std::fs::{File, OpenOptions};
use std::io::{Write};
use std::path::PathBuf;
use std::sync::Mutex;

/// 日志器
pub struct Logger {
    file: Mutex<Option<File>>,
    level: LevelFilter,
}

impl Logger {
    /// 初始化日志器
    pub fn init(log_file: Option<PathBuf>, level: &str) -> std::io::Result<()> {
        let level_filter = match level.to_lowercase().as_str() {
            "debug" => LevelFilter::Debug,
            "info" => LevelFilter::Info,
            "warn" => LevelFilter::Warn,
            "error" => LevelFilter::Error,
            _ => LevelFilter::Info,
        };
        
        let file = if let Some(path) = log_file {
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let f = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&path)?;
            Some(f)
        } else {
            None
        };
        
        let logger = Box::new(Logger {
            file: Mutex::new(file),
            level: level_filter,
        });
        
        log::set_boxed_logger(logger)
            .map(|()| log::set_max_level(level_filter))
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        
        Ok(())
    }
    
    /// 获取默认日志文件路径
    pub fn get_default_log_file() -> PathBuf {
        PathBuf::from("/tmp/voice-input.log")
    }
}

impl log::Log for Logger {
    fn enabled(&self, metadata: &Metadata) -> bool {
        metadata.level() <= self.level
    }
    
    fn log(&self, record: &Record) {
        if self.enabled(record.metadata()) {
            let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S");
            let message = format!(
                "{} - {} - {} - {}",
                timestamp,
                record.target(),
                record.level(),
                record.args()
            );
            
            eprintln!("{}", message);
            
            if let Ok(mut file_opt) = self.file.lock() {
                if let Some(file) = file_opt.as_mut() {
                    let _ = writeln!(file, "{}", message);
                    let _ = file.flush();
                }
            }
        }
    }
    
    fn flush(&self) {
        if let Ok(mut file_opt) = self.file.lock() {
            if let Some(file) = file_opt.as_mut() {
                let _ = file.flush();
            }
        }
    }
}
