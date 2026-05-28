# WidgetFinanzas

Widget de escritorio para Linux que muestra cotizaciones en tiempo real de criptomonedas, índices bursátiles, commodities y forex en una barra scrolleable transparente integrada al escritorio.

![WidgetFinanzas](icon.png)

## Características

| Feature | Descripción |
|---------|-------------|
| **Ticker animado** | Precios con scroll infinito horizontal |
| **Multi-activo** | Criptos, índices, commodities, forex y acciones |
| **Colores dinámicos** | Verde (subida), rojo (bajada), flechas según magnitud |
| **Parpadeo** | Alerta visual en cambios >1% |
| **Arrastrable** | Mover el widget con el ratón a cualquier posición |
| **Dock nativo** | Se integra al gestor de ventanas como dock |
| **Transparente** | Fondo translúcido, siempre al fondo |
| **Auto-inicio** | Se ejecuta automáticamente al iniciar sesión |
| **Configurable** | Editar `config.json` para personalizar activos |

## Requisitos

- Python 3.8+
- PyQt5
- yfinance
- Linux (GNOME, KDE o similar)

## Instalación rápida

```bash
git clone https://github.com/yhas1984/WidgetFinanzas.git
cd WidgetFinanzas
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python crypto_widget.py
```

## Configuración

Edita `config.json` para agregar o quitar activos:

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

### Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `currency` | string | Moneda de cotización (usd, eur, etc.) |
| `update_interval_seconds` | int | Segundos entre actualizaciones |
| `run_on_startup` | bool | Auto-inicio al iniciar sesión |
| `assets` | array | Lista de activos a mostrar |
| `assets[].id` | string | Identificador único del activo |
| `assets[].symbol` | string | Texto mostrado en el ticker |
| `assets[].color` | string | Color hex del texto |
| `assets[].yf_symbol` | string | Símbolo de Yahoo Finance |

### Activos de ejemplo

| Tipo | Símbolo | Yahoo Finance |
|------|---------|---------------|
| Crypto | BTC | `BTC-USD` |
| Crypto | ETH | `ETH-USD` |
| Crypto | HBAR | `HBAR-USD` |
| Índice | S&P500 | `^GSPC` |
| Índice | NASDAQ | `^IXIC` |
| Commodity | Oro | `GC=F` |
| Commodity | Petróleo | `CL=F` |
| Forex | EUR/USD | `EURUSD=X` |
| Acción | Apple | `AAPL` |
| Acción | Tesla | `TSLA` |

Cualquier símbolo de [Yahoo Finance](https://finance.yahoo.com/lookup) es compatible.

## Compilar ejecutable

```bash
pip install pyinstaller
pyinstaller CryptoWidget.spec
```

El ejecutable se generará en `dist/CryptoWidget/`.

## Estructura

```
WidgetFinanzas/
├── crypto_widget.py      # Aplicación principal
├── config.json           # Configuración de activos
├── requirements.txt      # Dependencias
├── CryptoWidget.spec     # Spec de PyInstaller
├── icon.png              # Icono
└── .gitignore
```

## Atajos de teclado

| Tecla | Acción |
|-------|--------|
| `ESC` | Cerrar widget |
| `Arrastrar` | Mover widget |

## Solución de problemas

**El widget no aparece:**
```bash
# Verificar que XCB esté instalado
sudo apt install libxcb-xinerama0
```

**Error de yfinance:**
```bash
pip install --upgrade yfinance
```

## Licencia

MIT
