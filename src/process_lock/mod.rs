//! 进程锁模块 - 确保单实例运行

use anyhow::{Context, Result};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::process;

/// 进程锁
pub struct ProcessLock {
    lock_file: PathBuf,
    file: Option<File>,
}

impl ProcessLock {
    /// 创建进程锁
    pub fn new(lock_file: Option<PathBuf>) -> Self {
        let lock_file = lock_file.unwrap_or_else(|| PathBuf::from("/tmp/voice-input.lock"));
        
        ProcessLock {
            lock_file,
            file: None,
        }
    }
    
    /// 尝试获取锁
    pub fn acquire(&mut self) -> Result<bool> {
        // 确保目录存在
        if let Some(parent) = self.lock_file.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("无法创建锁目录：{:?}", parent))?;
        }
        
        // 检查是否有已运行的实例
        if self.lock_file.exists() {
            if let Ok(content) = std::fs::read_to_string(&self.lock_file) {
                if let Ok(pid) = content.trim().parse::<u32>() {
                    // 检查进程是否存在
                    if self.is_process_running(pid) {
                        return Ok(false); // 锁已被占用
                    }
                    // 进程不存在，清理旧锁文件
                    let _ = std::fs::remove_file(&self.lock_file);
                }
            }
        }
        
        // 打开锁文件
        let file = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&self.lock_file)
            .with_context(|| format!("无法打开锁文件：{:?}", self.lock_file))?;
        
        // 写入 PID
        let mut file = file;
        writeln!(file, "{}", process::id())
            .with_context(|| "写入 PID 失败")?;
        file.flush()?;
        
        self.file = Some(file);
        Ok(true)
    }
    
    /// 检查进程是否运行
    fn is_process_running(&self, pid: u32) -> bool {
        #[cfg(unix)]
        {
            unsafe {
                libc::kill(pid as i32, 0) == 0
            }
        }
        #[cfg(not(unix))]
        {
            false
        }
    }
    
    /// 释放锁
    pub fn release(&mut self) {
        self.file = None;
        let _ = std::fs::remove_file(&self.lock_file);
    }
    
    /// 检查是否有已运行的实例
    pub fn check_existing() -> Option<u32> {
        let lock_file = PathBuf::from("/tmp/voice-input.lock");
        if !lock_file.exists() {
            return None;
        }
        
        if let Ok(content) = std::fs::read_to_string(&lock_file) {
            if let Ok(pid) = content.trim().parse::<u32>() {
                #[cfg(unix)]
                unsafe {
                    if libc::kill(pid as i32, 0) == 0 {
                        return Some(pid);
                    }
                }
            }
        }
        
        // 清理旧锁文件
        let _ = std::fs::remove_file(&lock_file);
        None
    }
}

impl Drop for ProcessLock {
    fn drop(&mut self) {
        self.release();
    }
}
