# WidgetFinanzas

Widget de escritorio para escritorio Linux que muestra cotizaciones en tiempo real de criptomonedas, índices bursátiles, commodities y forex en una barra scrolleable transparente.

![screenshot](icon.png)

## Características

- **Visualización tipo ticker** — precios se desplazan horizontalmente con scroll infinito
- **Soporte multi-activo** — criptos (BTC, ETH, HBAR), índices (S&P500), commodities (oro, petróleo), forex (EUR/USD)
- **Actualización automática** — intervalo configurable (por defecto 60 segundos)
- **Código de colores** — cambios de precio con colores y flechas según magnitud
- **Efecto de parpadeo** — cuando un activo tiene un cambio significativo (>1%)
- **Transparente y siempre al fondo** — se integra al escritorio sin molestar
- **Auto-inicio** — se configura automáticamente en el arranque de sesión (Linux)
- **Tecla ESC** — cerrar la aplicación

## Requisitos

- Python 3.8+
- PyQt5
- yfinance
- Un entorno de escritorio Linux (probado en GNOME, KDE)

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/yhas1984/WidgetFinanzas.git
cd WidgetFinanzas

# Crear y activar entorno virtual (opcional pero recomendado)
python -m venv myenv
source myenv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
python crypto_widget.py
```

El widget aparecerá en la parte superior de la pantalla, centrado horizontalmente.

## Configuración

Editar `config.json`:

```json
{
  "currency": "usd",
  "update_interval_seconds": 60,
  "run_on_startup": true,
  "assets": [
    {
      "id": "bitcoin",
      "symbol": "BTC",
      "color": "#F7931A",
      "type": "crypto",
      "yf_symbol": "BTC-USD"
    }
  ]
}
```

| Campo | Descripción |
|-------|-------------|
| `currency` | Moneda de cotización |
| `update_interval_seconds` | Intervalo de actualización en segundos |
| `run_on_startup` | Auto-inicio al iniciar sesión |
| `assets` | Lista de activos a mostrar |
| `assets[].id` | Identificador único |
| `assets[].symbol` | Símbolo mostrado en pantalla |
| `assets[].color` | Color hex del texto |
| `assets[].yf_symbol` | Símbolo de Yahoo Finance |

### Activos compatibles

Cualquier símbolo de [Yahoo Finance](https://finance.yahoo.com/lookup):
- Criptos: `BTC-USD`, `ETH-USD`, `HBAR-USD`
- Índices: `^GSPC` (S&P500), `^IXIC` (NASDAQ), `^DJI` (Dow Jones)
- Commodities: `GC=F` (oro), `CL=F` (petróleo)
- Forex: `EURUSD=X`, `USDEUR=X`
- Acciones: `AAPL`, `TSLA`, `MSFT`

## Compilar ejecutable (opcional)

```bash
pip install pyinstaller
pyinstaller CryptoWidget.spec
```

El ejecutable se generará en `dist/CryptoWidget/`.

## Estructura del proyecto

```
WidgetFinanzas/
├── crypto_widget.py      # Aplicación principal
├── config.json           # Configuración de activos
├── requirements.txt      # Dependencias Python
├── CryptoWidget.spec     # PyInstaller spec
├── icon.png              # Icono de la aplicación
└── .gitignore
```

## Licencia

MIT
