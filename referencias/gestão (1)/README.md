# Painel CAPS Refatorado

Estrutura organizada para o dashboard do CAPS com separação entre:

- importação para SQLite
- consultas ao banco
- regras de negócio por aba
- componentes de UI
- tabs do Dash

## Como usar

### 1. Importar a base para o SQLite

```bash
python scripts/importar_base.py
```

### 2. Executar o dashboard

```bash
python app.py
```

## Estrutura

- `core/`: normalização, geografia e referências territoriais do RJ
- `database/`: schema, importação e consultas
- `services/`: filtros e agregações por aba
- `ui/`: componentes, estilos e mapas
- `tabs/`: layouts e callbacks
- `scripts/`: rotinas auxiliares
