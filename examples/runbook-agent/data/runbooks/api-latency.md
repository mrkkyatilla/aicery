# API Latency Runbook

## 1. Doğrulama
- Grafana dashboard: checkout-api p95
- Son deploy zamanı

## 2. Olası nedenler
- DB connection pool exhaustion
- Downstream payment timeout
- Cache miss spike

## 3. Önerilen adımlar (onaylı)
- Scale deployment +2 (oncall lead onayı)
- Rollback son deploy (change freeze dışında)

## Yasak
- Production DB şema değişikliği bu runbook kapsamında değil.
