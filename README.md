# 🐋 Polymarket Whale Bot

Bot automatizado para **copy trading** en Polymarket siguiendo a las ballenas más exitosas.

## 🎯 Estrategia: Whale Watching

**Copia trades de los 12 mejores traders de Polymarket**

- ✅ **12 ballenas verificadas** con P&L positivo comprobado
- ✅ Seguimiento en tiempo real de sus trades
- ✅ Position sizing inteligente (10-20% del trade de la ballena)
- ✅ Filtros de riesgo multi-nivel
- ✅ Paper Trading para validación

**Rentabilidad esperada**: 15-30% mensual (basada en historial de ballenas)

**Estado actual**: Fase 1 completada ✅ - Listo para Fase 2 (copy trading logic)

[📖 Ver documentación completa →](WHALE_WATCHING_README.md)

---

## 📋 Requisitos

- Python 3.9+
- Cuenta en Polymarket (solo necesaria para Fase 2 - copy trading)
- USDC en Polygon (solo para trading real, no para monitoreo)

---

## 🚀 Quick Start

### 1. Clonar e instalar

```bash
git clone https://github.com/alebeta06/polymarket-whale-bot.git
cd polymarket-whale-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Ejecutar el monitor

```bash
export PYTHONPATH=.
python scripts/whale_watcher.py
```

El bot:

- ✅ Monitorea 12 ballenas con P&L positivo verificado
- ✅ Poll cada 60 segundos (configurable)
- ✅ Guarda estadísticas en database SQLite (`data/whales.db`)
- ✅ No requiere API keys (solo monitoreo)

### 3. Ver estadísticas

```bash
python scripts/view_whales.py
```

---

## 📁 Estructura del Proyecto

```
polymarket-whale-bot/
├── src/
│   ├── whale_watching/      # 🐋 Módulo principal
│   │   ├── database.py      #   - SQLite database manager
│   │   ├── individual_monitor.py  #   - Monitor de ballenas
│   │   ├── seed_whales.py   #   - 12 ballenas verificadas
│   │   ├── models.py        #   - Modelos Pydantic
│   │   └── data_api.py      #   - Cliente Data API
│   ├── config.py            # Configuración general
│   └── utils/               # Utilidades
├── scripts/
│   ├── whale_watcher.py     # 🎯 Script principal
│   ├── view_whales.py       # Ver estadísticas
│   └── scrape_leaderboard.py  # Scraper (one-time use)
├── data/
│   └── whales.db            # Database SQLite
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🐋 Las 12 Ballenas Monitoreadas

### 🏆 Consistentes (Top Mes + Semana):

```
1. 0x006cc834cc092684f1b56626e23bedb3835c16ea
2. 0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee
3. 0xe90bec87d9ef430f27f9dcfe72c34b76967d5da2
4. 0xdb27bf2ac5d428a9c63dbc914611036855a6c56e
5. 0x1bc0d88ca86b9049cf05d642e634836d5ddf4429
6. 0xdc876e6873772d38716fda7f2452a78d426d7ab6
7. 0xcd9bc2939f0dac121f6ccde59cca5e0b6a91414d
```

### 📈 Top Mensuales:

```
8. 0x16b29c50f2439faf627209b2ac0c7bbddaa8a881
9. 0x37e4728b3c4607fb2b3b205386bb1d1fb1a8c991
10. 0x507e52ef684ca2dd91f90a9d26d149dd3288beae
```

### ⚡ Top Semanales:

```
11. 0x96489abcb9f583d6835c8ef95ffc923d05a86825
12. 0x92672c80d36dcd08172aa1e51dface0f20b70f9a
```

**Todas verificadas con P&L positivo** - No hay perdedores en la lista.

---

## 📊 Roadmap

### ✅ Fase 1: Monitoreo (Completada)

- [x] Identificar 12 ballenas rentables
- [x] Database SQLite con SQLAlchemy
- [x] Monitor individual con polling
- [x] Scripts de ejecución

### 🔄 Fase 2: Copy Trading (En Progreso)

- [ ] Implementar detección de trades en tiempo real
- [ ] Filtros de riesgo avanzados
- [ ] Cálculo de position sizing
- [ ] Paper Trading mode
- [ ] Integración con CLOB API

### 🎯 Fase 3: Producción

- [ ] Testing en Paper Trading (1-2 semanas)
- [ ] Validar win rate >60%
- [ ] Deploy con capital limitado ($500-1000)
- [ ] Telegram notifications

---

## 🔧 Configuración (Fase 2)

Solo necesario cuando implementemos copy trading:

```bash
cp .env.example .env
nano .env
```

Variables requeridas:

```bash
POLYMARKET_API_KEY=tu_api_key
POLYMARKET_API_SECRET=tu_api_secret
POLYMARKET_API_PASSPHRASE=tu_passphrase
PRIVATE_KEY=0xtu_private_key
DRY_RUN=true  # Siempre empezar en Paper Trading
```

---

## 📚 Documentación

- [WHALE_WATCHING_README.md](WHALE_WATCHING_README.md) - Guía completa de uso
- [Walkthrough](whale_watching_walkthrough.md) - Proceso de implementación
- [Polymarket Docs](https://docs.polymarket.com) - Documentación oficial

---

## 🔐 Seguridad

- ⚠️ **NUNCA** compartas tu `PRIVATE_KEY`
- ⚠️ **NUNCA** subas `.env` a GitHub
- ⚠️ Usa `.gitignore` (ya incluido)
- 💡 Empieza siempre en Paper Trading (`DRY_RUN=true`)

---

## ⚖️ Legal & Disclaimer

**USO BAJO TU PROPIO RIESGO**

Este bot es para fines educativos y de investigación. El copy trading conlleva riesgos:

- Pérdida de capital
- Las ballenas también pierden trades
- Cambios de mercado imprevistos
- Bugs en el código

**NO** somos responsables por pérdidas financieras.

---

## 📧 Soporte

Para preguntas o issues, crea un issue en GitHub o consulta la documentación.

---

**Desarrollado con ❤️ para copiar a los mejores traders de Polymarket** 🐋
