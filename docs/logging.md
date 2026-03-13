# Padrao de Logging

## Objetivo
Padronizar logs com contexto tecnico sem poluir o loop de render.

## Configuracao
- Modulo: `infra/logging_config.py`
- Nivel via env: `BITDEV_LOG_LEVEL` (default `INFO`)
- Formato: `timestamp level module message`

## Uso
```python
from infra.logging_config import get_logger
logger = get_logger(__name__)

logger.info("op=boot status=started")
logger.warning("op=fetch_btc_only status=failed reason=%s", err)
logger.exception("op=main_loop status=recoverable_error reason=%s", err)
```

## Convencao de Mensagem
- `op=<operacao>`
- `status=<estado>`
- Campos extras quando util (`reason`, `code`, `path`)

## Diretriz de Ruido
- Loop critico de render: logar apenas falhas recuperaveis/criticas.
- Fluxo nominal recorrente: evitar logs por frame.