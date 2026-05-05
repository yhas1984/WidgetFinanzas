import os
import sys
import json
import yfinance as yf
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QIcon

# ---------------- Worker de datos ----------------
class DataWorker(QObject):
    data_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, assets, currency):
        super().__init__()
        self.assets = assets
        self.currency = currency

    def _fetch_yfinance_data(self, symbols_list):
        """Obtiene datos de múltiples símbolos usando yfinance"""
        try:
            # Crear string con todos los símbolos
            symbols_str = " ".join(symbols_list)
            
            # Obtener datos de los últimos 5 días para calcular cambio
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            # Descargar datos
            data = yf.download(
                symbols_str,
                start=start_date,
                end=end_date,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                prepost=True,
                threads=True,
                proxy=None
            )
            
            results = []
            
            for symbol in symbols_list:
                try:
                    # Si solo hay un símbolo, la estructura es diferente
                    if len(symbols_list) == 1:
                        symbol_data = data
                    else:
                        symbol_data = data[symbol] if symbol in data.columns.get_level_values(0) else None
                    
                    if symbol_data is None or symbol_data.empty:
                        print(f"No hay datos para {symbol}")
                        continue
                    
                    # Obtener el precio actual (último close disponible)
                    closes = symbol_data['Close'].dropna()
                    if len(closes) == 0:
                        continue
                        
                    current_price = float(closes.iloc[-1])
                    
                    # Calcular cambio porcentual (comparar con el día anterior disponible)
                    change_pct = 0.0
                    if len(closes) >= 2:
                        previous_price = float(closes.iloc[-2])
                        if previous_price > 0:
                            change_pct = ((current_price - previous_price) / previous_price) * 100
                    
                    results.append({
                        "symbol": symbol,
                        "current_price": current_price,
                        "price_change_percentage_24h": change_pct
                    })
                    
                except Exception as e:
                    print(f"Error procesando {symbol}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Error en yfinance: {e}")
            return []

    def _get_ticker_info(self, symbol):
        """Obtiene información adicional de un ticker específico"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Intentar obtener precio actual de diferentes fuentes
            current_price = (
                info.get('regularMarketPrice') or 
                info.get('currentPrice') or 
                info.get('previousClose') or 0.0
            )
            
            # Intentar obtener cambio porcentual
            change_pct = (
                info.get('regularMarketChangePercent') or
                info.get('changePercent') or 0.0
            )
            
            return {
                "symbol": symbol,
                "current_price": float(current_price),
                "price_change_percentage_24h": float(change_pct)
            }
            
        except Exception as e:
            print(f"Error obteniendo info de {symbol}: {e}")
            return None

    def run(self):
        try:
            result = {"prices": []}
            
            # Recopilar todos los símbolos
            all_symbols = []
            symbol_to_asset = {}  # Mapeo símbolo -> configuración del asset
            
            for asset in self.assets:
                symbol = asset["yf_symbol"]
                all_symbols.append(symbol)
                symbol_to_asset[symbol] = asset
            
            if not all_symbols:
                self.data_updated.emit(result)
                return
            
            # Obtener datos usando el método batch (más eficiente)
            yf_data = self._fetch_yfinance_data(all_symbols)
            
            # Si el método batch falla, intentar uno por uno
            if not yf_data:
                print("Método batch falló, intentando uno por uno...")
                for symbol in all_symbols:
                    ticker_data = self._get_ticker_info(symbol)
                    if ticker_data:
                        yf_data.append(ticker_data)
            
            # Procesar resultados y aplicar configuraciones
            for data_item in yf_data:
                symbol = data_item["symbol"]
                asset_config = symbol_to_asset.get(symbol)
                
                if not asset_config:
                    continue
                
                price = data_item["current_price"]
                change_pct = data_item["price_change_percentage_24h"]
                
                # Aplicar escala si está configurada
                scale = float(asset_config.get("scale", 1) or 1)
                price *= scale
                
                result["prices"].append({
                    "id": asset_config["id"],
                    "symbol": asset_config["symbol"],
                    "current_price": price,
                    "price_change_percentage_24h": change_pct
                })
            
            self.data_updated.emit(result)

        except Exception as e:
            self.error_occurred.emit(f"Error: {e}")

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
        if self.total_width < self.width():
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
        start_x = self.text_offset if self.total_width >= self.width() else (self.width() - self.total_width) // 2
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
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None
        self.thread = None
        self.previous_prices = {}  # Para detectar cambios
        self.init_ui()
        self.load_styles()
        self.trigger_update()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.trigger_update)
        self.update_timer.start(self.config["update_interval_seconds"] * 1000)

    def check_autostart(self):
        """Configura el escritorio y el inicio automático en Linux"""
        try:
            
            # Solo para Linux
            if sys.platform != "linux":
                return

            # Directorios
            autostart_dir = os.path.expanduser("~/.config/autostart")
            applications_dir = os.path.expanduser("~/.local/share/applications")
            
            for d in [autostart_dir, applications_dir]:
                if not os.path.exists(d):
                    os.makedirs(d)

            # Determinar rutas
            if getattr(sys, 'frozen', False):
                exec_cmd = f'"{sys.executable}"'
                app_dir = os.path.dirname(sys.executable)
            else:
                exec_cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

            # Buscar el icono en múltiples ubicaciones
            possible_icons = [
                os.path.join(app_dir, "icon.png"),
                os.path.abspath("icon.png"),
                os.path.join(os.path.dirname(app_dir), "icon.png") # Un nivel arriba de dist
            ]
            
            icon_path = ""
            for p in possible_icons:
                if os.path.exists(p):
                    icon_path = p
                    break
            
            # Contenido base del archivo .desktop
            desktop_img_line = f"Icon={icon_path}\n" if icon_path else ""
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Crypto Widget
Comment=Widget de criptomonedas y acciones
Exec={exec_cmd}
Path={app_dir}
{desktop_img_line}Terminal=false
Hidden=false
NoDisplay=false
"""
            
            # 1. Escribir en ~/.local/share/applications (Para el menú)
            app_desktop_path = os.path.join(applications_dir, "crypto_widget.desktop")
            with open(app_desktop_path, "w") as f:
                f.write(desktop_content)

            # 2. Escribir en ~/.config/autostart (Para inicio automático)
            autostart_content = desktop_content + "X-GNOME-Autostart-enabled=true\n"
            auto_desktop_path = os.path.join(autostart_dir, "crypto_widget.desktop")
            with open(auto_desktop_path, "w") as f:
                f.write(autostart_content)
                
            print(f"Configuración de escritorio actualizada. Icono: {icon_path}")

        except Exception as e:
            print(f"Error configurando escritorio: {e}")

    def init_ui(self):
        self.setWindowTitle("Ticker")
        # Integrado al escritorio: transparente, fijo y al fondo
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set Application Icon
        icon_path = "icon.png"
        if getattr(sys, 'frozen', False):
             icon_path = os.path.join(os.path.dirname(sys.executable), "icon.png")
        elif os.path.exists(os.path.join(os.path.dirname(__file__), "icon.png")):
             icon_path = os.path.join(os.path.dirname(__file__), "icon.png")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setFixedSize(1000, 50)

        main = QWidget(self)
        main.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(main)

        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_label = ScrollingLabel()
        self.scroll_label.setObjectName("scroll_label")
        layout.addWidget(self.scroll_label)
        
        # Configurar autostart
        self.check_autostart()

    def load_styles(self):
        self.setStyleSheet("""
            QLabel { background-color: transparent; border: none; }
            #scroll_label { font-size: 14pt; font-weight: bold; background-color: transparent; }
        """)

    def trigger_update(self):
        if self.thread and self.thread.isRunning():
            return  # Evitar múltiples threads simultáneos
            
        self.worker = DataWorker(
            self.config["assets"],
            self.config["currency"]
        )
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.data_updated.connect(self.update_ui)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.data_updated.connect(self.thread.quit)
        self.worker.error_occurred.connect(self.thread.quit)
        self.thread.start()

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
            if asset_id in self.previous_prices:
                old_price = self.previous_prices[asset_id]
                if abs(price - old_price) / old_price > 0.01:  # Cambio >1%
                    blinking_items.append(f"{asset_id}_price")
                    blinking_items.append(f"{asset_id}_change")
            
            self.previous_prices[asset_id] = price

            # Obtener icono
            icon = self.scroll_label.get_icon(a["symbol"])

            # Formato de precio mejorado
            if price >= 1000:
                price_str = f"${price:,.0f}"
            elif price >= 1:
                price_str = f"${price:,.2f}"
            else:
                price_str = f"${price:.4f}"
            
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
                (f"{icon} {a['symbol']}: {price_str} ", a["color"], f"{asset_id}_price"),
                (f"{arrow} {abs(chg):.2f}%", col, f"{asset_id}_change"),
            ])

        if segments:
            self.scroll_label.set_colored_text(segments[1:], blinking_items)
        else:
            self.scroll_label.set_status_text("No se pudieron cargar datos", "#FF4500")

    def show_error(self, msg):
        print(msg)
        self.scroll_label.set_status_text("Error al cargar datos", "#FF4500")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


def main():
    try:
        # Buscar config.json en el mismo directorio que el ejecutable/script
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            
        config_path = os.path.join(application_path, "config.json")
        
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error con 'config.json': {e}")
        # Configuración por defecto si falla
        config = {
            "currency": "usd",
            "update_interval_seconds": 60,
            "run_on_startup": False,
            "assets": []
        }

    app = QApplication(sys.argv)
    w = CryptoWidget(config)
    screen = app.primaryScreen().availableGeometry()
    w.move((screen.width() - w.width()) // 2, 30)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()