# Deploy 24/7 + handoff para próxima sesión

> Para correr el bot continuamente sin depender de tu laptop. Léelo con tiempo,
> elegí una opción, y volvé acá con el setup hecho para retomar el paper trading.

---

## TL;DR — qué te recomiendo

| Opción | Costo / mes | Esfuerzo setup | Cuándo elegirla |
|---|---|---|---|
| **Hetzner CX22** (cloud VPS) | **~$5 USD** (€4.59) | 30 min | Default razonable. Buena relación precio/perf, soporte serio. |
| **Oracle Cloud "Always Free"** | **$0** | 60-90 min | Si querés gastar cero y no te molesta pelear con la consola de Oracle. |
| **Raspberry Pi 4/5 en casa** | $0 (one-time ~$75) | 60 min | Si tenés internet hogareño estable y no querés depender de la nube. |

Mi pick: **Hetzner CX22** por simplicidad. $5/mes vale lo que ahorrás en tiempo de configuración y dolores de cabeza.

---

## Opciones detalladas

### A) Cloud VPS (recomendado)

El bot consume ~120 MB de RAM y casi nada de CPU/disco/red. Cualquier VPS chico alcanza.

| Provider | Plan | RAM | CPU | Precio/mes | Notas |
|---|---|---|---|---|---|
| **Hetzner Cloud** | CX22 | 4 GB | 2 vCPU | €4.59 (~$5) | EU/US. Excelente UI. **Recomendado.** |
| DigitalOcean | Basic | 1 GB | 1 vCPU | $6 | Más caro, mucha doc en español. |
| Vultr | Regular | 1 GB | 1 vCPU | $6 | Similar a DO. |
| AWS Lightsail | Nano | 1 GB | 2 vCPU | $5 | Si ya estás en AWS. |
| Linode (Akamai) | Nanode | 1 GB | 1 vCPU | $5 | Comparable a Hetzner. |

Todos cobran por hora; podés probar 1 día sin compromiso.

### B) Oracle Cloud "Always Free" — gratis pero más trabajo

Oracle ofrece, sin caducidad, una instancia ARM "Ampere A1" con hasta **4 vCPUs y 24 GB de RAM** gratis para siempre. Es el mejor deal del mercado si lo conseguís.

Caveats:
- Las instancias Always Free a veces no tienen capacidad disponible en regiones populares — hay que reintentar varias veces.
- La consola de Oracle es notoriamente confusa.
- En cualquier momento Oracle puede pedirte tarjeta de crédito (aunque no cobre).
- Si dejás la VM apagada >7 días, te la borran "por inactividad".

Vale la pena si querés cero costo y tenés paciencia.

### C) Raspberry Pi en casa

- **Hardware**: Raspberry Pi 4 (2 GB) o 5 (4 GB) ≈ $35-75 + fuente + microSD ≈ **$75-100 one-time**.
- **Pros**: cero recurrente, control total, "tuyo".
- **Contras**: tu internet hogareño tiene que estar prendido siempre. Si se corta la luz / se reinicia el router, el bot queda colgado hasta que vuelvas.
- **Setup**: idéntico al de un VPS Linux (sección de abajo aplica igual).

---

## Setup paso a paso (Hetzner — extrapolable a cualquier VPS Linux)

### 1) Crear la VM

1. Cuenta en https://www.hetzner.com/cloud (pide tarjeta para verificación, no cobra hasta usar).
2. **+ New Project** → **Add Server**.
3. Region: la más cerca de Polygon RPCs activos (Nuremberg/Falkenstein están bien, o Ashburn US si preferís US).
4. Image: **Ubuntu 24.04 LTS**.
5. Type: **CX22** (Shared vCPU, 4 GB RAM).
6. SSH key: pegá tu clave pública (`cat ~/.ssh/id_rsa.pub` desde tu laptop; si no tenés, generala con `ssh-keygen -t ed25519`).
7. Name: `whale-bot` o lo que quieras.
8. Create. Te queda una IP pública en ~30 segundos.

### 2) Primer login + hardening básico

```bash
ssh root@<TU_IP>

# Crear un usuario no-root para correr el bot
adduser whale
usermod -aG sudo whale
mkdir -p /home/whale/.ssh
cp ~/.ssh/authorized_keys /home/whale/.ssh/
chown -R whale:whale /home/whale/.ssh
chmod 700 /home/whale/.ssh
chmod 600 /home/whale/.ssh/authorized_keys

# Firewall: solo SSH permitido (HTTP/HTTPS no son necesarios — el bot NO recibe conexiones)
ufw allow OpenSSH
ufw enable

# Actualizar paquetes
apt update && apt upgrade -y

# Logout y entrar como whale
exit
ssh whale@<TU_IP>
```

### 3) Instalar dependencias del sistema

```bash
sudo apt install -y python3 python3-venv python3-pip git tmux
python3 --version  # debería ser 3.11+ en Ubuntu 24.04
```

### 4) Clonar el repo + setup

```bash
cd ~
git clone <TU_URL_DEL_REPO> polymarket-whale-bot
cd polymarket-whale-bot

# venv + dependencias
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5) Configurar `.env` con tus credenciales reales

```bash
cp .env.example .env
nano .env  # pegá los mismos valores que tenés en tu laptop
```

**Doble check antes de guardar**: `DRY_RUN=true`. Querés paper trading, no live.

### 6) Smoke test antes de dejarlo corriendo

```bash
# Verificar que arranca y carga las whales
PYTHONPATH=. python -c "
from src.config import get_settings
from src.whale_watching.database import WhaleDatabase
from src.whale_watching.individual_monitor import IndividualWhaleMonitor
print('Settings OK, DRY_RUN=', get_settings().dry_run)
"

# Correr la suite de tests
pytest -q
```

Si todo verde, seguí.

### 7) Convertir el bot en servicio systemd (mejor que tmux)

`tmux` está bien para empezar, pero un servicio `systemd` es lo correcto para 24/7:
- arranca solo al bootear
- se reinicia solo si crashea
- los logs van a journald (rotación automática)
- `systemctl status` te dice si está vivo en 1 comando

Crear el archivo de servicio:

```bash
sudo nano /etc/systemd/system/whale-bot.service
```

Pegar (ajustá la ruta si tu home no es `/home/whale`):

```ini
[Unit]
Description=Polymarket Whale Bot (paper trading)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=whale
WorkingDirectory=/home/whale/polymarket-whale-bot
Environment="PYTHONPATH=/home/whale/polymarket-whale-bot"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/whale/polymarket-whale-bot/venv/bin/python scripts/whale_watcher.py
Restart=always
RestartSec=10
StandardOutput=append:/home/whale/polymarket-whale-bot/logs/bot.log
StandardError=append:/home/whale/polymarket-whale-bot/logs/bot.log

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
mkdir -p logs
sudo systemctl daemon-reload
sudo systemctl enable whale-bot      # arranca al bootear
sudo systemctl start whale-bot       # arranca ahora
sudo systemctl status whale-bot      # verificar que está running
```

### 8) Logs + rotación

Los logs van a `logs/bot.log` y crecen lento (~5 MB/día estimado). Para rotarlos:

```bash
sudo nano /etc/logrotate.d/whale-bot
```

```
/home/whale/polymarket-whale-bot/logs/bot.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

---

## Comandos día-a-día (en la VM)

```bash
# Estado
sudo systemctl status whale-bot

# Logs en vivo
tail -f logs/bot.log

# O via journald (más limpio)
journalctl -u whale-bot -f

# Reporte de stats
source venv/bin/activate && PYTHONPATH=. python scripts/stats.py

# Reiniciar (después de tocar código)
sudo systemctl restart whale-bot

# Apagar
sudo systemctl stop whale-bot

# Ver paper trades crudo
source venv/bin/activate && PYTHONPATH=. python scripts/view_whales.py

# Reconciliación manual (el bot ya la hace cada 10 min)
source venv/bin/activate && PYTHONPATH=. python scripts/reconcile.py
```

### Conectarte desde tu laptop sin abrir SSH expuesto

Si te incomoda tener SSH público:
- Instalar **Tailscale** (gratis hasta 100 devices) en la VM y en tu laptop. Te conectás por la IP privada de Tailscale (`100.x.y.z`), nadie más ve tu SSH. https://tailscale.com/download

---

## Costos esperados (resumen honesto)

| Concepto | Costo |
|---|---|
| Hetzner CX22 | $5/mes |
| Tráfico | $0 (incluye 20 TB; usás <1 GB/mes) |
| Backups | Opcional, +20% del precio (€0.92/mes); innecesario al principio |
| Dominio / DNS | $0 (no necesitás) |
| **Total mensual** | **~$5 USD** |
| Setup time first-time | 30-45 min |

A precios actuales, **$60/año por tener el bot 24/7**. Si la estrategia da +5% mensual sobre $1k de paper, deberías recuperar el costo del VPS en horas (en la simulación). Real depende del executor live.

---

## ⚠️ Cosas que cuidar

1. **NO subas tu `.env` al repo.** Está en `.gitignore` pero verificá: `git status` no debería listarlo.
2. **NO logueés tu `PRIVATE_KEY`.** Ningún log actual lo hace, pero si modificás código, cuidado.
3. **Backup de `data/whales.db`**: una vez que tengas semanas de paper data, conviene `scp` periódico a tu laptop o un cron a S3/Backblaze. Es la única fuente de verdad de tu P&L.
4. **Si la API de Polymarket tira 429** (rate limit): subir `poll_interval` en `scripts/whale_watcher.py` a 90 o 120s.
5. **DRY_RUN=true es tu seguro.** Hasta que no tengas evidencia de win-rate ≥60% sostenido y estés listo para implementar el executor live, NO lo flipees.

---

# 📌 Donde quedamos (handoff)

## Estado al cierre (2026-04-27)

✅ **Bot funciona en paper trading end-to-end.**

Lo que se hizo en esta sesión (paso a paso del plan que recomendé):

1. **Test suite** (48 tests, todos verde): `tests/test_sizing.py`, `test_risk.py`, `test_database.py`, `test_reconcile.py`.
2. **Reconciliación** de paper trades:
   - Cliente nuevo `src/whale_watching/markets.py` (gamma-api de Polymarket).
   - `src/whale_watching/reconcile.py` con lógica pura de mark-to-market y resolución.
   - `scripts/reconcile.py` standalone.
   - **Integrado al loop del bot**: se ejecuta cada 10 polls (~10 min), no requiere proceso separado.
   - Schema actualizado: nuevas columnas `unrealized_pnl_usd`, `asset_id`, `last_reconciled_at` con migración idempotente.
3. **Leaderboard refrescado**: arreglé el endpoint (era `data-api/.../leaderboard` que daba 404; el real es `lb-api.polymarket.com/profit?window=all|30d|1d`).
   - `scripts/scrape_leaderboard.py` reescrito; saca intersección 30d ∩ all-time con PnL > 0.
   - **Aplicado**: `src/whale_watching/seed_whales.py` ahora tiene 11 whales actualizadas a 2026-04-27. (Solo 3 sobrevivieron del seed viejo de enero — confirmado que los seeds se podren rápido.)
4. **Stats script**: `scripts/stats.py` — win-rate, ROI, drawdown, breakdown por whale.

✅ **Smoke test exitoso**: el primer whale del seed nuevo tiene 50+ trades en las últimas 24h, incluido un **$276,298 SPURS** y **$66,329 ROCKETS**. Todos descartados en bootstrap por edad (>10 min); a partir del segundo ciclo solo se procesan trades frescos.

## Lo que NO se hizo (a propósito)

❌ **Executor live (Fase 2.7)** — pendiente intencional. La regla: implementarlo solo después de validar la estrategia con paper trading. Necesitás 1-2 semanas de data + win-rate ≥60% sostenido + mínimo ~30 trades resueltos antes de tomar la decisión.

## Para retomar mañana / próxima sesión

**Si elegiste deploy en VM**:
1. Seguí los pasos 1-8 de arriba.
2. `systemctl status whale-bot` debería decir `active (running)`.
3. Volvé al chat con: "el bot está corriendo en VM, llevamos X horas, mostrá stats" — yo te tiro el `python scripts/stats.py` y revisamos.

**Si querés correr en la laptop por ahora**:
```bash
cd /home/alebeta/Proyectos/polymarket-whale-bot
tmux new -s whalebot -d \
  'source venv/bin/activate && PYTHONPATH=. python scripts/whale_watcher.py 2>&1 | tee -a logs/bot.log'
tmux attach -t whalebot
```
(pero al apagar la laptop el bot se pausa o muere, dependiendo de WSL).

**Tareas pendientes registradas (en mi sistema interno)**:
- Tarea #12: Implementar executor live (Fase 2.7) — bloqueada hasta tener evidencia de paper.

**Para refrescar el seed más adelante**:
```bash
PYTHONPATH=. python scripts/scrape_leaderboard.py --top 12        # solo ver
PYTHONPATH=. python scripts/scrape_leaderboard.py --top 12 --apply  # sobrescribe
```
Recomiendo refrescar 1×/semana mientras el bot está en paper.

## Archivos modificados/creados en esta sesión (lista de revisión)

```
M  .env.example                              ← nuevas vars
M  requirements.txt                          ← descomenté py-clob-client
M  scripts/view_whales.py                    ← fix bug §6.3 + sección paper trades
M  scripts/whale_watcher.py                  ← pasa Settings al monitor
M  scripts/scrape_leaderboard.py             ← REESCRITO con lb-api
M  src/config.py                             ← paper/risk settings
M  src/whale_watching/data_api.py            ← endpoint leaderboard correcto
M  src/whale_watching/database.py            ← PaperTrade + ensure_trader + migraciones
M  src/whale_watching/individual_monitor.py  ← pipeline risk→sizing→paper, reconcile en loop
M  src/whale_watching/seed_whales.py         ← 11 whales frescas (2026-04-27)
+  src/whale_watching/markets.py             ← cliente gamma-api
+  src/whale_watching/reconcile.py           ← lógica de reconciliación
+  src/whale_watching/sizing.py              ← position sizing
+  src/whale_watching/risk.py                ← gates de riesgo
+  scripts/reconcile.py                      ← entry point standalone
+  scripts/stats.py                          ← reporte de paper trading
+  pytest.ini, tests/* (4 archivos)          ← 48 tests
+  CLAUDE.md                                 ← contexto del proyecto
+  DEPLOY.md                                 ← este archivo
```

Nada está commiteado todavía. Si querés guardar el progreso antes de seguir tocando: `git add -A && git commit -m "feat: paper trading pipeline + reconciliation"`.

Suerte y buenas noches. 🐋
