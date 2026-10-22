# Contribuindo com o PC Polimata

Obrigado pelo interesse! Este é um projeto de portfólio, mas issues e PRs são bem-vindos.

## Ambiente

```bash
git clone https://github.com/ThomasRhoden/pc-polimata.git
cd pc-polimata
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,memory,pdf]"
```

## Antes de abrir um PR

```bash
ruff check . && ruff format --check .
mypy
pytest --cov
xvfb-run -a pytest tests/test_gui_smoke.py    # Linux sem monitor (opcional)
```

## Regras do projeto

- **`core/` não importa nada de `gui/`.** Lógica nova vai para `core/` com testes; a GUI só apresenta.
- **Degradação graciosa**: dependências e hardware opcionais nunca devem derrubar o app. Retorne `None`
  e mostre "n/d".
- **Testes sem hardware real**: injete dependências (ver `network.py`, `smart.py`, `windows_temps.py`) e
  use fixtures (ex.: sysfs falso em `tests/test_gpu_amd.py`).
- **Sem segredos no repositório**: chaves de API vêm de variável de ambiente ou do arquivo `api_key`
  no diretório de config do usuário.
- **Textos da interface** em português via `tr("...")`, com tradução em `pc_polimata/i18n.py`.
- **Commits** no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
  (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`, `chore:`).
- Atualize o `CHANGELOG.md` na seção `[Não lançado]`.

## Novo backend de hardware

1. Função em `core/` que retorna dataclasses/dicts e nunca lança exceção para o chamador final.
2. Testes com fakes cobrindo sucesso, ausência da dependência e dados incompletos.
3. Linha na tabela "Suporte de hardware" do README.
