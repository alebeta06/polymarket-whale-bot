# 🤖 Polymarket Arbitrage Bot

Bot automatizado para detectar y ejecutar oportunidades de arbitraje en mercados de predicción de Polymarket.

## 🎯 Características

- **Detección de Arbitraje Intra-Mercado**: Identifica cuando YES + NO ≠ 1
- **Detección de Arbitraje Inter-Mercado**: Encuentra inconsistencias entre mercados relacionados
- **Paper Trading**: Modo simulación sin riesgo
- **WebSocket Real-Time**: Actualizaciones de precios en tiempo real (<1s latency)
- **Order Batching**: Ejecuta hasta 5 trades simultáneos
- **Risk Management**: Circuit breakers y límites de exposición
- **Proxy Wallet Support**: Compatible con sistema de proxy wallets de Polymarket

## 📋 Requisitos

- Python 3.9+
- Cuenta en Polymarket con API Keys
- Wallet Phantom con Polygon configurado
- USDC en Polygon para trading (mínimo recomendado: $500)

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
cd /home/alebeta/polymarket-arbitrage-bot
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
nano .env  # Editar con tus credenciales
```

**⚠️ IMPORTANTE**: Nunca compartas tu archivo `.env` ni lo subas a GitHub.

### 5. Variables críticas a configurar:

```bash
# API Keys de Polymarket (desde Builder Settings)
POLYMARKET_API_KEY=tu_api_key
POLYMARKET_API_SECRET=tu_api_secret
POLYMARKET_API_PASSPHRASE=tu_passphrase

# Private Key de Phantom (MANTENER SEGURA)
PRIVATE_KEY=0xtu_private_key

# Direcciones
EOA_ADDRESS=0xtu_direccion_phantom_polygon
PROXY_WALLET_ADDRESS=0xtu_direccion_polymarket

# Modo de operación
DRY_RUN=true  # true = Paper Trading, false = Real trading
```

## 📊 Uso

### Modo Paper Trading (Recomendado para empezar)

```bash
python src/main.py
```

El bot:

- ✅ Detecta oportunidades reales
- ✅ Calcula ganancias proyectadas
- ✅ Registra todo en logs
- ❌ NO ejecuta trades reales

### Modo Producción

1. Verificar que Paper Trading funciona correctamente (1-2 semanas)
2. Cambiar en `.env`: `DRY_RUN=false`
3. Ejecutar:

```bash
python src/main.py
```

## 📁 Estructura del Proyecto

```
polymarket-arbitrage-bot/
├── src/
│   ├── scanner/          # Escaneo de mercados (Gamma API)
│   ├── arbitrage/        # Detección de oportunidades
│   ├── execution/        # Ejecución de trades (CLOB API)
│   ├── risk/             # Gestión de riesgos
│   ├── monitoring/       # Logging y métricas
│   ├── utils/            # Utilidades generales
│   └── main.py           # Punto de entrada principal
├── tests/                # Tests unitarios
├── logs/                 # Archivos de log
├── data/                 # Datos y caché
├── requirements.txt      # Dependencias Python
├── .env.example          # Template de configuración
└── README.md             # Este archivo
```

## 🔐 Seguridad

### ⚠️ CRÍTICO - Protege tus credenciales:

1. **NUNCA** compartas tu `PRIVATE_KEY`
2. **NUNCA** subas `.env` a GitHub
3. **NUNCA** pegues credenciales en chats públicos
4. Usa `.gitignore` (ya incluido)
5. Considera usar hardware wallet para producción

### Proxy Wallets:

Polymarket usa smart contract wallets (proxy) para cada usuario:

- Tu EOA (Phantom): Firma transacciones
- Proxy Wallet: Ejecuta trades
- Ambas controladas por tu private key
- Las direcciones son diferentes (esto es **normal**)

## 📈 Configuración de Riesgo

En `.env`, ajusta estos parámetros:

```bash
# Máximo % del balance por trade
MAX_POSITION_SIZE_PERCENT=0.15  # 15%

# Stop-loss diario (detiene bot si se alcanza)
DAILY_STOP_LOSS_PERCENT=0.10    # 10%

# Ganancia mínima para ejecutar
MIN_PROFIT_PERCENT=0.02         # 2%
```

## 📊 Monitoreo

### Ver logs en tiempo real:

```bash
tail -f logs/polymarket_bot.log
```

### Reportes diarios:

Los reportes se guardan en `data/daily_reports/`

## 🐛 Troubleshooting

### Error: "Invalid API credentials"

- Verifica que copiaste correctamente las 3 credenciales de Polymarket
- Revisa que no haya espacios extras en `.env`

### Error: "Insufficient balance"

- Verifica que tienes USDC en tu proxy wallet de Polymarket
- Deposita desde Phantom si es necesario

### Error: "Rate limit exceeded"

- El bot tiene throttling automático
- Si persiste, reduce `MARKET_REFRESH_INTERVAL` en `.env`

### Direcciones no coinciden:

- ✅ Esto es normal - Polymarket usa proxy wallets
- Lee `proxy_wallet_solution.md` en la documentación

## 📚 Documentación Adicional

- [Polymarket Official Docs](https://docs.polymarket.com)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
- [Polygon Network](https://polygon.technology)

## ⚖️ Legal & Disclaimer

**USO BAJO TU PROPIO RIESGO**

Este bot es para fines educativos y de investigación. El trading de arbitraje conlleva riesgos:

- Pérdida de capital
- Slippage
- Cambios de mercado
- Bugs en el código

**NO** somos responsables por pérdidas financieras.

## 📝 Logs & Reportes

El bot genera:

- `logs/polymarket_bot.log` - Log general
- `data/trades.csv` - Historial de trades
- `data/opportunities.json` - Oportunidades detectadas
- `data/daily_reports/` - Reportes diarios de P&L

## 🚀 Roadmap

- [x] Scanner de mercados (Gamma API)
- [x] Detector de arbitraje intra-mercado
- [ ] Detector de arbitraje inter-mercado
- [x] Risk management básico
- [ ] WebSocket integration
- [ ] Order batching
- [ ] Telegram notifications
- [ ] Dashboard web (opcional)

## 📧 Soporte

Para preguntas o issues, consulta la documentación en `/docs/` o crea un issue en GitHub.

---

**Desarrollado con ❤️ para la comunidad de Polymarket**
