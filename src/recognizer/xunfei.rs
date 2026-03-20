//! 讯飞流式语音识别器

use anyhow::{Context, Result};
use base64::{engine::general_purpose::STANDARD, Engine};
use chrono::Utc;
use hmac::{Hmac, Mac};
use log::{debug, error, info};
use serde::Deserialize;
use sha2::Sha256;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use tokio_tungstenite::tungstenite::{client::IntoClientRequest, Message};
use tokio_tungstenite::{connect_async, WebSocketStream};
use futures_util::{SinkExt, StreamExt};

type HmacSha256 = Hmac<Sha256>;

/// 识别结果
#[derive(Debug, Clone)]
pub struct RecognitionResult {
    pub text: String,
    pub is_final: bool,
}

/// 讯飞流式识别器
pub struct XunfeiStreamer {
    app_id: String,
    api_key: String,
    api_secret: String,
    language: String,
    accent: String,
    vad_eos: u64,
    on_result: Box<dyn Fn(RecognitionResult) + Send + 'static>,
    is_running: Arc<AtomicBool>,
    user_stopped: Arc<AtomicBool>,
    audio_tx: Option<Sender<Vec<u8>>>,
}

#[derive(Debug, Deserialize)]
struct XunfeiResponse {
    code: i32,
    message: String,
    data: Option<XunfeiData>,
}

#[derive(Debug, Deserialize)]
struct XunfeiData {
    status: Option<i32>,
    result: Option<XunfeiResult>,
}

#[derive(Debug, Deserialize)]
struct XunfeiResult {
    ws: Option<Vec<WsItem>>,
}

#[derive(Debug, Deserialize)]
struct WsItem {
    cw: Option<Vec<CwItem>>,
}

#[derive(Debug, Deserialize)]
struct CwItem {
    w: Option<String>,
}

impl XunfeiStreamer {
    /// 创建讯飞识别器
    pub fn new<F>(
        app_id: String,
        api_key: String,
        api_secret: String,
        language: String,
        accent: String,
        vad_eos: u64,
        on_result: F,
    ) -> Self
    where
        F: Fn(RecognitionResult) + Send + 'static,
    {
        XunfeiStreamer {
            app_id,
            api_key,
            api_secret,
            language,
            accent,
            vad_eos,
            on_result: Box::new(on_result),
            is_running: Arc::new(AtomicBool::new(false)),
            user_stopped: Arc::new(AtomicBool::new(false)),
            audio_tx: None,
        }
    }
    
    /// 生成鉴权 URL
    fn create_url(&self) -> Result<String> {
        let date = Utc::now().format("%a, %d %b %Y %H:%M:%S GMT").to_string();
        let host = "iat-api.xfyun.cn";
        let path = "/v2/iat";
        
        // 签名原始字符串
        let sig_origin = format!("host: {}\ndate: {}\nGET {} HTTP/1.1", host, date, path);
        
        // 计算签名
        let mut mac = HmacSha256::new_from_slice(self.api_secret.as_bytes())
            .context("HMAC 初始化失败")?;
        mac.update(sig_origin.as_bytes());
        let signature = STANDARD.encode(mac.finalize().into_bytes());
        
        // authorization
        let auth_origin = format!(
            "api_key=\"{}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{}\"",
            self.api_key, signature
        );
        let authorization = STANDARD.encode(auth_origin.as_bytes());
        
        let url = format!(
            "wss://{}{}?authorization={}&date={}&host={}",
            host, path, authorization, date, host
        );
        
        Ok(url)
    }
    
    /// 开始识别
    pub fn start(&mut self) -> Result<()> {
        let url = self.create_url()?;
        info!("连接讯飞 WebSocket: {}", url);
        
        let (audio_tx, audio_rx) = mpsc::channel();
        self.audio_tx = Some(audio_tx);
        
        let is_running = self.is_running.clone();
        let user_stopped = self.user_stopped.clone();
        let on_result = self.on_result.clone();
        
        let app_id = self.app_id.clone();
        let language = self.language.clone();
        let accent = self.accent.clone();
        let vad_eos = self.vad_eos;
        
        tokio::spawn(async move {
            Self::run_websocket(
                url,
                app_id,
                language,
                accent,
                vad_eos,
                audio_rx,
                on_result,
                is_running,
                user_stopped,
            ).await;
        });
        
        // 等待连接建立
        thread::sleep(Duration::from_millis(500));
        
        Ok(())
    }
    
    async fn run_websocket(
        url: String,
        app_id: String,
        language: String,
        accent: String,
        vad_eos: u64,
        audio_rx: Receiver<Vec<u8>>,
        on_result: Box<dyn Fn(RecognitionResult) + Send>,
        is_running: Arc<AtomicBool>,
        user_stopped: Arc<AtomicBool>,
    ) {
        is_running.store(true, Ordering::SeqCst);
        
        let request = url.into_client_request().unwrap();
        match connect_async(request).await {
            Ok((mut ws, _)) => {
                info!("✅ WebSocket 连接成功");
                
                // 发送首帧
                let first_frame = serde_json::json!({
                    "common": {"app_id": app_id},
                    "business": {
                        "language": language,
                        "domain": "iat",
                        "accent": accent,
                        "dwa": "wpgs",
                        "vad_eos": vad_eos,
                        "pd": "result",
                    },
                    "data": {
                        "status": 0,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": "",
                    }
                });
                
                if let Err(e) = ws.send(Message::Text(first_frame.to_string())).await {
                    error!("发送首帧失败：{}", e);
                    return;
                }
                
                // 音频发送任务
                let ws_send = ws.split().0;
                let audio_task = tokio::spawn(async move {
                    let mut ws_send = ws_send;
                    while !user_stopped.load(Ordering::SeqCst) {
                        match audio_rx.recv_timeout(Duration::from_millis(100)) {
                            Ok(audio_data) => {
                                let audio_b64 = STANDARD.encode(&audio_data);
                                let frame = serde_json::json!({
                                    "data": {
                                        "status": 1,
                                        "format": "audio/L16;rate=16000",
                                        "encoding": "raw",
                                        "audio": audio_b64,
                                    }
                                });
                                let _ = ws_send.send(Message::Text(frame.to_string())).await;
                            }
                            Err(_) => continue,
                        }
                    }
                    
                    // 发送结束帧
                    let end_frame = serde_json::json!({
                        "data": {"status": 2, "audio": ""}
                    });
                    let _ = ws_send.send(Message::Text(end_frame.to_string())).await;
                    ws_send
                });
                
                // 接收结果
                while is_running.load(Ordering::SeqCst) {
                    match ws.next().await {
                        Some(Ok(Message::Text(text))) => {
                            if let Ok(resp) = serde_json::from_str::<XunfeiResponse>(&text) {
                                if resp.code == 0 {
                                    if let Some(data) = resp.data {
                                        let text = Self::extract_text(&data);
                                        let is_final = data.status.unwrap_or(0) == 2;
                                        if !text.is_empty() {
                                            on_result(RecognitionResult { text, is_final });
                                        }
                                        if is_final {
                                            break;
                                        }
                                    }
                                } else {
                                    error!("讯飞识别错误：{}", resp.message);
                                }
                            }
                        }
                        Some(Ok(Message::Close(_))) => break,
                        Some(Err(e)) => {
                            error!("WebSocket 错误：{}", e);
                            break;
                        }
                        _ => {}
                    }
                }
                
                let _ = audio_task.await;
                is_running.store(false, Ordering::SeqCst);
                info!("WebSocket 连接关闭");
            }
            Err(e) => {
                error!("WebSocket 连接失败：{}", e);
            }
        }
    }
    
    fn extract_text(data: &XunfeiData) -> String {
        let mut text = String::new();
        if let Some(result) = &data.result {
            if let Some(ws_items) = &result.ws {
                for ws_item in ws_items {
                    if let Some(cw_items) = &ws_item.cw {
                        for cw_item in cw_items {
                            if let Some(w) = &cw_item.w {
                                text.push_str(w);
                            }
                        }
                    }
                }
            }
        }
        text
    }
    
    /// 发送音频数据
    pub fn send_audio(&self, audio_data: &[u8]) {
        if let Some(tx) = &self.audio_tx {
            let _ = tx.send(audio_data.to_vec());
        }
    }
    
    /// 停止识别
    pub fn stop(&self) {
        self.user_stopped.store(true, Ordering::SeqCst);
        thread::sleep(Duration::from_millis(500));
    }
}
