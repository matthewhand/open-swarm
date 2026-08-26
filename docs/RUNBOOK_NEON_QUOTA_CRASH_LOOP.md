# Runbook: Open Swarm Crash-Loop on Neon Postgres Quota Exceeded

## Incident Summary

**Host**: teamstinky  
**Service**: `open-swarm-oracle.service` (systemd user unit)  
**Symptoms**: Service crash-looping with ~37,500 restarts  
**Root Cause**: Neon Postgres compute quota exceeded  
**Impact**: Service unavailable, high CPU/IO from restart churn  

## Root Cause Analysis

### What Happened

The `open-swarm-oracle.service` systemd unit on teamstinky was configured with:

- **ExecStart**: `manage.py runserver 127.0.0.1:8001` (or `uvicorn swarm.asgi:application`)
- **DATABASE_URL**: Pointed to a Neon Postgres instance
- **Restart policy**: `Restart=always` with `RestartSec=3`

The Neon Postgres instance exceeded its compute quota (free tier limit). When Django attempted to connect on startup, psycopg2 raised an `OperationalError` with messages like:

- "compute time quota exceeded"
- "Your compute endpoint exceeded its quota"
- Connection timeout/refusal after quota exhaustion

### Why It Crash-Looped

1. **Django startup failure**: The ASGI/WSGI application imports Django settings, which triggers database connection pool initialization
2. **psycopg2 connection attempt**: Django tries to connect to the Neon database specified in `DATABASE_URL`
3. **Neon rejects with quota error**: The database returns an error indicating quota exhaustion
4. **Immediate process exit**: Django initialization fails, process exits with code 1
5. **systemd restart**: With `Restart=always`, systemd immediately restarts the service after `RestartSec=3` seconds
6. **Repeat**: Steps 1-5 repeat indefinitely, accumulating ~37,500 restarts

### Why Existing Code Did Not Prevent This

- **No pre-startup health check**: Django's database connection is lazy by default, but ASGI app initialization (`get_asgi_application()`) triggers connection pool setup
- **No fail-fast on quota errors**: psycopg2 `OperationalError` is caught by Django's connection handling, but the exception propagates and crashes the process
- **No distinction between transient and permanent failures**: systemd's `Restart=always` does not differentiate between recoverable errors (network blip) and permanent configuration errors (quota exhausted)

### Why This Is Not a Live Paid Proxy Issue

The user confirmed this is **not a live paid proxy**, meaning:
- The Neon database was likely on the free tier with compute quota limits
- There is no customer-facing impact from upgrading or resuming paid compute
- The correct fix is to use a local database (SQLite or Docker Postgres) instead

## Immediate Remediation

### Step 1: Stop the Crash-Loop

Run as the user owning the service (check with `systemctl --user status open-swarm-oracle.service`):

```bash
systemctl --user stop open-swarm-oracle.service
systemctl --user disable open-swarm-oracle.service
```

This prevents the service from restarting and consuming system resources.

### Step 2: Verify Port 8001 is Free

Confirm the service has stopped and port 8001 is released:

```bash
ss -tlnp | grep 8001
# Should return empty or show no open-swarm process
```

Note: Port 8765 is confirmed to be `mcp-openapi-proxy`, not open-swarm.

### Step 3: Choose a Database Backend

**Option A: Use SQLite (simplest, zero-config)**

Edit `~/.config/systemd/user/open-swarm-oracle.service`:

1. **Remove** the `Environment=DATABASE_URL=...` line (if present)
2. **Add** (or ensure it exists):
   ```
   Environment=DJANGO_DB_NAME=/home/YOUR_USER/.local/share/swarm/db.sqlite3
   ```

**Option B: Use Local Docker Postgres**

1. Copy the provided `docker-compose.postgres.yml` to your open-swarm directory:
   ```bash
   cd ~/open-swarm
   docker compose -f docker-compose.postgres.yml up -d postgres
   ```

2. Edit `~/.config/systemd/user/open-swarm-oracle.service`:
   ```
   Environment=DATABASE_URL=postgresql://swarm:swarm_dev_password@localhost:5432/swarm
   ```

**Option C: Keep Neon (if you upgrade to paid tier)**

Only do this if you intentionally want to use Neon and have upgraded your plan to remove compute limits. Otherwise, prefer Option A or B.

**In all options**, also add this to the `[Service]` section of
`~/.config/systemd/user/open-swarm-oracle.service` (already present in the
repo template `deploy/oracle/open-swarm-oracle.service`):

```
RestartPreventExitStatus=78
```

Without it, `Restart=always` restarts the service on every exit code —
including the health check's fail-fast exit 78 — and the crash-loop continues.
With it, an exit 78 stops the service until you fix the configuration.

### Step 4: Apply Changes and Restart

```bash
systemctl --user daemon-reload
systemctl --user enable open-swarm-oracle.service
systemctl --user start open-swarm-oracle.service

# Verify startup
systemctl --user status open-swarm-oracle.service
journalctl --user -u open-swarm-oracle.service -f
```

If using a new database (SQLite or local Postgres), run migrations:

```bash
cd ~/open-swarm
source .venv/bin/activate
cd src
python manage.py migrate
```

### Step 5: Verify Service is Healthy

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/v1/models
# Should return 200
```

## Long-Term Fix (Included in This PR)

This PR introduces a **pre-startup database health check** that prevents crash-looping:

### New Behavior

1. **Health check runs before Django starts**: The check happens in `swarm.utils.db_health.enforce_database_health_on_startup()`
2. **Detects quota-exceeded errors**: Looks for Neon-specific error indicators like "quota", "compute time", "suspended"
3. **Fails fast with clear error**: Exits with code 78 (EX_CONFIG) and prints actionable remediation steps
4. **Prevents systemd restart churn — only together with `RestartPreventExitStatus=78`**: The exit code alone does NOT stop the loop. `Restart=always` restarts the service on *every* exit code, including 78. The unit file must set `RestartPreventExitStatus=78` (now included in `deploy/oracle/open-swarm-oracle.service`) so systemd leaves the service stopped after a config-error exit instead of restarting it

### Files Changed

- **`src/swarm/utils/db_health.py`**: New module with health check logic
- **`src/swarm/asgi.py`**: Calls health check before `get_asgi_application()`
- **`src/manage.py`**: Calls health check for server commands (runserver, daphne, etc.)
- **`deploy/oracle/open-swarm-oracle.service`**: Adds `RestartPreventExitStatus=78` so systemd does not restart the service after a fail-fast exit 78 (required — `Restart=always` restarts on all exit codes otherwise)
- **`docker-compose.postgres.yml`**: New compose file for local Postgres setup

### Environment Variables

- **`SKIP_DB_HEALTH_CHECK=true`**: Bypass health check (for testing or emergency situations)

### Example Health Check Failure Output

```
[ERROR] Database health check failed: DATABASE_URL points to a quota-exceeded Neon Postgres instance

IMMEDIATE ACTION REQUIRED:
1. Stop this service to prevent crash-looping:
   systemctl --user stop open-swarm-oracle.service
   systemctl --user disable open-swarm-oracle.service

2. Either:
   a) Remove DATABASE_URL from the service environment to use local SQLite, OR
   b) Point DATABASE_URL to a non-quota-stopped Postgres instance, OR
   c) If this was a paid proxy, upgrade your Neon plan

3. Update service file: /home/YOUR_USER/.config/systemd/user/open-swarm-oracle.service
4. Reload and restart: systemctl --user daemon-reload && systemctl --user start open-swarm-oracle.service

For local development, see docker-compose.postgres.yml for a local Postgres setup.

=== EXITING TO PREVENT CRASH-LOOP ===
```

## Testing the Fix

### Local Test: Simulate Quota Exceeded

```bash
# Point DATABASE_URL to a non-existent or firewalled host to simulate connection failure
export DATABASE_URL="postgresql://user:pass@10.255.255.1:5432/db"
cd ~/open-swarm/src
python manage.py runserver
# Should fail fast with helpful error message, not crash-loop
```

### Integration Test: Local Postgres

```bash
cd ~/open-swarm
docker compose -f docker-compose.postgres.yml up -d
# Verify both postgres and swarm services start healthy
docker compose -f docker-compose.postgres.yml ps
curl http://localhost:8000/v1/models
```

## Monitoring and Alerting

### Systemd Unit Status

Monitor restart count to detect crash-loops early:

```bash
systemctl --user show open-swarm-oracle.service -p NRestarts
```

Set up an alert if `NRestarts` exceeds a threshold (e.g., >10 in 5 minutes).

### Service Logs

Watch for database health check failures:

```bash
journalctl --user -u open-swarm-oracle.service | grep "DATABASE HEALTH CHECK FAILED"
```

## Related Documentation

- **Neon Postgres compute limits**: https://neon.tech/docs/introduction/plans#compute-time
- **systemd Restart behavior**: `man systemd.service` (see `Restart=`, `RestartSec=`, and `RestartPreventExitStatus=`)
- **Django database configuration**: https://docs.djangoproject.com/en/4.2/ref/settings/#databases
- **dj-database-url**: https://github.com/jazzband/dj-database-url

## Contact

For questions about this runbook or the fix, contact the open-swarm maintainers or refer to:
- **Oracle deployment docs**: `docs/ORACLE_DEPLOY.md`
- **GitHub Issues**: https://github.com/matthewhand/open-swarm/issues
