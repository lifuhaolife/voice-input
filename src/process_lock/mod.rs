//! 进程锁模块 - 确保单实例运行

use anyhow::{Context, Result};
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::path::PathBuf;
use std::process;

#[cfg(unix)]
use std::os::unix::io::AsRawFd;

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
        
        // 尝试获取独占锁（非阻塞）
        #[cfg(unix)]
        {
            use std::os::unix::prelude::*;
            use libc::{flock, LOCK_EX, LOCK_NB};
            
            let flock_struct = flock {
                l_type: libc::F_WRLCK as i16,
                l_whence: libc::SEEK_SET as i16,
                l_start: 0,
                l_len: 0,
                l_pid: 0,
            };
            
            let ret = unsafe { flock(file.as_raw_fd(), LOCK_EX | LOCK_NB) };
            if ret != 0 {
                return Ok(false);
            }
        }
        
        // 写入 PID
        let mut file = file;
        writeln!(file, "{}", process::id())
            .with_context(|| "写入 PID 失败")?;
        file.flush()?;
        
        self.file = Some(file);
        Ok(true)
    }
    
    /// 检查进程是否运行
    #[cfg(unix)]
    fn is_process_running(&self, pid: u32) -> bool {
        unsafe {
            libc::kill(pid as i32, 0) == 0
        }
    }
    
    #[cfg(not(unix))]
    fn is_process_running(&self, _pid: u32) -> bool {
        false
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
                // 检查进程是否存在
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
