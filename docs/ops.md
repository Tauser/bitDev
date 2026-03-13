# Operacao (Quality Gate + Deploy Seguro)

## Quality Gate local

```bash
bash scripts/quality_gate.sh
```

Valida:
- py_compile dos modulos criticos
- pytest rapido (state/web/health/http_client)
- smoke de health local

## Deploy com rollback automatico

```bash
bash scripts/deploy_safe.sh /home/tauser/bitdev
```

Fluxo:
1. backup dos arquivos alvo em `backups/deploy_<timestamp>`
2. copia incremental dos arquivos
3. restart do `crypto.service`
4. health/readiness check
5. rollback automatico em qualquer falha

## Endpoint de metricas

`GET /api/metrics`

Resumo:
- `runtime`: status do collector/readiness
- `freshness`: staleness por dominio + TTL
- `providers`: tentativas/sucesso/erro/ultima duracao/ultimo erro

Payload pensado para automacao e troubleshooting rapido.
