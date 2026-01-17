## 📚 Appendix: Código Legacy de Arbitraje

### ⚠️ Arbitrage Bot (NO Recomendado)

El código original de arbitraje intra-mercado está en `src/arbitrage/` y `src/main.py`.

**Por qué lo descontinuamos:**

- Rentabilidad <1% mensual en práctica real
- Requiere latencia extremadamente baja (<50ms)
- Competencia con bots institucionales
- Oportunidades desaparecen en <1 segundo
- No viable para traders retail

**Si aún quieres probarlo (solo educacional):**

```bash
# Configurar .env primero
cp .env.example .env
nano .env  # Agregar credenciales

# Ejecutar en modo paper trading
export PYTHONPATH=.
python src/main.py
```

**Resultado esperado**: Verás muchas oportunidades detectadas, pero pocas ejecutables. Esto es normal y es por lo que cambiamos a Whale Watching.

---

### Variables .env para Arbitraje

Solo si decides probar el bot de arbitraje (legacy):

```bash
# API Keys de Polymarket
POLYMARKET_API_KEY=tu_api_key
POLYMARKET_API_SECRET=tu_api_secret
POLYMARKET_API_PASSPHRASE=tu_passphrase

# Private Key de Phantom
PRIVATE_KEY=0xtu_private_key

# Direcciones
EOA_ADDRESS=0xtu_direccion_phantom
PROXY_WALLET_ADDRESS=0xtu_direccion_polymarket

# Modo (SIEMPRE usar true primero)
DRY_RUN=true

# Risk management
MAX_POSITION_SIZE_PERCENT=0.15    # 15% max por trade
DAILY_STOP_LOSS_PERCENT=0.10      # 10% stop-loss diario
MIN_PROFIT_PERCENT=0.02           # 2% mínimo de ganancia
```

⚠️ **Recordatorio**: Esta estrategia fue abandonada. Usa Whale Watching en su lugar.
