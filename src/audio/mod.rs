//! 音频录制模块 - 流式音频采集

use anyhow::{Context, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, Stream, StreamConfig};
use log::{debug, error, info};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::sync::mpsc::{self, Sender, Receiver};

/// 音频数据块
pub type AudioChunk = Vec<i16>;

/// 流式录音器
pub struct StreamingRecorder {
    sample_rate: u32,
    channels: u16,
    chunk_size: usize,
    tx: Option<Sender<AudioChunk>>,
    rx: Option<Receiver<AudioChunk>>,
    stream: Option<Stream>,
    is_recording: Arc<AtomicBool>,
}

impl StreamingRecorder {
    /// 创建流式录音器
    pub fn new(sample_rate: u32, channels: u16, chunk_ms: u32) -> Self {
        let chunk_size = (sample_rate * chunk_ms / 1000) as usize;
        let (tx, rx) = mpsc::channel();
        
        StreamingRecorder {
            sample_rate,
            channels,
            chunk_size,
            tx: Some(tx),
            rx: Some(rx),
            stream: None,
            is_recording: Arc::new(AtomicBool::new(false)),
        }
    }
    
    /// 列出可用的音频输入设备
    pub fn list_devices() -> Result<Vec<(String, Device)>> {
        let host = cpal::default_host();
        let devices = host.input_devices()?;
        let mut result = Vec::new();
        
        for device in devices {
            if let Ok(name) = device.name() {
                result.push((name, device));
            }
        }
        
        Ok(result)
    }
    
    /// 获取默认输入设备
    pub fn get_default_device() -> Result<Device> {
        let host = cpal::default_host();
        host.default_input_device()
            .context("未找到默认输入设备")
    }
    
    /// 开始录音
    pub fn start(&mut self, device: Option<Device>) -> Result<()> {
        if self.is_recording.load(Ordering::SeqCst) {
            return Ok(());
        }
        
        let device = device.unwrap_or_else(|| Self::get_default_device()?);
        let config = device.default_input_config()?;
        
        info!(
            "开始录音：{}Hz, {} 声道，块大小：{} 采样",
            self.sample_rate, self.channels, self.chunk_size
        );
        
        let tx = self.tx.take().context("发送器已使用")?;
        let is_recording = self.is_recording.clone();
        is_recording.store(true, Ordering::SeqCst);
        
        let err_fn = |err| error!("音频流错误：{}", err);
        
        let stream = match config.sample_format() {
            cpal::SampleFormat::I16 => device.build_input_stream(
                &config.into(),
                move |data: &[i16], _: &cpal::InputCallbackInfo| {
                    if is_recording.load(Ordering::SeqCst) {
                        let _ = tx.send(data.to_vec());
                    }
                },
                err_fn,
                None,
            )?,
            cpal::SampleFormat::F32 => device.build_input_stream(
                &config.into(),
                move |data: &[f32], _: &cpal::InputCallbackInfo| {
                    if is_recording.load(Ordering::SeqCst) {
                        let samples: Vec<i16> = data.iter()
                            .map(|&s| (s * 32767.0) as i16)
                            .collect();
                        let _ = tx.send(samples);
                    }
                },
                err_fn,
                None,
            )?,
            _ => return Err(anyhow::anyhow!("不支持的采样格式")),
        };
        
        stream.play()?;
        self.stream = Some(stream);
        
        Ok(())
    }
    
    /// 停止录音
    pub fn stop(&mut self) {
        self.is_recording.store(false, Ordering::SeqCst);
        if let Some(stream) = self.stream.take() {
            stream.pause().ok();
            drop(stream);
        }
        info!("录音已停止");
    }
    
    /// 获取接收器
    pub fn get_receiver(&mut self) -> Option<Receiver<AudioChunk>> {
        self.rx.take()
    }
    
    /// 是否正在录音
    pub fn is_recording(&self) -> bool {
        self.is_recording.load(Ordering::SeqCst)
    }
}

impl Drop for StreamingRecorder {
    fn drop(&mut self) {
        self.stop();
    }
}
