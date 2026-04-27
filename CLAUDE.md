# CLAUDE.md

Guía de contexto para Claude Code al trabajar en este repositorio.

---

## 1. Qué hace el proyecto

`polymarket-whale-bot` es un bot de **copy trading** para [Polymarket](https://polymarket.com) (mercados de predicción sobre Polygon). La estrategia es replicar las operaciones de las 12 ballenas con P&L positivo verificado, escalando el tamaño de cada copia al 10–20 % del tamaño original.

Estado real del código (no del README):

- **Fase 1 (monitoreo)**: estructura lista, pero el fetch real de trades está **stubbed** — el monitor no hace llamadas reales a la API todavía (ver §6).
- **Fase 2 (copy trading)**: no iniciada.
- **Fase 3 (producción / Telegram / capital real)**: no iniciada.

El proyecto reemplazó una iteración previa de arbitraje intra-/inter-market (esos modelos viven como código muerto en `src/utils/models.py` — ver §5).

---

## 2. Stack técnico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.9+ |
| Persistencia | SQLite via SQLAlchemy 2.0 (ORM) |
| Async / red | `asyncio`, `aiohttp`, `websockets` |
| Config | `pydantic` 2.x + `pydantic-settings` (lee `.env`) |
| Logging | `loguru` (rotación + handler de errores separado) |
| Scraping | `requests` + `beautifulsoup4` |
| Polymarket | `py-clob-client` (importado en `individual_monitor.py` pero **comentado** en `requirements.txt` — ver §6) |
| Tests | `pytest` + `pytest-asyncio` (no hay tests escritos aún) |

Dependencias futuras de Fase 2 (comentadas en `requirements.txt`): `py-clob-client>=0.25.0`, `web3>=6.0.0`, `eth-account>=0.9.0`.

---

## 3. Estructura de carpetas

```
polymarket-whale-bot/
├── src/
│   ├── config.py                       # Pydantic Settings (requiere .env)
│   ├── utils/
│   │   ├── logger.py                   # setup loguru, depende de get_settings()
│   │   └── models.py                   # CÓDIGO MUERTO de la versión arbitrage
│   └── whale_watching/                 # Módulo principal
│       ├── database.py                 # SQLAlchemy: ObservedTrader, ObservedTrade, WhaleDatabase
│       ├── seed_whales.py              # Lista hardcodeada de 12 ballenas
│       ├── models.py                   # Pydantic: WhaleStats, WhaleTrade, LeaderboardUser
│       ├── data_api.py                 # Cliente async de https://data-api.polymarket.com (NO conectado al monitor)
│       ├── individual_monitor.py       # Polling por whale (fetch stubbed)
│       └── trade_monitor.py            # Legacy WebSocket — descartado, sigue en repo
├── scripts/
│   ├── whale_watcher.py                # Entry point principal
│   ├── view_whales.py                  # CLI de stats (TIENE BUG, ver §6)
│   └── scrape_leaderboard.py           # One-shot — extrajo las 12 direcciones iniciales
├── data/                               # NO existe en repo (gitignored). Lo crea SQLite al primer run.
├── logs/                               # NO existe en repo (gitignored). Lo crea loguru.
├── requirements.txt
├── setup.sh                            # Crea venv, instala deps, copia .env.example
├── .env.example                        # Plantilla — la mayor parte de las vars son para Fase 2
├── README.md                           # Visión de producto (puede sobrevender el estado actual)
└── WHALE_WATCHING_README.md            # Notas técnicas, explica por qué se abandonó el WS
```

---

## 4. Comandos importantes

**Setup inicial**

```bash
./setup.sh                              # crea venv, instala requirements, copia .env
# o manualmente:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Ejecutar el monitor** (requiere `PYTHONPATH=.` por los imports absolutos `src.*`)

```bash
export PYTHONPATH=.
python scripts/whale_watcher.py
```

**Ver estado de la DB**

```bash
python scripts/view_whales.py           # OJO: tiene bug, ver §6
```

**Re-scrapear leaderboard** (raro — la lista actual fue curada manualmente)

```bash
python scripts/scrape_leaderboard.py
```

**Tests**: aún no hay test suite. Cuando se agregue, usar `pytest` (`pytest-asyncio` ya está en deps).

---

## 5. Convenciones del código

- **Imports absolutos desde `src.*`** (no relativos desde scripts). Por eso es obligatorio `export PYTHONPATH=.` antes de correr cualquier script.
- **Logging**: usar `from loguru import logger as log` directamente en módulos de `whale_watching/`. `src/utils/logger.py` agrega handlers de archivo/rotación pero **depende de `get_settings()`**, lo cual exige `.env` — los scripts actuales lo evitan importando `loguru` directo.
- **Async**: el monitor y el data-api son `async`; usar `asyncio.run()` desde scripts. Polling con `await asyncio.sleep(1)` entre whales para rate-limit suave.
- **DB**: una sola sesión global por instancia de `WhaleDatabase`; commits explícitos tras cada mutación. Direcciones siempre en lowercase antes de persistir.
- **Direcciones EVM**: siempre con prefijo `0x`, longitud 42, validadas en `config.py` (Pydantic validator).
- **Modelos duales**: SQLAlchemy en `database.py` (persistencia), Pydantic en `models.py` (DTOs/IO). No mezclar.
- **Idioma**: README/docs en español; comentarios y docstrings en inglés.
- **Emojis**: el código fuente y logs los usan profusamente (🐋 ✅ ⚠️ etc.). Mantener el estilo si se editan los logs existentes; no introducirlos en código nuevo a menos que el usuario lo pida.
- **No hay linter/formatter configurado** (ni `ruff`, ni `black`, ni `mypy`). Si se añade, decidir con el usuario primero.

---

## 6. Estado real por archivo y bugs conocidos

Antes de tocar código de Fase 2, tener presente lo que NO funciona hoy:

### 6.1 `individual_monitor.py` — fetch de trades es un stub
Líneas 62–87: `check_whale_trades` no llama a ninguna API. El bloque "real" está como comentario:

```python
# trades = await self.client.get_user_trades(address, since=last_check)
# for trade in trades:
#     self.process_trade(address, trade)
```

Solo actualiza `last_trade_timestamps[address]` y loguea. Esto significa que **el bot actualmente no detecta trades** — gira en vacío.

### 6.2 `py_clob_client` no está instalado
`individual_monitor.py:13-14` importa `py_clob_client`, pero en `requirements.txt:30-33` la dependencia está **comentada**. `pip install -r requirements.txt` no la trae, y `python scripts/whale_watcher.py` revienta con `ModuleNotFoundError` en cuanto se importa el monitor.

Para hacerlo arrancar: descomentar `py-clob-client>=0.25.0` en `requirements.txt` y `pip install` de nuevo.

### 6.3 `view_whales.py:15` está roto
Línea malformada (query anidada con `bind.execute` sobre una sesión, no compila lógicamente):

```python
all_traders = db.session.query(db.session.query(db.session.bind.execute("SELECT COUNT(*) FROM observed_traders").scalar())).scalar()
```

Reemplazar por algo como `db.session.query(ObservedTrader).count()`.

### 6.4 `trade_monitor.py` — código legacy
Estrategia WebSocket descartada (ver `WHALE_WATCHING_README.md`). Sigue en el repo como referencia. No invocar; al revisar Fase 2 considerar borrarlo si ya no aporta.

### 6.5 `data_api.py` — implementado pero huérfano
El cliente HTTP de `data-api.polymarket.com` ya está completo (`get_leaderboard`, `get_user_portfolio`, `get_user_trades`, `get_user_stats`). **Ningún módulo lo importa todavía**. Es la pieza natural a conectar en Fase 2 (ver §7).

### 6.6 `src/utils/models.py` — código muerto
Modelos de la era arbitrage (`Market`, `ArbitrageOpportunity`, `TradeOrder`, etc.) que `whale_watching/` no usa. `src/utils/__init__.py` los re-exporta. Candidato a borrar al cerrar Fase 2.

### 6.7 `src/config.py` exige `.env` con credenciales reales
Validators de Pydantic exigen `private_key` (66 chars, prefijo `0x`), `eoa_address`, `proxy_wallet_address`, etc. Si algún módulo importa `src.config` sin `.env`, falla al construir `Settings()`. Hoy el monitor evita esto importando `loguru` directo, pero cualquier feature de Fase 2 que use `get_settings()` necesitará `.env` válido o relajar los validators (mejor: marcar opcionales los campos solo-Fase-2).

### 6.8 Doc fantasma
`README.md:174` linkea a `whale_watching_walkthrough.md` que no existe en el repo.

---

## 7. Qué falta implementar — Fase 2 (copy trading)

Backlog ordenado por dependencia:

1. **Habilitar `py-clob-client`**: descomentar en `requirements.txt`, reinstalar, verificar import.
2. **Conectar `PolymarketDataAPI` al monitor**: en `individual_monitor.py:62-87`, reemplazar el stub por una llamada a `data_api.get_user_trades(address, limit=N)` filtrada por `last_trade_timestamps[address]`. Persistir cada trade nuevo con `db.record_trade(...)`.
3. **Detección de trades nuevos**: hoy `last_trade_timestamps` se inicializa a `now - 24h` por whale en memoria. Persistirlo en DB (nueva columna en `ObservedTrader` o tabla `monitor_state`) para sobrevivir reinicios y evitar reprocesar.
4. **Position sizing**: módulo nuevo (sugerido `src/whale_watching/sizing.py`) que calcule el tamaño de la copia como `whale_size * MAX_POSITION_SIZE_PERCENT` (`.env` ya tiene la var, default 0.15) con tope por balance.
5. **Filtros de riesgo**:
   - Min/max trade size de la ballena.
   - Liquidez mínima del market (`MIN_MARKET_VOLUME` ya en config).
   - Time-to-expiry mínimo del market.
   - Edad máxima del trade de la ballena (no copiar trades viejos).
   - Stop-loss diario (`DAILY_STOP_LOSS_PERCENT`).
6. **Paper Trading mode**: respetar `DRY_RUN=true`. Crear tabla `paper_trades` (o reutilizar `ObservedTrade` con flag) que registre la copia simulada con fill price del momento, sin tocar CLOB.
7. **Ejecución real (cuando `DRY_RUN=false`)**: integrar `ClobClient` autenticado (API key + secret + passphrase + private key — todas ya en `.env.example`). Order types: LIMIT por defecto, batch máximo 5 (`ORDER_BATCH_SIZE`).
8. **Métricas y P&L**: cerrar el loop comparando paper trades vs precio actual / settled outcome. Necesario para validar el "win rate >60 %" pedido en Fase 3.
9. **Reparar `view_whales.py`** (§6.3) y borrar `trade_monitor.py` legacy + `src/utils/models.py` muerto si ya no aportan.
10. **Tests**: al menos cubrir `WhaleDatabase` (CRUD), `PolymarketDataAPI` (con `aiohttp` mockeado) y la lógica de sizing/filtros.

---

## 8. Qué falta — Fase 3 (producción)

- Correr el bot en Paper Trading 1–2 semanas y medir win rate, ROI, drawdown.
- Validar P&L de las 12 ballenas sigue vigente (re-scrapear leaderboard, refrescar `seed_whales.py`).
- Telegram notifications (vars `ENABLE_TELEGRAM`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` ya en `.env.example` pero sin código).
- Rotación/curaduría automática de la lista de ballenas (entrada/salida según P&L observado).
- Hardening: manejo de reconexión, backoff exponencial, circuit breakers ante errores de API, persistencia de `last_trade_timestamps`.
- Deploy: Dockerfile + systemd/PM2 + monitoring (Prometheus/Grafana o similar).
- Capital limitado inicial ($500–1000) con `DRY_RUN=false` y stops conservadores.

---

## 9. Notas operativas para futuras sesiones

- **No commitear `data/whales.db`, `logs/`, ni `.env`** (ya en `.gitignore`).
- **Nunca loguear ni imprimir** `PRIVATE_KEY` o secretos derivados.
- Antes de modificar el esquema de `ObservedTrader` / `ObservedTrade`, asumir que existen DBs locales del usuario en `data/whales.db` con datos — escribir una migración manual o instrucciones de re-seed.
- El proyecto está en español de cara al usuario; documentación nueva debería seguir esa convención salvo indicación contraria.
