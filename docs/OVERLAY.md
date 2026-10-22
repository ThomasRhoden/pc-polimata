# Overlay e FPS

## Overlay de sensores (Windows e Linux)

Aba **Overlay & FPS** → *Mostrar/ocultar overlay* (ou pelo menu da bandeja). Uma janela pequena, sem borda,
sempre por cima e semitransparente mostra CPU %, GPU %, RAM % e temperaturas, atualizada no intervalo das
Configurações. Canto, tamanho (small/medium/large) e opacidade (0.2–1.0) ficam em Configurações.
Arraste para mover; clique direito fecha.

**Limitações honestas**

- É uma janela comum do SO, **não um hook no jogo**. Aparece por cima de jogos em **janela** ou **janela sem
  borda**. Em **tela cheia exclusiva** (DirectX/Vulkan) o jogo cobre qualquer janela e o overlay some. Para
  overlay dentro de tela cheia, use ferramentas que injetam no render (RTSS, MangoHud, overlay da NVIDIA/AMD).
- Transparência depende do gerenciador de janelas; em alguns ambientes Linux sem compositor ela é ignorada.
- O overlay só é atualizado enquanto o monitoramento está ativo (a pausa pela bandeja congela os valores).

## FPS, 1% low e frametime (Windows, PresentMon)

O PC Polimata não mede FPS sozinho. Ele usa o **[PresentMon](https://github.com/GameTechDev/PresentMon)**
(open source, da Intel), que lê eventos ETW do Windows e grava um CSV com uma linha por frame.

1. Baixe o executável de linha de comando em <https://github.com/GameTechDev/PresentMon/releases>
   (ex.: `PresentMon-2.x.x-x64.exe`).
2. Coloque-o no `PATH` **ou** defina `PRESENTMON_PATH` com o caminho completo. O app também procura em
   `%ProgramFiles%\Intel\PresentMon`.
3. Rode o PC Polimata **como administrador** (exigência do ETW).
4. Com o jogo aberto, informe o executável (ex.: `game.exe`), escolha 10/30/60 s e clique em
   *Medir FPS (PresentMon)*. O resultado aparece na aba, no relatório (`fps_capture`) e no overlay.

Também dá para analisar um CSV gravado antes, inclusive em Linux:

```bash
pc-polimata --fps-csv captura.csv --process game.exe
```

**Como os números são calculados** (`pc_polimata/core/presentmon.py`):

- frametime = coluna `MsBetweenPresents` (PresentMon 1.x/2.x) ou `FrameTime` (2.x); linhas `NA` são ignoradas;
- FPS médio = 1000 / frametime médio;
- 1% low = FPS médio do 1% de frames mais lentos (definição usada em reviews);
- p99 e máximo de frametime em ms.

**Limitações**: somente Windows; requer admin; mede a **cadência de apresentação** (o que o PresentMon vê),
não o tempo de GPU por frame; os parâmetros de linha de comando seguem o PresentMon 2.x (a 1.x usa os
mesmos nomes com um hífen só — rode-a manualmente e use `--fps-csv`). O parser é testado com CSVs de
exemplo; a captura real não pôde ser testada na VM Linux de desenvolvimento.

## FPS no Linux (MangoHud)

O [MangoHud](https://github.com/flightlessmango/MangoHud) grava logs CSV de frametime.

1. Instale o MangoHud (`sudo apt install mangohud`, `pacman -S mangohud`...).
2. Rode o jogo com log ativado, por exemplo:

   ```bash
   MANGOHUD=1 MANGOHUD_CONFIG=output_folder=$HOME/mangohud_logs,autostart_log=1 %command%   # Steam
   mangohud --dlsym ./jogo                                                                  # nativo
   ```

   Sem `autostart_log`, inicie/pare o log com **Shift+F2** dentro do jogo.
3. Depois: `pc-polimata --fps-csv ~/mangohud_logs/jogo_2026-10-22_01-00-00.csv`.

`--fps-csv` **detecta o formato** pelo cabeçalho: PresentMon (`MsBetweenPresents`/`FrameTime`) ou MangoHud
(linha `fps,frametime,...`, com ou sem a linha `FRAME METRICS` e as especificações no topo). A saída JSON traz
`"format": "presentmon" | "mangohud"`. Arquivos `*_summary.csv` são ignorados.

## FPS ao vivo no overlay

Aba **Overlay & FPS** → *FPS ao vivo no overlay*:

- **Arquivo CSV…**: acompanha um CSV que outro programa ainda está gravando (PresentMon ou MangoHud);
- **Pasta do MangoHud…**: segue sempre o CSV mais novo da pasta (o MangoHud cria um arquivo por sessão);
- **PresentMon ao vivo** (Windows): inicia o PresentMon sem tempo limite para o processo informado.

A cada 1 s o app lê só os bytes novos do arquivo (linhas incompletas esperam a próxima leitura; arquivo
truncado/recriado reinicia a leitura), calcula FPS médio, 1% low e frametime **dos últimos 5 s** e mostra no
overlay (`FPS 144  1% 98  6.9 ms`). Na CLI: `pc-polimata --fps-csv arquivo.csv --follow`.

Limitações: o valor tem o atraso do próprio log (o MangoHud grava em lotes, então pode haver 1–2 s de atraso);
o PresentMon ao vivo precisa de admin; o overlay continua invisível em tela cheia exclusiva.
