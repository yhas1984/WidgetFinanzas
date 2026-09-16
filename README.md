# WidgetFinanzas

Widget de escritorio para Linux que muestra cotizaciones periódicas de criptomonedas, índices bursátiles, commodities y forex en una barra scrolleable transparente.

![Icono de Widget Finanzas](icon.png)

## Características

- **Visualización tipo ticker** — precios se desplazan horizontalmente con scroll infinito
- **Soporte multi-activo** — criptos, índices, commodities, forex, acciones
- **Actualización automática** — intervalo configurable, timeout y reintento limitado
- **Caché local** — si la API falla, muestra los últimos datos conocidos con indicador ⚠️
- **Código de colores** — cambios de precio con colores y flechas según magnitud
- **Efecto de parpadeo** — cuando un activo tiene un cambio significativo (>1%)
- **Transparente y siempre al fondo** — se integra al escritorio sin molestar
- **Posición persistente** — recuerda la posición exacta y el monitor después de arrastrarlo
- **Auto-inicio opcional** — desactivado por defecto y configurable en Linux
- **Logging estructurado** — trazas con timestamps y niveles (DEBUG/INFO/ERROR)
- **Validación de config** — detecta errores en `config.json` antes de arrancar
- **Tests unitarios** — cobertura de configuración, caché, formato, persistencia y regresiones
- **X11 y Wayland** — Qt elige la plataforma disponible sin forzar XWayland

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

## Configuración

Los valores incluidos están en `config.json`. En una instalación `.deb`, crea una configuración personal en `~/.config/widget-finanzas/config.json`; sus valores tienen prioridad y no se sobrescriben al actualizar el paquete.

```json
{
  "currency": "usd",
  "update_interval_seconds": 60,
  "run_on_startup": false,
  "desktop_mode": true,
  "position": "top-center",
  "window_width": 1000,
  "window_height": 50,
  "assets": [
    {
      "id": "bitcoin",
      "symbol": "BTC",
      "color": "#F7931A",
      "type": "crypto",
      "quote_currency": "usd",
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
| `desktop_mode` | Intenta mantener el ticker integrado al escritorio cuando el compositor lo permite |
| `position` | `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right` |
| `window_width` | Ancho del widget (px) |
| `window_height` | Alto del widget (px) |
| `assets` | Lista de activos |
| `icons` | Diccionario de iconos por símbolo |

La posición se guarda en `~/.local/state/widget-finanzas/window.json`, la caché en `~/.cache/widget-finanzas/prices.json` y el log en `~/.local/state/widget-finanzas/widget-finanzas.log`. Se respetan las variables XDG equivalentes.

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
├── crypto_widget.py         # Punto de entrada estable
├── crypto_widgetV5.py       # Datos, persistencia e interfaz
├── tests/                   # Pruebas automatizadas
├── config.json
├── requirements.txt
├── requirements-dev.txt
├── CryptoWidget.spec
├── packaging/build-deb.sh
└── icon.png
```

## Instalación desde `.deb`

Los paquetes compilados se publican como assets en la sección [Releases](https://github.com/yhas1984/WidgetFinanzas/releases). Descarga `widget-finanzas_*_amd64.deb` y ejecuta:

```bash
sudo apt install ./widget-finanzas_*_amd64.deb
```

### Desinstalación

```bash
sudo apt remove widget-finanzas
```

El paquete elimina el lanzador, el icono y las entradas de autoinicio administradas por versiones anteriores. La configuración, la caché y el estado personal se conservan para permitir una reinstalación posterior.

## Compilar el `.deb`

```bash
python -m pip install -r requirements.txt
bash packaging/build-deb.sh 5.0.3
```

Al crear un tag `v5.0.3`, GitHub Actions ejecuta las pruebas, compila el paquete y lo publica automáticamente como asset del release.

## Licencia

MIT
