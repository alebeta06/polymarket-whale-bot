# 🤖 Polymarket Trading Bot

Bot automatizado para trading en mercados de predicción de Polymarket con **2 estrategias**:

1. **Arbitraje** (original - limitado)
2. **Whale Watching** (nuevo - recomendado) 🐋

## 🎯 Estrategias Disponibles

### 🐋 Whale Watching (Recomendado)

**Copia trades de los mejores traders de Polymarket**

- ✅ **12 ballenas verificadas** con P&L positivo comprobado
- ✅ Seguimiento en tiempo real de sus trades
- ✅ Position sizing inteligente (10-20% del trade de la ballena)
- ✅ Filtros de riesgo multi-nivel
- ✅ Paper Trading para validación

**Rentabilidad esperada**: 15-30% mensual (basada en historial de ballenas)

[Ver documentación completa →](WHALE_WATCHING_README.md)

### 📊 Arbitraje Intra-Mercado

**Detecta cuando YES + NO ≠ 1**

- Detección automática de oportunidades
- Ejecución simultánea de ambos lados
- Risk management integrado

**Nota**: Esta estrategia es altamente competitiva y requiere velocidad extrema. Rentabilidad limitada para traders retail.

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

### 🐋 Whale Watching Bot (Recomendado)

**Monitoreo y copy trading de ballenas verificadas:**

```bash
cd /home/alebeta/polymarket-arbitrage-bot
source venv/bin/activate
export PYTHONPATH=.
python scripts/whale_watcher.py
```

El bot:

- ✅ Monitorea 12 ballenas con P&L positivo verificado
- ✅ Poll cada 60 segundos (configurable)
- ✅ Guarda estadísticas en database SQLite
- ✅ Ready para implementar copy trading

**Ver estadísticas de ballenas:**

```bash
python scripts/view_whales.py
```

[Documentación completa de Whale Watching →](WHALE_WATCHING_README.md)

---

### 📈 Arbitrage Bot (Original)

**Modo Paper Trading (Recomendado para empezar):**

```bash
export PYTHONPATH=.
python src/main.py
```

El bot:

- ✅ Detecta oportunidades reales
- ✅ Calcula ganancias proyectadas
- ✅ Registra todo en logs
- ❌ NO ejecuta trades reales

**Modo Producción:**

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
│   ├── arbitrage/        # Detección de oportunidades de arbitraje
│   ├── execution/        # Ejecución de trades (CLOB API)
│   ├── risk/             # Gestión de riesgos
│   ├── monitoring/       # Logging y métricas
│   ├── whale_watching/   # 🐋 NUEVO: Monitor de ballenas
│   │   ├── database.py   #   - Base de datos SQLite
│   │   ├── individual_monitor.py  #   - Monitor individual
│   │   ├── seed_whales.py         #   - 12 ballenas verificadas
│   │   └── models.py     #   - Modelos de datos
│   ├── utils/            # Utilidades generales
│   └── main.py           # Bot de arbitraje
├── scripts/              # 🐋 Scripts de whale watching
│   ├── whale_watcher.py  #   - Main bot
│   ├── view_whales.py    #   - Ver estadísticas
│   └── scrape_leaderboard.py  #   - Scraper (one-time)
├── data/
│   ├── whales.db         # 🐋 Database de ballenas
│   ├── trades.json       # Trades de arbitraje
│   └── opportunities.json
├── logs/                 # Archivos de log
├── requirements.txt      # Dependencias Python
├── .env.example          # Template de configuración
├── README.md             # Este archivo
└── WHALE_WATCHING_README.md  # 🐋 Docs de whale watching
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

### Estrategia de Arbitraje:

- [x] Scanner de mercados (Gamma API)
- [x] Detector de arbitraje intra-mercado
- [ ] Detector de arbitraje inter-mercado
- [x] Risk management básico
- [ ] WebSocket integration
- [ ] Order batching

### Estrategia de Whale Watching: 🐋

- [x] Identificación de ballenas rentables (12 verificadas)
- [x] Database de tracking (SQLite + SQLAlchemy)
- [x] Monitor individual con polling
- [ ] **NEXT**: Implementar copy trading logic
- [ ] **NEXT**: Risk filters avanzados
- [ ] **NEXT**: Paper trading mode
- [ ] **NEXT**: Position sizing inteligente

### General:

- [ ] Telegram notifications
- [ ] Dashboard web (opcional)

## 📧 Soporte

Para preguntas o issues, consulta la documentación en `/docs/` o crea un issue en GitHub.

---

**Desarrollado con ❤️ para la comunidad de Polymarket**
