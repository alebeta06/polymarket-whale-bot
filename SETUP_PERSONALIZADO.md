# 🔐 Configuración de Credenciales - Guía Personalizada

## 📋 Tu Información

Basándome en tus datos confirmados:

| Credencial        | Valor                                        | Estado        |
| ----------------- | -------------------------------------------- | ------------- |
| **API Key**       | `019bb5dc-210a-7d56-ba8c-916be4ed9916`       | ✅ Confirmada |
| **API Secret**    | `[guardada localmente]`                      | ✅ Lista      |
| **Passphrase**    | `[guardada localmente]`                      | ✅ Lista      |
| **Dirección EOA** | `0xcF430a8Fa09A3a2b1CE9Dbd4403102a43e5e8e06` | ✅ Confirmada |
| **Proxy Wallet**  | `0x84c916bb5314515bffa04dd9c714bfa348b98ab8` | ✅ Confirmada |
| **Private Key**   | `[extraída de Phantom]`                      | ✅ Lista      |

---

## ⚡ Pasos Rápidos de Configuración

### 1. Navega al Proyecto

```bash
cd /home/alebeta/polymarket-arbitrage-bot
```

### 2. Ejecuta Setup Automatizado

```bash
./setup.sh
```

Esto creará:

- ✅ Virtual environment en `venv/`
- ✅ Instalará todas las dependencias
- ✅ Copiará `.env.example` a `.env`

### 3. Edita el Archivo .env

```bash
nano .env
```

### 4. Reemplaza EXACTAMENTE estos valores:

```bash
# ========================================
# POLYMARKET API CREDENTIALS
# ========================================
POLYMARKET_API_KEY=019bb5dc-210a-7d56-ba8c-916be4ed9916
POLYMARKET_API_SECRET=tu_api_secret_aqui
POLYMARKET_API_PASSPHRASE=tu_passphrase_aqui

# ========================================
# WALLET CONFIGURATION
# ========================================
PRIVATE_KEY=0xTU_PRIVATE_KEY_DE_PHANTOM_AQUI
EOA_ADDRESS=0xcF430a8Fa09A3a2b1CE9Dbd4403102a43e5e8e06
PROXY_WALLET_ADDRESS=0x84c916bb5314515bffa04dd9c714bfa348b98ab8

# ========================================
# BOT CONFIGURATION
# ========================================
DRY_RUN=true  # ⚠️ MANTENER true para Paper Trading
MAX_POSITION_SIZE_PERCENT=0.15  # 15% según tus preferencias
DAILY_STOP_LOSS_PERCENT=0.10    # 10% según tus preferencias
MIN_PROFIT_PERCENT=0.02         # 2% según tus preferencias
```

**⚠️ IMPORTANTE**:

- NO compartas estas credenciales con nadie
- El archivo `.env` está en `.gitignore` (no se subirá a GitHub)
- Guarda un backup de estas credenciales en un lugar seguro

### 5. Guarda el Archivo

- `Ctrl + O` (guardar)
- `Enter` (confirmar)
- `Ctrl + X` (salir)

---

## 🚀 Ejecutar el Bot

### Activar Virtual Environment

```bash
source venv/bin/activate
```

Verás `(venv)` al inicio de tu prompt.

### Ejecutar el Bot

```bash
python src/main.py
```

### Deberías Ver:

```
======================================== ========
🤖 POLYMARKET ARBITRAGE BOT STARTING
============================================================
Mode: 📝 PAPER TRADING (Simulation)
Max Position Size: 15.0%
Daily Stop-Loss: 10.0%
Min Profit: 2.0%
Categories: ['Politics', 'Crypto', 'Sports']
============================================================
2026-01-13 17:30:00 | INFO     | Fetching active markets from Gamma API...
2026-01-13 17:30:02 | INFO     | Fetched 45 markets, 23 above $10000 volume
2026-01-13 17:30:02 | INFO     | Detected 3 arbitrage opportunities across 23 markets
```

---

## 📊 Monitoreo

### En Otra Terminal:

```bash
# Logs en tiempo real
tail -f /home/alebeta/polymarket-arbitrage-bot/logs/polymarket_bot.log

# Oportunidades detectadas
cat /home/alebeta/polymarket-arbitrage-bot/data/opportunities.json | jq .

# Métricas diarias
cat /home/alebeta/polymarket-arbitrage-bot/data/daily_metrics.json | jq '.[-1]'
```

---

## 🛑 Detener el Bot

Presiona `Ctrl + C` en la terminal donde está corriendo el bot.

Verás un reporte final:

```
⚠️  Received signal 2, initiating shutdown...
🛑 Shutting down bot...

📊 Final Daily Statistics:
  Date: 2026-01-13
  P&L: $0.00
  Trades: 0 (0 successful)
  Opportunities Detected: 5

✅ Bot shutdown complete
```

---

## ✅ Checklist Pre-Ejecución

Antes de ejecutar, verifica:

- [ ] Ejecutaste `./setup.sh`
- [ ] El archivo `.env` existe
- [ ] Reemplazaste `POLYMARKET_API_KEY` con `019bb5dc-210a-7d56-ba8c-916be4ed9916`
- [ ] Reemplazaste `POLYMARKET_API_SECRET` con el valor que guardaste
- [ ] Reemplazaste `POLYMARKET_API_PASSPHRASE` con el valor que guardaste
- [ ] Reemplazaste `PRIVATE_KEY` con tu private key de Phantom (empieza con `0x`)
- [ ] Verificaste `EOA_ADDRESS` = `0xcF430a8Fa09A3a2b1CE9Dbd4403102a43e5e8e06`
- [ ] Verificaste `PROXY_WALLET_ADDRESS` = `0x84c916bb5314515bffa04dd9c714bfa348b98ab8`
- [ ] `DRY_RUN=true` está configurado ✅

---

## 🐛 Troubleshooting

### Error: "Failed to load configuration"

```bash
# Verifica que .env existe
ls -la ~/.env

# Si no existe, créalo
cp .env.example .env
nano .env
```

### Error: "Invalid API credentials"

```bash
# Verifica que copiaste las credenciales correctamente
# Sin espacios extras, sin comillas
grep "POLYMARKET_API_KEY" .env
```

### Error: "Invalid private key"

```bash
# La private key debe:
# - Empezar con 0x
# - Tener 66 caracteres totales (0x + 64 caracteres hex)
grep "PRIVATE_KEY" .env | wc -c  # Debe ser 67 (66 + newline)
```

### Bot no encuentra markets

```bash
# Verifica conectividad a Polymarket API
curl https://gamma-api.polymarket.com/markets | jq '.'
```

---

## 📞 Siguientes Pasos

Una vez que el bot esté corriendo:

1. **Déjalo correr durante 1-2 semanas** en Paper Trading
2. **Revisa logs diarios** para ver oportunidades detectadas
3. **Analiza métricas** en `data/daily_metrics.json`
4. **Decide** si vale la pena:
   - Añadir más capital ($500+)
   - Cambiar a modo producción (`DRY_RUN=false`)
   - Desplegar en VPS para 24/7

---

## 🎯 Configuración Actual (Tus Preferencias)

Basándome en lo que elegiste:

| Parámetro                     | Valor      | Significado                              |
| ----------------------------- | ---------- | ---------------------------------------- |
| **MAX_POSITION_SIZE_PERCENT** | 0.15 (15%) | Con $15.61, máximo $2.34 por trade       |
| **DAILY_STOP_LOSS_PERCENT**   | 0.10 (10%) | Bot se detiene si pierde $1.56 en un día |
| **MIN_PROFIT_PERCENT**        | 0.02 (2%)  | Solo ejecuta si ganancia neta ≥ 2%       |
| **DRY_RUN**                   | true       | Paper Trading (simulación)               |

Estas preferencias son **más agresivas que el promedio** (15% por trade es alto), perfecto para maximizar ganancia proyectada en Paper Trading.

---

¡Todo listo! 🚀
