# Plugins

O PC Polimata aceita plugins Python que adicionam dados ao relatório/CLI e, opcionalmente, uma aba na GUI.

## Contrato (`pc_polimata.core.plugins.Plugin`)

```python
class Plugin(Protocol):
    name: str  # único; usado para habilitar/desabilitar
    version: str

    def collect(self) -> dict[str, Any]: ...  # dados serializáveis em JSON
```

Opcional:

- `description: str` — mostrado em Configurações → Plugins.
- `create_tab(master, app) -> None` — recebe o frame da aba (customtkinter) e a janela principal; o app cria
  uma aba `🔌 <name>`. Importe `customtkinter` **dentro** da função, para o plugin continuar funcionando na CLI.

Um módulo pode expor o plugin como `plugin = MeuPlugin()` ou `def get_plugin() -> Plugin`. Um entry point pode
apontar para o objeto, a classe (será instanciada) ou o módulo.

## Onde o app procura

1. **Embutidos**: `pc_polimata/plugins/uptime.py` (tempo ligado, com aba de exemplo) e
   `pc_polimata/plugins/battery.py` (carga e saúde da bateria).
2. **Entry points** do grupo `pc_polimata.plugins` de pacotes instalados:

   ```toml
   # pyproject.toml do seu pacote
   [project.entry-points."pc_polimata.plugins"]
   meu_plugin = "meu_pacote.plugin:plugin"
   ```

3. **Pasta local**: todo `*.py` em `%APPDATA%\PCPolimata\plugins` (Windows) ou `~/.config/pc-polimata/plugins`
   (Linux); arquivos que começam com `_` são ignorados. Exemplo pronto: [examples/plugins/cpu_freq.py](examples/plugins/cpu_freq.py).

Se dois plugins tiverem o mesmo `name`, vale o primeiro na ordem acima.

## Isolamento de falhas

Toda chamada passa por `PluginHost`:

- erro ao importar (inclusive `SyntaxError`) vira `load_error`, mostrado em vermelho em Configurações;
- exceção em `collect()` ou retorno que não é `dict` vira `{"ok": false, "error": "..."}` no relatório;
- exceção em `create_tab()` mostra a mensagem dentro da aba;
- valores não serializáveis são convertidos para texto.

Ou seja, um plugin com defeito não derruba o app. **Isso não é um sandbox de segurança**: plugins são código
Python com as mesmas permissões do app. Instale só plugins em que você confia.

## Usar

- GUI: Configurações → Plugins (marcar/desmarcar e reiniciar para abas novas).
- CLI: `pc-polimata --list-plugins` e `pc-polimata --plugins -o relatorio.json`.

## Testar o seu plugin

```python
from pc_polimata.core.plugins import PluginHost, _record
from meu_pacote.plugin import plugin

result = PluginHost([_record(plugin, "test", plugin.name)]).collect_all()[plugin.name]
assert result.ok, result.error
```
