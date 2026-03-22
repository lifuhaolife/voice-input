//! 快捷键监听模块 - 使用 evdev 监听全局快捷键

use anyhow::Result;
use evdev::{AttributeSet, Device, Key};
use log::info;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use std::sync::mpsc::{self, Sender};

/// 快捷键事件
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum HotkeyEvent {
    Pressed,
    Released,
}

/// 快捷键监听器
pub struct HotkeyListener {
    trigger_key: Key,
    is_running: Arc<AtomicBool>,
    thread: Option<thread::JoinHandle<()>>,
    event_tx: Option<Sender<HotkeyEvent>>,
    event_rx: Option<std::sync::mpsc::Receiver<HotkeyEvent>>,
}

impl HotkeyListener {
    /// 创建快捷键监听器
    pub fn new(trigger: &str) -> Result<Self> {
        let trigger_key = Self::parse_key(trigger)?;
        let (tx, rx) = mpsc::channel();
        
        Ok(HotkeyListener {
            trigger_key,
            is_running: Arc::new(AtomicBool::new(false)),
            thread: None,
            event_tx: Some(tx),
            event_rx: Some(rx),
        })
    }
    
    /// 解析按键名称
    fn parse_key(key_str: &str) -> Result<Key> {
        match key_str.to_lowercase().as_str() {
            "alt" | "alt_l" => Ok(Key::KEY_LEFTALT),
            "alt_r" => Ok(Key::KEY_RIGHTALT),
            "ctrl" | "ctrl_l" => Ok(Key::KEY_LEFTCTRL),
            "ctrl_r" => Ok(Key::KEY_RIGHTCTRL),
            "shift" | "shift_l" => Ok(Key::KEY_LEFTSHIFT),
            "shift_r" => Ok(Key::KEY_RIGHTSHIFT),
            "super" | "cmd" | "win" => Ok(Key::KEY_LEFTMETA),
            _ => Err(anyhow::anyhow!("不支持的按键：{}", key_str)),
        }
    }
    
    /// 查找键盘设备
    fn find_keyboard_devices() -> Vec<Device> {
        let mut devices = Vec::new();
        
        for (_, device) in evdev::enumerate() {
            if let Ok(keys) = device.get_supported_keys() {
                if keys.contains(&Key::KEY_LEFTALT) || keys.contains(&Key::KEY_RIGHTALT) {
                    if let Ok(name) = device.name() {
                        info!("找到键盘设备：{}", name);
                        devices.push(device);
                    }
                }
            }
        }
        
        devices
    }
    
    /// 开始监听
    pub fn start(&mut self) -> Result<()> {
        if self.is_running.load(Ordering::SeqCst) {
            return Ok(());
        }
        
        let devices = Self::find_keyboard_devices();
        if devices.is_empty() {
            return Err(anyhow::anyhow!("未找到键盘设备"));
        }
        
        info!("监听 {} 个键盘设备", devices.len());
        
        let trigger_key = self.trigger_key;
        let is_running = self.is_running.clone();
        let tx = self.event_tx.take().unwrap();
        
        is_running.store(true, Ordering::SeqCst);
        
        let handle = thread::spawn(move || {
            let mut pressed_keys: AttributeSet<Key> = AttributeSet::new();
            let mut hotkey_pressed = false;
            
            while is_running.load(Ordering::SeqCst) {
                for device in &mut devices.iter() {
                    if let Ok(events) = device.fetch_events() {
                        for event in events {
                            let key = Key::new(event.code());
                            if event.value() == 1 {
                                pressed_keys.insert(key);
                                
                                if pressed_keys.contains(trigger_key) && !hotkey_pressed {
                                    hotkey_pressed = true;
                                    let _ = tx.send(HotkeyEvent::Pressed);
                                }
                            } else if event.value() == 0 {
                                pressed_keys.remove(key);
                                
                                if !pressed_keys.contains(trigger_key) && hotkey_pressed {
                                    hotkey_pressed = false;
                                    let _ = tx.send(HotkeyEvent::Released);
                                }
                            }
                        }
                    }
                }
                
                thread::sleep(Duration::from_millis(10));
            }
        });
        
        self.thread = Some(handle);
        
        Ok(())
    }
    
    /// 获取事件接收器
    pub fn get_event_receiver(&mut self) -> Option<std::sync::mpsc::Receiver<HotkeyEvent>> {
        self.event_rx.take()
    }
    
    /// 停止监听
    pub fn stop(&mut self) {
        self.is_running.store(false, Ordering::SeqCst);
        if let Some(thread) = self.thread.take() {
            let _ = thread.join();
        }
        info!("快捷键监听已停止");
    }
}

impl Drop for HotkeyListener {
    fn drop(&mut self) {
        self.stop();
    }
}
