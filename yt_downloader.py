import os
import sys
import urllib.request
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor, QCursor, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar, QFileDialog,
    QButtonGroup, QRadioButton, QFrame, QGraphicsDropShadowEffect,
    QComboBox, QSizePolicy, QGraphicsOpacityEffect
)

try:
    import yt_dlp
except ImportError:
    print("Приложение не может быть запущено. Пожалуйста, установите yt-dlp: pip install yt-dlp")
    sys.exit(1)

# Цветовая палитра
P = {
    "bg": "#0F0F13",
    "surface": "#1A1A24",
    "surface2": "#22222F",
    "border": "#2E2E40",
    "accent": "#6C63FF",
    "accent_h": "#8B84FF",
    "accent_p": "#5148D4",
    "danger": "#FF5B5B",
    "success": "#4BFFB5",
    "text": "#EEEEF5",
    "muted": "#7A7A9A",
}

APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {P['bg']};
    color: {P['text']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
}}
QLineEdit {{
    background-color: {P['surface']};
    border: 1.5px solid {P['border']};
    border-radius: 12px;
    color: {P['text']};
    font-size: 14px;
    padding: 12px 16px;
    selection-background-color: {P['accent']};
}}
QLineEdit:focus {{ border-color: {P['accent']}; }}
QPushButton#btnDownload {{
    background-color: {P['accent']};
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    padding: 13px 28px;
}}
QPushButton#btnDownload:hover    {{ background-color: {P['accent_h']}; }}
QPushButton#btnDownload:pressed  {{ background-color: {P['accent_p']}; }}
QPushButton#btnDownload:disabled {{ background-color: {P['surface2']}; color: {P['muted']}; }}
QPushButton#btnFolder {{
    background-color: {P['surface2']};
    color: {P['text']};
    border: 1.5px solid {P['border']};
    border-radius: 10px;
    font-size: 13px;
    padding: 10px 18px;
}}
QPushButton#btnFolder:hover  {{ background-color: {P['surface']}; border-color: {P['accent']}; color: {P['accent']}; }}
QPushButton#btnFolder:pressed {{ background-color: {P['bg']}; }}
QRadioButton {{
    color: {P['muted']};
    font-size: 14px;
    spacing: 8px;
}}
QRadioButton:checked {{ color: {P['text']}; font-weight: 600; }}
QRadioButton::indicator {{
    width: 18px; height: 18px;
    border-radius: 9px;
    border: 2px solid {P['border']};
    background: {P['surface']};
}}
QRadioButton::indicator:checked {{
    border-color: {P['accent']};
    background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,fx:0.5,fy:0.5,
        stop:0 {P['accent']}, stop:0.55 {P['accent']},
        stop:0.56 {P['surface']}, stop:1 {P['surface']});
}}
QProgressBar {{
    background-color: {P['surface2']};
    border-radius: 6px;
    border: none;
    height: 10px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {P['accent']}, stop:1 {P['accent_h']});
    border-radius: 6px;
}}
QFrame#sep {{ background-color: {P['border']}; border: none; max-height: 1px; }}
QFrame#card {{
    background: {P['surface']};
    border: 1.5px solid {P['border']};
    border-radius: 18px;
}}
QFrame#previewCard {{
    background: {P['surface2']};
    border: 1.5px solid {P['border']};
    border-radius: 14px;
}}
QComboBox {{
    background-color: {P['surface']};
    border: 1.5px solid {P['border']};
    border-radius: 10px;
    color: {P['text']};
    font-size: 13px;
    padding: 9px 14px;
    min-width: 160px;
}}
QComboBox:hover {{ border-color: {P['accent']}; }}
QComboBox:focus {{ border-color: {P['accent']}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background-color: {P['surface2']};
    border: 1.5px solid {P['border']};
    color: {P['text']};
    selection-background-color: {P['accent']};
    padding: 4px;
    outline: none;
}}
"""

def get_yt_dlp_base_opts():
    """Базовые настройки yt-dlp."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extractor_retries": 3,
        "sleep_interval": 1,
        "max_sleep_interval": 2,
        "http_headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        }
    }
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    return opts


class UserCancelledError(Exception):
    pass


class FetchWorker(QObject):
    ready = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        opts = get_yt_dlp_base_opts()
        opts["skip_download"] = True
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            self.ready.emit(info)
        except Exception as e:
            msg = str(e)
            if "drm protected" in msg.lower() or "drm" in msg.lower():
                msg = "Видео защищено (DRM) и не может быть скачано."
            elif "bot" in msg.lower() or "sign in" in msg.lower():
                msg = "Блокировка сервиса. Создайте файл cookies.txt рядом с программой."
            elif "Unsupported URL" in msg:
                msg = "Сайт не поддерживается."
            elif "Video unavailable" in msg or "unavailable" in msg.lower():
                msg = "Видео недоступно или удалено."
            else:
                msg = "Не удалось получить информацию о видео."
            self.failed.emit(msg)


class PreviewCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewCard")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        self._thumb = QLabel()
        self._thumb.setFixedSize(160, 90)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setStyleSheet(f"background:{P['surface']}; border-radius:8px; color:{P['muted']}; font-size:11px;")
        self._thumb.setText("…")
        layout.addWidget(self._thumb)

        meta = QVBoxLayout()
        meta.setSpacing(6)
        meta.setContentsMargins(0, 0, 0, 0)

        self._lbl_title = QLabel()
        self._lbl_title.setWordWrap(True)
        self._lbl_title.setStyleSheet(f"font-size:14px; font-weight:700; color:{P['text']};")

        self._lbl_dur = QLabel()
        self._lbl_dur.setStyleSheet(f"font-size:12px; color:{P['muted']};")

        self._lbl_uploader = QLabel()
        self._lbl_uploader.setStyleSheet(f"font-size:12px; color:{P['muted']};")

        meta.addWidget(self._lbl_title)
        meta.addWidget(self._lbl_uploader)
        meta.addWidget(self._lbl_dur)
        meta.addStretch()

        layout.addLayout(meta, 1)

        # Настройка анимации появления карточки
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim_opacity = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_opacity.setDuration(400)
        self.anim_opacity.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def set_info(self, title: str, uploader: str, duration_s: int):
        t = title if len(title) <= 80 else title[:77] + "…"
        self._lbl_title.setText(t)
        self._lbl_uploader.setText(f"👤  {uploader}" if uploader else "")
        if duration_s:
            m, s = divmod(int(duration_s), 60)
            h, m = divmod(m, 60)
            dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            self._lbl_dur.setText(f"🕒  {dur}")
        
        # Плавное появление
        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.anim_opacity.setStartValue(0.0)
        self.anim_opacity.setEndValue(1.0)
        self.anim_opacity.start()

    def set_thumbnail(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            160, 90,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (scaled.width() - 160) // 2
        y = (scaled.height() - 90) // 2
        cropped = scaled.copy(x, y, 160, 90)
        self._thumb.setPixmap(cropped)

    def reset(self):
        self.anim_opacity.stop()
        self._thumb.clear()
        self._thumb.setText("…")
        self._lbl_title.setText("")
        self._lbl_uploader.setText("")
        self._lbl_dur.setText("")
        self.hide()
        self.opacity_effect.setOpacity(0.0)


class ThumbnailLoader(QObject):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            px = QPixmap()
            px.loadFromData(data)
            if not px.isNull():
                self.loaded.emit(px)
        except Exception:
            pass


class DownloadWorker(QObject):
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    filename = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url: str, save_dir: str, audio_only: bool, target_height: str = ""):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self.audio_only = audio_only
        self.target_height = target_height 
        self._cancelled = False

    def _hook(self, d: dict):
        if self._cancelled:
            raise UserCancelledError("Загрузка отменена")

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                self.progress.emit(downloaded / total * 100)
            fname = d.get("filename", "")
            if fname:
                self.filename.emit(Path(fname).name)
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            parts = [s for s in [speed, eta] if s and s != "Unknown"]
            self.status.emit("Скачивание…  " + " · ".join(parts) if parts else "Скачивание…")

        elif d.get("status") == "finished":
            self.progress.emit(100.0)
            self.status.emit("Обработка файла…")

    def run(self):
        outtmpl = os.path.join(self.save_dir, "%(title)s.%(ext)s")
        ydl_opts = get_yt_dlp_base_opts()
        ydl_opts.update({
            "outtmpl": outtmpl,
            "progress_hooks": [self._hook],
            "merge_output_format": "mp4" 
        })

        if self.audio_only:
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        elif self.target_height:
            h = self.target_height
            ydl_opts["format"] = f"bestvideo[height={h}]+bestaudio/best[height={h}]/bestvideo+bestaudio/best"
        else:
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            if not self._cancelled:
                self.finished.emit(True, "Готово! Файл сохранён.")
        except UserCancelledError:
            self.finished.emit(False, "Загрузка отменена.")
        except yt_dlp.utils.DownloadCancelled:
            self.finished.emit(False, "Загрузка отменена.")
        except Exception as e:
            if self._cancelled:
                self.finished.emit(False, "Загрузка отменена.")
                return
            msg = str(e)
            if "requested format is not available" in msg.lower():
                self.finished.emit(False, "Выбранное качество недоступно. Выберите 'Авто (лучшее)'.")
            elif "drm protected" in msg.lower() or "drm" in msg.lower():
                self.finished.emit(False, "Видео защищено (DRM) и не может быть скачано.")
            elif "bot" in msg.lower() or "sign in" in msg.lower():
                self.finished.emit(False, "Ошибка сервиса: нужны cookies (cookies.txt).")
            elif "Unsupported URL" in msg:
                self.finished.emit(False, "Сайт не поддерживается.")
            else:
                self.finished.emit(False, f"Ошибка загрузки.")

    def cancel(self):
        self._cancelled = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._thread: QThread | None = None
        self._worker: DownloadWorker | None = None
        self._fetch_thread: QThread | None = None
        self._fetch_worker: FetchWorker | None = None
        self._thumb_thread: QThread | None = None
        self._thumb_worker: ThumbnailLoader | None = None
        
        self._old_threads = []
        
        self._save_dir: str = str(Path.home() / "Downloads")
        self._format_map: dict[str, str] = {}
        Path(self._save_dir).mkdir(parents=True, exist_ok=True)

        # Настройка таймера для анимации текста "Загрузка..."
        self._dot_count = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(400)
        self._loading_timer.timeout.connect(self._update_loading_text)

        self.setWindowTitle("YT Downloader")
        self.setMinimumSize(580, 530)
        self.resize(640, 640)
        self._build_ui()

        # Плавное появление главного окна
        self.setWindowOpacity(0.0)
        self.win_anim = QPropertyAnimation(self, b"windowOpacity")
        self.win_anim.setDuration(500)
        self.win_anim.setStartValue(0.0)
        self.win_anim.setEndValue(1.0)
        self.win_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.win_anim.start()

    def _update_loading_text(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self.lbl_status.setText(f"Получение информации о видео{dots}")

    def _play_btn_anim(self, target_opacity: float):
        if not self.btn_download.isEnabled(): return
        self.btn_anim.stop()
        self.btn_anim.setStartValue(self.btn_opacity.opacity())
        self.btn_anim.setEndValue(target_opacity)
        self.btn_anim.start()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer  = QVBoxLayout(root)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(18)

        # Header
        title = QLabel("YT Downloader")
        title.setStyleSheet(f"font-size:24px; font-weight:800; color:{P['text']}; letter-spacing:-0.5px;")
        sub = QLabel("YouTube · TikTok · Instagram · SoundCloud и другие")
        sub.setStyleSheet(f"font-size:13px; color:{P['muted']};")
        lay.addWidget(title)
        lay.addWidget(sub)

        sep1 = QFrame(); sep1.setObjectName("sep"); sep1.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep1)

        # URL row
        lbl_url = QLabel("Ссылка на видео")
        lbl_url.setStyleSheet(f"font-size:13px; color:{P['muted']};")
        lay.addWidget(lbl_url)

        url_row = QHBoxLayout(); url_row.setSpacing(10)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=…")
        self.url_input.setClearButtonEnabled(True)
        url_row.addWidget(self.url_input, 1)

        self._fetch_timer = QTimer(self)
        self._fetch_timer.setSingleShot(True)
        self._fetch_timer.setInterval(900)
        self._fetch_timer.timeout.connect(self._trigger_fetch)
        self.url_input.textChanged.connect(self._on_url_changed)

        self.btn_folder = QPushButton("📁  Папка")
        self.btn_folder.setObjectName("btnFolder")
        self.btn_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_folder.clicked.connect(self._choose_folder)
        url_row.addWidget(self.btn_folder)
        lay.addLayout(url_row)

        lbl_fmt = QLabel("Формат")
        lbl_fmt.setStyleSheet(f"font-size:13px; color:{P['muted']};")
        lay.addWidget(lbl_fmt)

        radio_row = QHBoxLayout(); radio_row.setSpacing(24)
        self.radio_video = QRadioButton("🎬  Видео")
        self.radio_audio = QRadioButton("🎵  Аудио (MP3)")
        self.radio_video.setChecked(True)
        self._fmt_group = QButtonGroup()
        self._fmt_group.addButton(self.radio_video, 0)
        self._fmt_group.addButton(self.radio_audio, 1)
        radio_row.addWidget(self.radio_video)
        radio_row.addWidget(self.radio_audio)

        self.combo_quality = QComboBox()
        self.combo_quality.setToolTip("Выберите качество видео")
        self.combo_quality.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_quality.addItem("⏳ Вставьте ссылку…")
        self.combo_quality.setEnabled(False)
        radio_row.addWidget(self.combo_quality)
        radio_row.addStretch()

        self.radio_video.toggled.connect(lambda checked: self.combo_quality.setVisible(checked))
        lay.addLayout(radio_row)

        self.preview_card = PreviewCard()
        lay.addWidget(self.preview_card)

        sep_pre = QFrame(); sep_pre.setObjectName("sep"); sep_pre.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep_pre)

        # Download button
        self.btn_download = QPushButton("⬇  Скачать")
        self.btn_download.setObjectName("btnDownload")
        self.btn_download.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_download.clicked.connect(self._start_or_cancel)
        self.btn_download.setEnabled(False)
        lay.addWidget(self.btn_download)

        # Анимация кнопки
        self.btn_opacity = QGraphicsOpacityEffect(self.btn_download)
        self.btn_download.setGraphicsEffect(self.btn_opacity)
        self.btn_anim = QPropertyAnimation(self.btn_opacity, b"opacity")
        self.btn_anim.setDuration(120)
        self.btn_download.pressed.connect(lambda: self._play_btn_anim(0.6))
        self.btn_download.released.connect(lambda: self._play_btn_anim(1.0))

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        lay.addWidget(self.progress_bar)

        # Анимация Progress Bar
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_anim.setDuration(300)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        pct_row = QHBoxLayout()
        self.lbl_filename = QLabel("")
        self.lbl_filename.setStyleSheet(f"font-size:13px; color:{P['text']}; font-weight:500;")
        self.lbl_filename.setWordWrap(True)
        self.lbl_pct = QLabel("")
        self.lbl_pct.setStyleSheet(f"font-size:13px; color:{P['accent']}; font-weight:700;")
        self.lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pct_row.addWidget(self.lbl_filename, 1)
        pct_row.addWidget(self.lbl_pct)
        lay.addLayout(pct_row)

        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setStyleSheet(f"font-size:13px; color:{P['muted']};")
        lay.addWidget(self.lbl_status)

        lay.addStretch()

        sep2 = QFrame(); sep2.setObjectName("sep"); sep2.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep2)
        self.lbl_folder = QLabel(f"Папка: {self._save_dir}")
        self.lbl_folder.setStyleSheet(f"font-size:12px; color:{P['muted']};")
        self.lbl_folder.setWordWrap(True)
        lay.addWidget(self.lbl_folder)

    def _safe_quit_thread(self, thread_obj, worker_obj=None):
        if thread_obj is None:
            return
        try:
            if worker_obj and hasattr(worker_obj, 'cancel'):
                worker_obj.cancel()
        except Exception:
            pass
        try:
            if thread_obj.isRunning():
                self._old_threads.append(thread_obj)
                thread_obj.finished.connect(lambda t=thread_obj: self._cleanup_old_thread(t))
                thread_obj.quit()
        except RuntimeError:
            pass 

    def _cleanup_old_thread(self, thread_obj):
        if thread_obj in self._old_threads:
            self._old_threads.remove(thread_obj)

    def _on_url_changed(self, text: str):
        self.preview_card.reset()
        self._reset_quality_combo()
        self.btn_download.setEnabled(False) 
        if text.strip().startswith("http"):
            self._fetch_timer.start()
        else:
            self._fetch_timer.stop()
            self._set_status("Готов к работе", P["muted"])

    def _trigger_fetch(self):
        url = self.url_input.text().strip()
        if not url.startswith("http"):
            return

        self._safe_quit_thread(self._fetch_thread, self._fetch_worker)

        self._set_status("Получение информации о видео…", P["muted"])
        self._reset_quality_combo(loading=True)

        self._fetch_worker = FetchWorker(url)
        self._fetch_thread = QThread(self)
        self._fetch_worker.moveToThread(self._fetch_thread)
        self._fetch_thread.started.connect(self._fetch_worker.run)
        
        self._fetch_worker.ready.connect(self._on_fetch_ready)
        self._fetch_worker.failed.connect(self._on_fetch_failed)
        
        self._fetch_worker.ready.connect(self._fetch_thread.quit)
        self._fetch_worker.failed.connect(self._fetch_thread.quit)
        self._fetch_thread.finished.connect(self._fetch_thread.deleteLater)
        
        self._set_inputs_enabled(False)
        self.btn_download.setEnabled(False)
        self._loading_timer.start()

        self._fetch_thread.start()

    def _on_fetch_ready(self, info: dict):
        if self.sender() != self._fetch_worker:
            return
            
        self._loading_timer.stop()
        self._set_inputs_enabled(True)

        title = info.get("title", "Без названия")
        uploader = info.get("uploader") or info.get("channel") or ""
        duration = info.get("duration", 0)
        self.preview_card.set_info(title, uploader, duration)
        self._set_status("Готово к загрузке", P["success"])
        
        self._populate_quality(info)
        self.btn_download.setEnabled(True)

        thumb_url = self._pick_thumbnail(info)
        if thumb_url:
            self._load_thumbnail(thumb_url)

    def _on_fetch_failed(self, msg: str):
        if self.sender() != self._fetch_worker:
            return
            
        self._loading_timer.stop()
        self._set_inputs_enabled(True)

        self._set_status(msg, P["danger"])
        self._reset_quality_combo()
        self.btn_download.setEnabled(False)

    def _pick_thumbnail(self, info: dict) -> str:
        thumbs = info.get("thumbnails") or []
        best = ""
        for t in thumbs:
            w = t.get("width", 0)
            url = t.get("url", "")
            if not url: continue
            if 280 <= w <= 480: return url
            best = url
        return best

    def _load_thumbnail(self, url: str):
        self._safe_quit_thread(self._thumb_thread, self._thumb_worker)

        self._thumb_worker = ThumbnailLoader(url)
        self._thumb_thread = QThread(self)
        self._thumb_worker.moveToThread(self._thumb_thread)
        self._thumb_thread.started.connect(self._thumb_worker.run)
        
        self._thumb_worker.loaded.connect(self._on_thumb_loaded)
        self._thumb_worker.loaded.connect(self._thumb_thread.quit)
        self._thumb_thread.finished.connect(self._thumb_thread.deleteLater)
        self._thumb_thread.start()

    def _on_thumb_loaded(self, pixmap: QPixmap):
        if self.sender() != self._thumb_worker:
            return
        self.preview_card.set_thumbnail(pixmap)

    def _populate_quality(self, info: dict):
        formats = info.get("formats") or []
        duration = info.get("duration") or 0
        
        # Оценка аудио (с защитой от NoneType)
        best_audio_size = 0
        for f in formats:
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                size = f.get("filesize") or f.get("filesize_approx") or 0
                if size == 0:
                    vbr = f.get("vbr") or 0
                    abr = f.get("abr") or 0
                    tbr = f.get("tbr") or (vbr + abr)
                    if tbr and duration:
                        size = (tbr * 1000 * duration) / 8
                if size > best_audio_size:
                    best_audio_size = size

        if best_audio_size == 0 and duration > 0:
            best_audio_size = (192 * 1000 * duration) / 8

        # Собираем все разрешения видео
        height_map = {}
        for f in formats:
            h = f.get("height")
            if not h:
                res = f.get("resolution", "")
                if isinstance(res, str) and "x" in res:
                    try:
                        h = int(res.split("x")[1])
                    except:
                        pass
            
            vcodec = f.get("vcodec", "none")
            fmt_id = f.get("format_id", "")
            
            if not h or type(h) is not int or vcodec == "none" or not fmt_id:
                continue
                
            if h not in height_map:
                height_map[h] = f
            else:
                curr_f = height_map[h]
                if f.get("ext") == "mp4" and curr_f.get("ext") != "mp4":
                    height_map[h] = f
                elif f.get("ext") == curr_f.get("ext"):
                    # Защита от NoneType при сравнении tbr
                    tbr_new = f.get("tbr") or 0
                    tbr_curr = curr_f.get("tbr") or 0
                    if tbr_new > tbr_curr:
                        height_map[h] = f

        quality_opts = []
        for h, f in height_map.items():
            target_h = str(h) 
            
            v_size = f.get("filesize") or f.get("filesize_approx") or 0
            if v_size == 0:
                # Защита от NoneType при расчете битрейта
                vbr = f.get("vbr") or 0
                abr = f.get("abr") or 0
                tbr = f.get("tbr") or (vbr + abr)
                if tbr and duration:
                    v_size = (tbr * 1000 * duration) / 8
            
            if f.get("acodec") != "none":
                total_size = v_size
            else:
                total_size = v_size + best_audio_size
            
            fps = f.get("fps")
            fps_str = f" {int(fps)}fps" if fps and isinstance(fps, (int, float)) and fps > 30 else ""
            
            if total_size > 0:
                mb = total_size / (1024 * 1024)
                label = f"{h}p{fps_str} (MP4) — ~{mb:.1f} МБ"
            else:
                label = f"{h}p{fps_str} (MP4) — (размер неизвестен)"
                
            quality_opts.append((h, label, target_h))

        quality_opts.sort(key=lambda x: x[0], reverse=True)

        self.combo_quality.clear()
        self._format_map.clear()
        
        if best_audio_size > 0:
            audio_mb = best_audio_size / (1024 * 1024)
            audio_label = f"🎵  Аудио (MP3) — ~{audio_mb:.1f} МБ"
        else:
            audio_label = "🎵  Аудио (MP3) — (размер неизвестен)"
            
        self.radio_audio.setText(audio_label)

        if not quality_opts:
            self.combo_quality.addItem("Авто (лучшее)")
            self._format_map["Авто (лучшее)"] = ""
        else:
            self.combo_quality.addItem("Авто (лучшее)")
            self._format_map["Авто (лучшее)"] = ""
            for _, label, height_str in quality_opts:
                self.combo_quality.addItem(label)
                self._format_map[label] = height_str 

        self.combo_quality.setEnabled(True)

    def _reset_quality_combo(self, loading: bool = False):
        self.combo_quality.clear()
        self._format_map.clear()
        if loading:
            self.combo_quality.addItem("⏳ Загрузка…")
        else:
            self.combo_quality.addItem("⏳ Вставьте ссылку…")
        self.combo_quality.setEnabled(False)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для сохранения", self._save_dir)
        if folder:
            self._save_dir = folder
            self.lbl_folder.setText(f"Папка: {folder}")

    def _start_or_cancel(self):
        try:
            if self._thread is not None and self._thread.isRunning():
                if self._worker:
                    self._worker.cancel()
                self.btn_download.setText("✖  Остановка...")
                self.btn_download.setEnabled(False)
                return
        except RuntimeError:
            pass

        url = self.url_input.text().strip()
        if not url: return

        target_height = ""
        if not self.radio_audio.isChecked():
            selected_label = self.combo_quality.currentText()
            target_height = self._format_map.get(selected_label, "")

        self._worker = DownloadWorker(url, self._save_dir, self.radio_audio.isChecked(), target_height)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(lambda t: self._set_status(t, P["muted"]) if self.sender() == self._worker else None)
        self._worker.filename.connect(lambda n: self.lbl_filename.setText(n[:70] + "…" if len(n) > 70 else n) if self.sender() == self._worker else None)
        self._worker.finished.connect(self._on_finished)
        
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self.progress_bar.setValue(0)
        self.lbl_pct.setText("0%")
        self.lbl_filename.setText("")
        self._set_status("Начало загрузки…", P["muted"])
        self.btn_download.setText("✖  Отменить")
        self._set_inputs_enabled(False)
        self.btn_download.setEnabled(True)
        self._thread.start()

    def _on_progress(self, pct: float):
        if self.sender() != self._worker:
            return
        self.progress_anim.setStartValue(self.progress_bar.value())
        self.progress_anim.setEndValue(int(pct))
        self.progress_anim.start()
        self.lbl_pct.setText(f"{pct:.0f}%")

    def _on_finished(self, ok: bool, msg: str):
        if self.sender() != self._worker:
            return
            
        self._thread = None
        self._worker = None
        color = P["success"] if ok else P["danger"]
        self._set_status(msg, color)
        self.btn_download.setText("⬇  Скачать")
        self.btn_download.setEnabled(True)
        self._set_inputs_enabled(True)
        if ok:
            self.progress_anim.stop()
            self.progress_bar.setValue(100)
            self.lbl_pct.setText("100%")
            QTimer.singleShot(4000, self._reset_progress)

    def _reset_progress(self):
        self.progress_anim.stop()
        self.progress_bar.setValue(0)
        self.lbl_pct.setText("")
        self.lbl_filename.setText("")
        self._set_status("Готов к работе", P["muted"])

    def _set_status(self, text: str, color: str):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"font-size:13px; color:{color};")

    def _set_inputs_enabled(self, enabled: bool):
        for w in (self.url_input, self.radio_video, self.radio_audio, self.btn_folder):
            w.setEnabled(enabled)
        if enabled and self.radio_video.isChecked() and self.combo_quality.count() > 0:
            self.combo_quality.setEnabled(True)
        elif not enabled:
            self.combo_quality.setEnabled(False)

    def closeEvent(self, event):
        self._safe_quit_thread(self._thread, self._worker)
        self._safe_quit_thread(self._fetch_thread, self._fetch_worker)
        self._safe_quit_thread(self._thumb_thread, self._thumb_worker)
        
        for t in self._old_threads:
            if t.isRunning():
                t.wait(1000)
                
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("YT Downloader")
    app.setStyle("Fusion")

    pal = QPalette()
    for role, hex_color in [
        (QPalette.ColorRole.Window, P["bg"]),
        (QPalette.ColorRole.WindowText, P["text"]),
        (QPalette.ColorRole.Base, P["surface"]),
        (QPalette.ColorRole.AlternateBase, P["surface2"]),
        (QPalette.ColorRole.Text, P["text"]),
        (QPalette.ColorRole.Button, P["surface2"]),
        (QPalette.ColorRole.ButtonText, P["text"]),
        (QPalette.ColorRole.Highlight, P["accent"]),
        (QPalette.ColorRole.HighlightedText, "#FFFFFF"),
    ]:
        pal.setColor(role, QColor(hex_color))
    app.setPalette(pal)
    app.setStyleSheet(APP_STYLE)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
