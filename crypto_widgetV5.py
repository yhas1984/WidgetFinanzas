#!/usr/bin/env python3

import faulthandler
import json
import logging
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_runtime_environment():
    """Reduce hilos nativos y evita seleccionar un plugin Deepin no empaquetado."""
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(variable, "1")

    platform = os.environ.get("QT_QPA_PLATFORM", "")
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "x11" and platform.split(";", 1)[0] == "dxcb":
        os.environ["QT_QPA_PLATFORM"] = "xcb"


configure_runtime_environment()

import yfinance as yf
from PyQt5.QtCore import QObject, QPoint, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QIcon, QPainter
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

APP_NAME = "Widget Finanzas"
APP_SLUG = "widget-finanzas"
VERSION = "5.0.4"
VALID_POSITIONS = {
    "top-left", "top-center", "top-right",
    "bottom-left", "bottom-center", "bottom-right",
}
DEFAULT_CONFIG = {
    "currency": "usd",
    "update_interval_seconds": 60,
    "run_on_startup": False,
    "desktop_mode": True,
    "position": "top-center",
    "window_width": 1000,
    "window_height": 50,
    "assets": [],
    "icons": {},
}

logger = logging.getLogger(APP_SLUG)
_crash_log_handle = None


def _xdg_dir(env_name, fallback):
    configured = os.environ.get(env_name)
    return Path(configured).expanduser() if configured else Path.home() / fallback


def app_paths():
    """Devuelve rutas por usuario sin escribir dentro de /opt."""
    return {
        "config": _xdg_dir("XDG_CONFIG_HOME", ".config") / APP_SLUG,
        "cache": _xdg_dir("XDG_CACHE_HOME", ".cache") / APP_SLUG,
        "state": _xdg_dir("XDG_STATE_HOME", ".local/state") / APP_SLUG,
    }


def setup_logging(log_dir):
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "widget-finanzas.log",
            maxBytes=512_000,
            backupCount=2,
            encoding="utf-8",
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logger.addHandler(handler)


def setup_crash_logging(log_dir):
    """Conserva trazas de excepciones y fallos nativos que antes quedaban ocultos."""
    global _crash_log_handle
    if _crash_log_handle is not None:
        return
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _crash_log_handle = (log_dir / "crash.log").open(
            "a", encoding="utf-8", buffering=1
        )
        faulthandler.enable(_crash_log_handle, all_threads=True)
    except (OSError, RuntimeError) as exc:
        logger.warning("No se pudo activar el registro de fallos nativos: %s", exc)

    previous_hook = sys.excepthook

    def exception_hook(exc_type, value, traceback):
        logger.critical(
            "Excepción no controlada",
            exc_info=(exc_type, value, traceback),
        )
        previous_hook(exc_type, value, traceback)

    exception_hook._widget_finanzas_hook = True
    if not getattr(sys.excepthook, "_widget_finanzas_hook", False):
        sys.excepthook = exception_hook


def read_json(path, default=None):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else (default or {})
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("No se pudo leer %s: %s", path, exc)
        return default or {}


def write_json_atomic(path, value):
    """Escribe JSON de forma atómica y tolera sistemas de archivos de solo lectura."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise
        return True
    except OSError as exc:
        logger.warning("No se pudo escribir %s: %s", path, exc)
        return False


def _validated_int(value, default, minimum, maximum, field, warnings):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        warnings.append(f"{field} debe ser un número entero")
        return default
    if parsed < minimum or parsed > maximum:
        warnings.append(f"{field} debe estar entre {minimum} y {maximum}")
        return default
    return parsed


def validate_config(raw):
    """Normaliza configuración no confiable sin impedir que arranque el widget."""
    raw = raw if isinstance(raw, dict) else {}
    config = dict(DEFAULT_CONFIG)
    warnings = []

    currency = raw.get("currency", config["currency"])
    if isinstance(currency, str) and 2 <= len(currency.strip()) <= 5:
        config["currency"] = currency.strip().lower()
    else:
        warnings.append("currency no es válida")

    config["update_interval_seconds"] = _validated_int(
        raw.get("update_interval_seconds", config["update_interval_seconds"]),
        config["update_interval_seconds"], 30, 86_400,
        "update_interval_seconds", warnings,
    )
    config["window_width"] = _validated_int(
        raw.get("window_width", config["window_width"]),
        config["window_width"], 240, 7680, "window_width", warnings,
    )
    config["window_height"] = _validated_int(
        raw.get("window_height", config["window_height"]),
        config["window_height"], 32, 1080, "window_height", warnings,
    )
    config["run_on_startup"] = bool(raw.get("run_on_startup", False))
    config["desktop_mode"] = bool(raw.get("desktop_mode", True))

    position = raw.get("position", config["position"])
    if position in VALID_POSITIONS:
        config["position"] = position
    else:
        warnings.append("position no es válida")

    icons = raw.get("icons", {})
    config["icons"] = {
        str(key): str(value) for key, value in icons.items()
    } if isinstance(icons, dict) else {}

    assets = raw.get("assets", [])
    if not isinstance(assets, list):
        warnings.append("assets debe ser una lista")
        assets = []
    valid_assets = []
    seen_ids = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            warnings.append(f"assets[{index}] no es un objeto")
            continue
        required = ("id", "symbol", "yf_symbol")
        if any(not isinstance(asset.get(key), str) or not asset[key].strip() for key in required):
            warnings.append(f"assets[{index}] no tiene id, symbol o yf_symbol válido")
            continue
        if asset["id"] in seen_ids:
            warnings.append(f"id duplicado: {asset['id']}")
            continue
        color = asset.get("color", "#FFFFFF")
        if not QColor(str(color)).isValid():
            warnings.append(f"color no válido para {asset['id']}")
            color = "#FFFFFF"
        normalized = dict(asset)
        normalized["color"] = str(color)
        try:
            normalized["scale"] = float(asset.get("scale", 1))
            if not math.isfinite(normalized["scale"]) or normalized["scale"] <= 0:
                raise ValueError("scale debe ser positiva")
        except (TypeError, ValueError):
            normalized["scale"] = 1.0
            warnings.append(f"scale no válida para {asset['id']}")
        seen_ids.add(asset["id"])
        valid_assets.append(normalized)
    config["assets"] = valid_assets
    return config, warnings


def load_config(application_path, user_config_path):
    bundled = read_json(Path(application_path) / "config.json", {})
    user = read_json(user_config_path, {}) if Path(user_config_path).exists() else {}
    merged = dict(bundled)
    merged.update(user)
    config, warnings = validate_config(merged)
    for message in warnings:
        logger.warning("Configuración: %s", message)
    return config


def format_price(price, asset, fallback_currency="usd"):
    quote_currency = asset.get("quote_currency", fallback_currency)
    symbols = {"usd": "$", "eur": "€", "gbp": "£", "jpy": "¥"}
    prefix = "" if quote_currency in (None, "", "points") else symbols.get(
        str(quote_currency).lower(), f"{str(quote_currency).upper()} "
    )
    if price >= 1000:
        return f"{prefix}{price:,.0f}"
    if price >= 1:
        return f"{prefix}{price:,.2f}"
    return f"{prefix}{price:.4f}"

# ---------------- Worker de datos ----------------
class DataWorker(QObject):
    data_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, assets, currency, cache_path):
        super().__init__()
        self.assets = assets
        self.currency = currency
        self.cache_path = Path(cache_path)

    def _fetch_yfinance_data(self, symbols_list):
        """Obtiene los últimos cierres en una sola solicitud limitada."""
        symbols_list = list(dict.fromkeys(symbols_list))
        symbols_str = " ".join(symbols_list)
        last_error = None
        for attempt in range(2):
            if QThread.currentThread().isInterruptionRequested():
                return []
            try:
                data = yf.download(
                    symbols_str,
                    period="5d",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    prepost=True,
                    threads=False,
                    progress=False,
                    timeout=8,
                )
                if data is not None and not data.empty:
                    break
                last_error = RuntimeError("Yahoo Finance devolvió una respuesta vacía")
            except Exception as exc:  # noqa: BLE001 - frontera de la librería de red
                last_error = exc
            if attempt == 0:
                time.sleep(1.0)
        else:
            raise RuntimeError(str(last_error or "No se recibieron cotizaciones"))

        results = []
        for symbol in symbols_list:
            try:
                top_level = data.columns.get_level_values(0)
                if len(symbols_list) == 1 and "Close" in top_level:
                    symbol_data = data
                else:
                    symbol_data = data[symbol] if symbol in top_level else None
                if symbol_data is None or symbol_data.empty:
                    logger.warning("Yahoo Finance no devolvió datos para %s", symbol)
                    continue
                closes = symbol_data["Close"].dropna()
                if getattr(closes, "ndim", 1) > 1:
                    closes = closes.iloc[:, 0].dropna()
                if closes.empty:
                    continue
                current_price = float(closes.iloc[-1])
                if not math.isfinite(current_price) or current_price <= 0:
                    continue
                change_pct = 0.0
                if len(closes) >= 2:
                    previous_price = float(closes.iloc[-2])
                    if math.isfinite(previous_price) and previous_price > 0:
                        change_pct = ((current_price - previous_price) / previous_price) * 100
                results.append({
                    "symbol": symbol,
                    "current_price": current_price,
                    "price_change_percentage_24h": change_pct,
                })
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                logger.warning("No se pudo procesar %s: %s", symbol, exc)
        return results

    def _cached_prices(self):
        document = read_json(self.cache_path, {})
        raw_prices = document.get("prices", {})
        if not isinstance(raw_prices, dict):
            return {}
        valid = {}
        for asset_id, item in raw_prices.items():
            if not isinstance(item, dict):
                continue
            try:
                price = float(item["current_price"])
                change = float(item.get("price_change_percentage_24h", 0.0))
            except (KeyError, TypeError, ValueError):
                continue
            if math.isfinite(price) and price > 0 and math.isfinite(change):
                cached = dict(item)
                cached["current_price"] = price
                cached["price_change_percentage_24h"] = change
                cached["cached"] = True
                valid[str(asset_id)] = cached
        return valid

    def _store_prices(self, fresh_prices, cached_prices):
        merged = {key: dict(value) for key, value in cached_prices.items()}
        now = datetime.now(timezone.utc).isoformat()
        for item in fresh_prices:
            stored = dict(item)
            stored.pop("cached", None)
            stored["updated_at"] = now
            merged[item["id"]] = stored
        write_json_atomic(self.cache_path, {
            "version": 1,
            "updated_at": now,
            "prices": merged,
        })

    def _result_from_cache(self, cached_prices, error=None):
        prices = []
        for asset in self.assets:
            cached = cached_prices.get(asset["id"])
            if cached:
                item = dict(cached)
                item["id"] = asset["id"]
                item["symbol"] = asset["symbol"]
                item["cached"] = True
                prices.append(item)
        return {"prices": prices, "stale": bool(prices), "error": error}

    @pyqtSlot()
    def run(self):
        cached_prices = self._cached_prices()
        try:
            all_symbols = [asset["yf_symbol"] for asset in self.assets]
            if not all_symbols:
                self.data_updated.emit({"prices": [], "stale": False, "error": None})
                return

            yf_data = self._fetch_yfinance_data(all_symbols)
            by_symbol = {item["symbol"]: item for item in yf_data}
            fresh_prices = []
            result_prices = []
            for asset in self.assets:
                item = by_symbol.get(asset["yf_symbol"])
                if item:
                    price = item["current_price"] * float(asset.get("scale", 1.0))
                    fresh = {
                        "id": asset["id"],
                        "symbol": asset["symbol"],
                        "current_price": price,
                        "price_change_percentage_24h": item["price_change_percentage_24h"],
                        "cached": False,
                    }
                    fresh_prices.append(fresh)
                    result_prices.append(fresh)
                elif asset["id"] in cached_prices:
                    cached = dict(cached_prices[asset["id"]])
                    cached["id"] = asset["id"]
                    cached["symbol"] = asset["symbol"]
                    cached["cached"] = True
                    result_prices.append(cached)

            if fresh_prices:
                self._store_prices(fresh_prices, cached_prices)
            if not result_prices:
                self.error_occurred.emit("No se recibieron cotizaciones ni existe caché local")
            else:
                self.data_updated.emit({
                    "prices": result_prices,
                    "stale": any(item.get("cached") for item in result_prices),
                    "error": None,
                })
        except Exception as exc:  # noqa: BLE001 - protege el hilo y recupera la caché
            logger.warning("Actualización fallida: %s", exc)
            cached_result = self._result_from_cache(cached_prices, str(exc))
            if cached_result["prices"]:
                self.data_updated.emit(cached_result)
            else:
                self.error_occurred.emit(str(exc))
        finally:
            self.finished.emit()

    @pyqtSlot()
    def stop(self):
        """Detiene el hilo persistente desde su propio bucle de eventos."""
        current_thread = QThread.currentThread()
        app = QApplication.instance()
        if app is not None:
            self.moveToThread(app.thread())
        current_thread.quit()

# ---------------- Etiqueta scrolleable con efectos ----------------
class ScrollingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_text_offset)
        self.timer.start(30)
        self.segments = []
        self.total_width = 0
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Para efectos de parpadeo - INICIALIZAR ANTES
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.update_blink)
        self.blink_timer.start(500)  # Parpadeo cada 500ms
        self.blink_state = True
        self.blinking_segments = set()  # IDs de segmentos que deben parpadear
        
        # Ahora sí podemos llamar set_status_text
        self.set_status_text("Cargando datos...", "#FFFFFF")
        
        # Diccionario de iconos
        self.icons = {
            "BTC": "₿",
            "ETH": "Ξ", 
            "HBAR": "ℏ",
            "S&P500": "📈",
            "GOLD": "🥇",
            "OIL": "🛢️",
            "NASDAQ": "🏛️",
            "DOW": "📊",
            "TSLA": "🚗",
            "AAPL": "🍎",
            "EUR/USD": "💱",
            "USD/EUR": "💰"
        }

    def get_icon(self, symbol):
        """Obtiene el icono para un símbolo dado"""
        return self.icons.get(symbol, "📋")

    def update_text_offset(self):
        if self.total_width <= self.width():
            self.text_offset = 0
        else:
            self.text_offset -= 1
            if self.text_offset < -self.total_width:
                self.text_offset = 0
        self.update()

    def update_blink(self):
        """Actualiza el estado del parpadeo"""
        self.blink_state = not self.blink_state
        if self.blinking_segments:
            self.update()

    def set_colored_text(self, segments, blinking_items=None):
        """Establece texto coloreado con posibles elementos parpadeantes"""
        self.segments = segments
        self.blinking_segments = set(blinking_items or [])
        self.total_width = sum(self.fontMetrics().horizontalAdvance(text) for text, _, _ in segments)
        self.text_offset = 0
        self.timer.start()

    def set_status_text(self, text, color="#CCCCCC"):
        self.timer.stop()
        self.segments = [(text, color, None)]
        self.total_width = self.fontMetrics().horizontalAdvance(text)
        self.blinking_segments.clear()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self.font())
        y = (self.height() - p.fontMetrics().height()) // 2 + p.fontMetrics().ascent()
        start_x = self.text_offset if self.total_width > self.width() else (self.width() - self.total_width) // 2
        x = start_x
        
        for text, color, segment_id in self.segments:
            # Aplicar efecto de parpadeo si corresponde
            if segment_id in self.blinking_segments and not self.blink_state:
                # Color más tenue durante el parpadeo
                temp_color = QColor(color)
                temp_color.setAlpha(100)  # Más transparente
                p.setPen(temp_color)
            else:
                p.setPen(QColor(color))
            
            p.drawText(x, y, text)
            x += self.fontMetrics().horizontalAdvance(text)
        
        # Duplicar texto para scroll infinito
        if self.total_width > self.width():
            x2 = start_x + self.total_width + 50
            for text, color, segment_id in self.segments:
                if segment_id in self.blinking_segments and not self.blink_state:
                    temp_color = QColor(color)
                    temp_color.setAlpha(100)
                    p.setPen(temp_color)
                else:
                    p.setPen(QColor(color))
                p.drawText(x2, y, text)
                x2 += self.fontMetrics().horizontalAdvance(text)

# ---------------- Widget principal ----------------
class CryptoWidget(QMainWindow):
    update_requested = pyqtSignal()
    stop_worker_requested = pyqtSignal()

    def __init__(self, config, cache_path, state_path):
        super().__init__()
        self.config = config
        self.cache_path = Path(cache_path)
        self.state_path = Path(state_path)
        self.window_width = self.config["window_width"]
        self.window_height = self.config["window_height"]
        self.worker = None
        self.thread = None
        self._closing = False
        self._quit_requested = False
        self._update_in_progress = False
        self._stop_requested = False
        self.previous_prices = {}  # Para detectar cambios
        self.drag_position = QPoint()
        self.is_dragging = False
        self.init_ui()
        self.load_styles()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.trigger_update)
        self.update_timer.start(self.config["update_interval_seconds"] * 1000)
        self.visibility_timer = QTimer(self)
        self.visibility_timer.timeout.connect(self.ensure_visible)
        self.visibility_timer.start(10_000)
        self._start_worker_thread()
        self.trigger_update()

    def check_autostart(self):
        """Mantiene una sola entrada de autoinicio y elimina launchers heredados."""
        if sys.platform != "linux":
            return
        autostart_dir = _xdg_dir("XDG_CONFIG_HOME", ".config") / "autostart"
        legacy_autostart = autostart_dir / "crypto_widget.desktop"
        legacy_application = (
            _xdg_dir("XDG_DATA_HOME", ".local/share")
            / "applications" / "crypto_widget.desktop"
        )
        current_autostart = autostart_dir / f"{APP_SLUG}.desktop"

        for legacy in (legacy_autostart, legacy_application):
            try:
                if legacy.exists() and "Crypto Widget" in legacy.read_text(
                    encoding="utf-8", errors="ignore"
                ):
                    legacy.unlink()
                    logger.info("Entrada heredada eliminada: %s", legacy)
            except OSError as exc:
                logger.warning("No se pudo limpiar %s: %s", legacy, exc)

        if not self.config.get("run_on_startup", False):
            try:
                current_autostart.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("No se pudo desactivar el autoinicio: %s", exc)
            return

        if getattr(sys, "frozen", False):
            executable = "/usr/bin/widget-finanzas" if Path(
                "/usr/bin/widget-finanzas"
            ).exists() else sys.executable
            exec_cmd = f'"{executable}"'
            try_exec = executable
            icon = APP_SLUG
        else:
            script = str(Path(__file__).with_name("crypto_widget.py").resolve())
            exec_cmd = f'"{sys.executable}" "{script}"'
            try_exec = sys.executable
            icon = str(Path(__file__).with_name("icon.png").resolve())

        content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Widget de criptomonedas, mercados y divisas
Exec={exec_cmd}
TryExec={try_exec}
Icon={icon}
Terminal=false
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-WidgetFinanzas-Managed=true
"""
        try:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            temporary = current_autostart.with_suffix(".desktop.tmp")
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, current_autostart)
        except OSError as exc:
            logger.warning("No se pudo configurar el autoinicio: %s", exc)

    def init_ui(self):
        self.setWindowTitle("Ticker")
        # Integrado al escritorio: transparente; el modo escritorio es configurable
        flags = Qt.FramelessWindowHint
        if self.config.get("desktop_mode", True):
            flags |= Qt.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        if os.environ.get("XDG_SESSION_TYPE", "").lower() != "wayland":
            self.setAttribute(Qt.WA_X11NetWmWindowTypeDock, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set Application Icon
        icon_path = "icon.png"
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(os.path.dirname(sys.executable), "icon.png")
        elif os.path.exists(os.path.join(os.path.dirname(__file__), "icon.png")):
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setFixedSize(self.window_width, self.window_height)

        main = QWidget(self)
        main.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(main)

        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_label = ScrollingLabel()
        self.scroll_label.icons.update(self.config.get("icons", {}))
        self.scroll_label.setObjectName("scroll_label")
        layout.addWidget(self.scroll_label)
        
        # Configurar autostart
        self.check_autostart()

    def load_styles(self):
        self.setStyleSheet("""
            QLabel { background-color: transparent; border: none; }
            #scroll_label { font-size: 14pt; font-weight: bold; background-color: transparent; }
        """)

    def _start_worker_thread(self):
        if self._closing or (self.thread is not None and self.thread.isRunning()):
            return

        self._stop_requested = False
        thread = QThread(self)
        worker = DataWorker(
            self.config["assets"],
            self.config["currency"],
            self.cache_path,
        )
        worker.moveToThread(thread)
        self.worker = worker
        self.thread = thread
        self.update_requested.connect(worker.run, Qt.QueuedConnection)
        self.stop_worker_requested.connect(worker.stop, Qt.QueuedConnection)
        worker.data_updated.connect(self.update_ui)
        worker.error_occurred.connect(self.show_error)
        worker.finished.connect(self._update_finished)
        thread.finished.connect(self._thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        logger.info("Hilo de actualización iniciado")

    def trigger_update(self):
        if self._closing or self._update_in_progress:
            return

        if self.thread is None or not self.thread.isRunning():
            logger.warning("El hilo de actualización no estaba activo; reiniciándolo")
            self._start_worker_thread()
        if self.worker is None or self.thread is None or not self.thread.isRunning():
            logger.error("No se pudo iniciar el hilo de actualización")
            return

        self._update_in_progress = True
        logger.info("Actualización de cotizaciones iniciada")
        self.update_requested.emit()

    def _update_finished(self):
        self._update_in_progress = False
        logger.info("Actualización de cotizaciones finalizada")

    def _request_worker_stop(self):
        if self._stop_requested:
            return
        self._stop_requested = True
        if self.thread is not None and self.thread.isRunning():
            self.thread.requestInterruption()
            self.stop_worker_requested.emit()
        else:
            self._thread_finished()

    def _thread_finished(self):
        self._update_in_progress = False
        self.worker = None
        self.thread = None
        logger.info("Hilo de actualización detenido")
        if self._closing:
            QApplication.instance().quit()
        else:
            QTimer.singleShot(1_000, self._start_worker_thread)

    def ensure_visible(self):
        if not self._closing and not self.isVisible():
            logger.warning("La ventana fue ocultada externamente; restaurándola")
            self.show()

    def update_ui(self, data):
        segments = []
        price_map = {it["id"]: it for it in data.get("prices", [])}
        blinking_items = []

        for a in self.config["assets"]:
            d = price_map.get(a["id"])
            # Fallback: segmento con "--" si no hay datos de ese activo
            if not d:
                icon = self.scroll_label.get_icon(a["symbol"])
                segments.extend([
                    ("   |   ", "#555", None),
                    (f"{icon} {a['symbol']}: --", a["color"], None)
                ])
                continue

            price = d.get("current_price", 0.0) or 0.0
            chg = d.get("price_change_percentage_24h", 0.0) or 0.0

            # Detectar cambios significativos para efectos
            asset_id = a["id"]
            if asset_id in self.previous_prices and not d.get("cached"):
                old_price = self.previous_prices[asset_id]
                if old_price > 0 and abs(price - old_price) / old_price > 0.01:
                    blinking_items.append(f"{asset_id}_price")
                    blinking_items.append(f"{asset_id}_change")
            
            self.previous_prices[asset_id] = price

            # Obtener icono
            icon = self.scroll_label.get_icon(a["symbol"])

            price_str = format_price(price, a, self.config["currency"])
            stale_prefix = "⚠ " if d.get("cached") else ""
            
            # Determinar color y flecha basado en cambio
            if abs(chg) >= 5.0:  # Cambio significativo >= 5%
                if chg >= 0:
                    arrow, col = ("🚀", "#00FF00")  # Verde brillante + cohete
                else:
                    arrow, col = ("📉", "#FF0000")  # Rojo brillante + gráfico bajando
            elif abs(chg) >= 2.0:  # Cambio moderado >= 2%
                if chg >= 0:
                    arrow, col = ("⬆️", "#32CD32")
                else:
                    arrow, col = ("⬇️", "#FF4500")
            else:  # Cambio pequeño
                arrow, col = ("▲", "#32CD32") if chg >= 0 else ("▼", "#FF4500")

            segments.extend([
                ("   |   ", "#555", None),
                (f"{stale_prefix}{icon} {a['symbol']}: {price_str} ", a["color"], f"{asset_id}_price"),
                (f"{arrow} {abs(chg):.2f}%", col, f"{asset_id}_change"),
            ])

        if segments:
            self.scroll_label.set_colored_text(segments[1:], blinking_items)
        else:
            self.scroll_label.set_status_text("No se pudieron cargar datos", "#FF4500")

    def show_error(self, msg):
        logger.error("Error al actualizar: %s", msg)
        self.scroll_label.set_status_text("Sin conexión · sin datos en caché", "#FF4500")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.request_exit()
        else:
            super().keyPressEvent(event)

    def request_exit(self):
        """Cierra de forma explícita; los cierres externos accidentales se ignoran."""
        if self._closing:
            return
        self._quit_requested = True
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.is_dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.save_position()
            event.accept()

    def save_position(self):
        screen = self.screen()
        write_json_atomic(self.state_path, {
            "version": 1,
            "x": self.x(),
            "y": self.y(),
            "screen": screen.name() if screen else "",
        })

    def closeEvent(self, event):
        if not self._quit_requested:
            logger.warning("Solicitud externa de cierre ignorada para mantener el widget activo")
            event.ignore()
            QTimer.singleShot(0, self.show)
            return

        if self._closing:
            event.ignore()
            return

        self._closing = True
        self.save_position()
        self.update_timer.stop()
        self.visibility_timer.stop()
        self.scroll_label.timer.stop()
        self.scroll_label.blink_timer.stop()
        self.hide()
        self._request_worker_stop()
        event.ignore()


def initial_position(app, widget, config, state_path):
    state = read_json(state_path, {})
    try:
        saved_x = int(state["x"])
        saved_y = int(state["y"])
    except (KeyError, TypeError, ValueError):
        saved_x = saved_y = None

    if saved_x is not None:
        target_screen = next(
            (screen for screen in app.screens() if screen.name() == state.get("screen")),
            None,
        )
        if target_screen is None:
            target_screen = app.screenAt(QPoint(saved_x, saved_y))
        if target_screen is not None:
            geometry = target_screen.availableGeometry()
            max_x = max(geometry.left(), geometry.right() - widget.width() + 1)
            max_y = max(geometry.top(), geometry.bottom() - widget.height() + 1)
            x = min(max(saved_x, geometry.left()), max_x)
            y = min(max(saved_y, geometry.top()), max_y)
            return x, y

    screen = app.primaryScreen().availableGeometry()
    position = config["position"]
    margin = 20
    positions = {
        "top-left": (screen.left() + margin, screen.top() + margin),
        "top-center": (screen.left() + (screen.width() - widget.width()) // 2, screen.top() + margin),
        "top-right": (screen.right() - widget.width() - margin, screen.top() + margin),
        "bottom-left": (screen.left() + margin, screen.bottom() - widget.height() - margin),
        "bottom-center": (
            screen.left() + (screen.width() - widget.width()) // 2,
            screen.bottom() - widget.height() - margin,
        ),
        "bottom-right": (
            screen.right() - widget.width() - margin,
            screen.bottom() - widget.height() - margin,
        ),
    }
    return positions[position]


def main():
    if getattr(sys, "frozen", False):
        application_path = Path(sys.executable).parent
    else:
        application_path = Path(__file__).resolve().parent

    paths = app_paths()
    setup_logging(paths["state"])
    setup_crash_logging(paths["state"])
    logger.info(
        "Iniciando %s %s (%s, Qt=%s)",
        APP_NAME,
        VERSION,
        os.environ.get("XDG_SESSION_TYPE", "desconocida"),
        os.environ.get("QT_QPA_PLATFORM", "automático"),
    )
    config = load_config(application_path, paths["config"] / "config.json")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("yhas1984")
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName(APP_SLUG)
    icon_path = application_path / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.aboutToQuit.connect(lambda: logger.info("Aplicación finalizada"))

    state_path = paths["state"] / "window.json"
    w = CryptoWidget(config, paths["cache"] / "prices.json", state_path)
    x, y = initial_position(app, w, config, state_path)
    w.move(x, y)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
