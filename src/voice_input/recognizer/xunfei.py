"""讯飞语音听写流式识别"""

import base64
import hashlib
import hmac
import json
import logging
import queue
import threading
import time
from typing import Callable, Optional
from urllib.parse import urlencode, urlparse

import websocket

logger = logging.getLogger(__name__)


class XunfeiStreamer:
    """讯飞流式语音识别 - 支持实时边说边出字"""

    WS_URL = "wss://iat-api.xfyun.cn/v2/iat"

    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        language: str = "zh_cn",
        accent: str = "mandarin",
        on_result: Optional[Callable[[str, bool], None]] = None,
        vad_eos: int = 5000,
    ):
        """初始化讯飞流式识别器

        Args:
            app_id: 讯飞应用ID
            api_key: 讯飞API Key
            api_secret: 讯飞API Secret
            language: 语言 (zh_cn, en_us)
            accent: 方言 (mandarin, cantonese)
            on_result: 结果回调 (text, is_final)
            vad_eos: 语音结束静默时长(毫秒), 默认5000
        """
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.language = language
        self.accent = accent
        self.on_result = on_result
        self.vad_eos = vad_eos

        self._ws: Optional[websocket.WebSocketApp] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._result_text = ""
        self._result_parts: list[str] = []  # 用于动态修正
        self._running = False
        self._user_stopped = False  # 用户主动停止标志，不受服务端影响
        self._server_final = False  # 服务端已返回最终结果
        self._connected = False
        self._thread: Optional[threading.Thread] = None

    def _create_url(self) -> str:
        """生成鉴权URL"""
        # RFC1123格式时间戳
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        parsed = urlparse(self.WS_URL)

        # 签名字符串
        sig_origin = f"host: {parsed.netloc}\ndate: {date}\nGET {parsed.path} HTTP/1.1"
        sig_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            sig_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(sig_sha).decode()

        # authorization
        auth_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(auth_origin.encode("utf-8")).decode()

        params = {"authorization": authorization, "date": date, "host": parsed.netloc}
        return self.WS_URL + "?" + urlencode(params)

    def _on_message(self, ws, message):
        """处理识别结果"""
        try:
            data = json.loads(message)
            code = data.get("code")

            if code != 0:
                logger.error(f"讯飞识别错误: {data}")
                return

            result_data = data.get("data", {})
            status = result_data.get("status", 0)
            result = result_data.get("result", {})

            # 解析识别文字
            ws_list = result.get("ws", [])
            text_parts = []
            for ws_item in ws_list:
                for cw in ws_item.get("cw", []):
                    text_parts.append(cw.get("w", ""))
            text = "".join(text_parts)

            # 动态修正处理 (dwa=wpgs)
            pgs = result.get("pgs")
            sn = result.get("sn", 0)

            if pgs == "rpl":
                # 替换模式: 替换指定范围的结果
                rg = result.get("rg", [0, 0])
                if len(self._result_parts) > rg[0]:
                    # 替换rg范围内的内容
                    self._result_parts = self._result_parts[: rg[0]] + [text]
            elif pgs == "apd" or not pgs:
                # 追加模式
                if sn >= len(self._result_parts):
                    self._result_parts.append(text)
                else:
                    self._result_parts[sn] = text

            # 合并所有部分
            self._result_text = "".join(self._result_parts)

            # 回调
            is_final = status == 2
            if self.on_result and self._result_text:
                self.on_result(self._result_text, is_final)

            if is_final:
                logger.info(f"识别完成（服务端VAD）: {self._result_text}")
                self._server_final = True
                # 不设置 _running=False，让用户控制录音结束

        except Exception as e:
            logger.error(f"解析识别结果失败: {e}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket错误: {error}")
        self._running = False

    def _on_close(self, ws, close_status_code, close_msg):
        logger.debug(f"WebSocket关闭: {close_status_code} {close_msg}")
        self._connected = False
        self._running = False

    def _on_open(self, ws):
        """连接建立，发送首帧"""
        logger.debug("WebSocket连接建立")
        self._connected = True
        self._running = True

        # 发送首帧
        frame = {
            "common": {"app_id": self.app_id},
            "business": {
                "language": self.language,
                "domain": "iat",
                "accent": self.accent,
                "dwa": "wpgs",  # 开启动态修正
                "vad_eos": self.vad_eos,  # 语音结束静默时长(毫秒)
            },
            "data": {
                "status": 0,  # 首帧
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            },
        }
        ws.send(json.dumps(frame))

        # 启动音频发送线程
        self._thread = threading.Thread(target=self._send_audio_loop, daemon=True)
        self._thread.start()

    def _send_audio_loop(self):
        """音频发送循环"""
        while not self._user_stopped:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.1)
                if audio_chunk is None:
                    # 结束信号，发送结束帧
                    if self._ws and self._connected:
                        frame = {"data": {"status": 2, "audio": ""}}
                        self._ws.send(json.dumps(frame))
                        logger.debug("发送结束帧")
                    break

                if self._ws and self._connected:
                    # 发送中间帧
                    audio_b64 = base64.b64encode(audio_chunk).decode()
                    frame = {
                        "data": {
                            "status": 1,
                            "format": "audio/L16;rate=16000",
                            "encoding": "raw",
                            "audio": audio_b64,
                        }
                    }
                    self._ws.send(json.dumps(frame))

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"发送音频失败: {e}")
                break

    def start(self) -> bool:
        """开始识别会话

        Returns:
            是否成功启动
        """
        self._result_text = ""
        self._result_parts = []
        self._audio_queue = queue.Queue()
        self._user_stopped = False
        self._server_final = False

        try:
            url = self._create_url()
            self._ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            # 后台运行WebSocket
            ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
            ws_thread.start()

            # 等待连接建立
            for _ in range(50):  # 最多等待5秒
                if self._connected:
                    return True
                time.sleep(0.1)

            logger.error("WebSocket连接超时")
            return False

        except Exception as e:
            logger.error(f"启动识别会话失败: {e}")
            return False

    def send_audio(self, audio_data: bytes):
        """发送音频数据

        Args:
            audio_data: PCM音频数据 (16kHz, 16bit, mono)
        """
        if not self._user_stopped:
            self._audio_queue.put(audio_data)

    def stop(self) -> str:
        """停止识别，返回最终结果

        Returns:
            识别的文字
        """
        self._user_stopped = True
        self._audio_queue.put(None)  # 发送结束信号

        # 等待服务端返回最终结果或连接断开，最多等待8秒
        for _ in range(80):
            if self._server_final or not self._connected:
                break
            time.sleep(0.1)

        if self._ws:
            self._ws.close()

        return self._result_text

    @property
    def is_running(self) -> bool:
        """是否正在识别"""
        return self._running


class XunfeiRecognizer:
    """讯飞短语音识别（非流式）- 用于简单场景"""

    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        language: str = "zh_cn",
    ):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.language = language

    def transcribe(self, audio_data: bytes) -> str:
        """识别音频数据

        Args:
            audio_data: PCM音频数据

        Returns:
            识别的文字
        """
        result_text = ""
        error_msg = ""

        def on_result(text, is_final):
            nonlocal result_text
            result_text = text

        def on_error(ws, error):
            nonlocal error_msg
            error_msg = str(error)

        streamer = XunfeiStreamer(
            app_id=self.app_id,
            api_key=self.api_key,
            api_secret=self.api_secret,
            language=self.language,
            on_result=on_result,
        )

        if streamer.start():
            streamer.send_audio(audio_data)
            result_text = streamer.stop()

        return result_text

    def is_available(self) -> bool:
        """检查配置是否完整"""
        return bool(self.app_id and self.api_key and self.api_secret)

    @property
    def name(self) -> str:
        return "xunfei"