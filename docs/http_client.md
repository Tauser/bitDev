# HTTP Client Padrao

## Objetivo
Centralizar chamadas HTTP com timeout, retry, backoff e headers padronizados.

## Modulo
`infra/http_client.py`

## Uso
```python
from infra.http_client import get_http_client

http_client = get_http_client()
r = http_client.get("https://api.exemplo.com/recurso", timeout=3)
if r.status_code == 200:
    data = r.json()
```

## Padrao aplicado
- Timeout default: `3s`
- Retry default: `2` tentativas adicionais
- Backoff default: `0.25s` exponencial (`0.25`, `0.5`, ...)
- Retry para `429` e `5xx` (GET/HEAD)
- Retry para `Timeout` e `ConnectionError`
- Header padrao `User-Agent: CryptoMonitor/1.0 (+local-rpi)`

## Observacao
Cada chamada pode sobrescrever `timeout`, `retries` e `backoff` via argumento.