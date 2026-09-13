# WidgetFinanzas

Widget de escritorio para Linux que muestra cotizaciones en tiempo real de criptomonedas, índices bursátiles, commodities y forex en una barra scrolleable transparente.

![screenshot](icon.png)

## Características

- **Visualización tipo ticker** — precios se desplazan horizontalmente con scroll infinito
- **Soporte multi-activo** — criptos, índices, commodities, forex, acciones
- **Actualización automática** — intervalo configurable con retry y backoff exponencial
- **Caché local** — si la API falla, muestra los últimos datos conocidos con indicador ⚠️
- **Código de colores** — cambios de precio con colores y flechas según magnitud
- **Efecto de parpadeo** — cuando un activo tiene un cambio significativo (>1%)
- **Transparente y siempre al fondo** — se integra al escritorio sin molestar
- **Posición configurable** — top-left, top-center, top-right, bottom-left, bottom-center, bottom-right
- **Menú contextual / tray icon** — click derecho para actualizar, pausar scroll o salir
- **Auto-inicio** — se configura automáticamente en el arranque de sesión (Linux)
- **Logging estructurado** — trazas con timestamps y niveles (DEBUG/INFO/ERROR)
- **Validación de config** — detecta errores en `config.json` antes de arrancar
- **Tests unitarios** — cobertura de formato, colores y validación

## Requisitos

- Python 3.10+
- PyQt5
- yfinance (con pandas, numpy, requests, lxml)
- Entorno de escritorio Linux

## Instalación

```bash
# Clonar
git clone https://github.com/yhas1984/WidgetFinanzas.git
cd WidgetFinanzas

# Entorno virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
python crypto_widget.py
```

O desde el paquete:

```bash
python -m src.main
```

## Configuración

Editar `config.json`:

```json
{
  "currency": "usd",
  "update_interval_seconds": 60,
  "run_on_startup": true,
  "position": "top-center",
  "window_width": 1000,
  "window_height": 50,
  "assets": [
    {
      "id": "bitcoin",
      "symbol": "BTC",
      "color": "#F7931A",
      "type": "crypto",
      "yf_symbol": "BTC-USD"
    }
  ],
  "icons": {
    "BTC": "₿",
    "ETH": "Ξ"
  }
}
```

| Campo | Descripción |
|-------|-------------|
| `currency` | Moneda de cotización |
| `update_interval_seconds` | Intervalo de actualización |
| `run_on_startup` | Auto-inicio en Linux |
| `position` | `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right` |
| `window_width` | Ancho del widget (px) |
| `window_height` | Alto del widget (px) |
| `assets` | Lista de activos |
| `icons` | Diccionario de iconos por símbolo |

### Activos compatibles

Cualquier símbolo de [Yahoo Finance](https://finance.yahoo.com/lookup).

## Tests

```bash
pytest tests/ -v
```

## Compilar ejecutable

```bash
pip install pyinstaller
pyinstaller CryptoWidget.spec
```

## Estructura del proyecto

```
WidgetFinanzas/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Carga y validación de config
│   ├── constants.py         # Constantes centralizadas
│   ├── data_fetcher.py      # Worker de Yahoo Finance
│   ├── autostart.py         # Lógica .desktop
│   ├── utils.py             # Helpers y logging
│   └── ui/
│       ├── widgets.py       # ScrollingLabel
│       ├── main_window.py   # CryptoWidget
│       └── tray_menu.py     # Menú contextual
├── tests/
│   ├── test_config.py
│   └── test_formatting.py
├── crypto_widget.py         # Wrapper
├── config.json
├── requirements.txt
├── CryptoWidget.spec
└── icon.png
```

## Instalación desde `.deb`

Los paquetes compilados se publican como assets en la sección [Releases](https://github.com/yhas1984/WidgetFinanzas/releases). Descarga `widget-finanzas_*_amd64.deb` y ejecuta:

```bash
sudo apt install ./widget-finanzas_*_amd64.deb
```

## Compilar el `.deb`

```bash
python -m pip install -r requirements.txt
bash packaging/build-deb.sh 5.0.2
```

Al crear un tag `v5.0.2`, GitHub Actions compila el paquete y lo publica automáticamente como asset del release.

## Licencia

MIT
