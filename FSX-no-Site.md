# Terceiro motor: Fairy-Stockfish-X

Integrado em 2026-10-18, mantendo os motores oficial e Alice separados.

| Motor | Servidor | Browser | Variantes |
|---|---|---|---|
| Oficial | `pyffish` | `ffish-es6` | Variantes anteriores, exceto Alice |
| Alice | `pyffish_alice` | `ffish-alice-es6` | Alice |
| FSX | `pyffish_fsx` | `ffish-fsx-es6` | Rifle Chess, Brotherhood, Spell Chess, Monster Chess |

## Instalar em Linux/WSL

Requisitos: CPython 3.14, compilador C++17, headers Python, uv, Node 24 e
Yarn Classic. O WSL Ubuntu 24.04 usado nos testes tem GCC/G++ 13.3.

Na pasta `pychess-variants`, dentro de Linux/WSL:

```bash
uv sync --frozen --extra dev
yarn install --frozen-lockfile
yarn dev
yarn md
uv run server/server.py -a
```

Para o servidor normal, configura tambem MongoDB e as ENV descritas em
`Instalar-no-Render.txt`. `-a` permite visitantes anonimos, nao cria MongoDB.
A pre-visualizacao com MongoDB em memoria e apenas uma ferramenta local de teste.

`uv sync` compila automaticamente `vendor/pyffish-fsx` no proprio Linux.
Nao instala a wheel especifica do WSL, nao altera o pacote oficial e nao exige
`FSX_PYTHON_PACKAGE` nem uma ENV para selecionar o motor no site.

Verificar os imports:

```bash
uv run python -c 'import pyffish, pyffish_alice, pyffish_fsx; print(pyffish.version(), pyffish_alice.version(), pyffish_fsx.version())'
PYTHONPATH=server uv run python -c 'from fsx import fsx_available; print(fsx_available())'
```

No Python Windows, a dependencia FSX nao e instalada automaticamente: executa
o servidor no WSL para jogar estas quatro variantes. Sem `pyffish_fsx`, o sorteio
exclui apenas essas quatro entradas; nunca as executa com regras de chess normal.

## Recursos e deploy

- `vendor/ffish-fsx-es6`: JS/WASM da mesma compilacao, tipos e GPL.
- `vendor/pyffish-fsx`: fonte correspondente e GPL; o pacote gera `pyffish_fsx`.
- `variants-fsx.ini` e `client/fsx.ts`: definicoes Rifle/Brotherhood/Monster.
  Spell Chess e builtin. O INI oficial do site nao foi substituido.
- `cp2static.sh`: copia JS e WASM FSX para `static/`, com nomes separados.
  O cliente carrega o modulo ES6 FSX apenas nas variantes que o usam.
- O Dockerfile copia os dois pacotes locais e instala a extensao FSX.

Incluir `vendor/`, os dois locks e `variants-fsx.ini` ao publicar o projeto.
O deploy Linux precisa de um compilador C++17 e headers Python durante o build.
No Render nativo, usa `bash render-build.sh` como build e
`python3 server/server.py` como start, e configura MongoDB Atlas online.
O script instala primeiro `./vendor/pyffish-fsx` e depois a aplicacao com pip.
O pip nao interpreta `[tool.uv.sources]`; se usares pip manualmente, preserva
essa ordem. A alternativa `uv sync --frozen` ja resolve o pacote local pelo lock,
mas exige iniciar o servidor no mesmo ambiente, com `uv run server/server.py`.
Nao ha ENV FSX adicional. A compilacao a partir de fonte evita depender da glibc
da wheel exportada do Ubuntu; o build Docker nao foi executado nesta verificacao.

## Partidas e limites

Random Dice tem 27 entradas com pesos iguais quando FSX esta instalado.
A versao do pool passou a 7; as revanches continuam a excluir so a entrada
anterior. Wild 29 mantem o pool ICC anterior. Nao se criaram modos de jogo ou
ratings independentes para estas variantes.

Rifle mantem o atacante na origem quando captura. Brotherhood impede capturas
entre pecas do mesmo tipo, exceto reis. Spell Chess oferece Freeze e Jump, com
alvo, cancelamento, reservas e cooldowns; feitico e movimento sao um unico lance.
O FEN conserva zonas/cooldowns, incluindo ao recarregar ou rever uma partida.
O codec de Spell Chess conserva o token composto completo, incluindo promocao.
O PGN usa alvos explicitos, por exemplo `f@e7,e4`: a notacao nativa `e4/F`
omite a casa-alvo e nao e suficiente para reproduzir uma partida sem ambiguidade.

Estas variantes funcionam entre humanos e contra Random-Mover. A AI calculada
e a avaliacao automatica estao desativadas para elas: o worker/motor de analise
oficial nao implementa estas regras. Para as disponibilizar sera necessario
integrar tambem um executavel FSX UCI compativel no worker, nao apenas pyffish.
A reproducao manual de partidas e a importacao PGN usam o motor de regras FSX.

## Monster Chess e testes diretos

O lobby tem um bloco separado `Tests / Random-Mover` com Monster, Rifle e Spell
Chess, escolha de cor, minutos e incremento. Estas partidas nao sorteiam uma
variante: usam diretamente a escolhida, sempre casual e contra Random-Mover.
A criacao normal continua a oferecer apenas Wild 29 e Random Dice.

Monster copia a definicao `[monster:extinction]` do FSX: rei branco em e1 e
peoes c2/d2/e2/f2 contra o exercito negro normal. As brancas jogam duas vezes,
com a mesma peca ou duas diferentes; as negras jogam uma vez. O servidor faz
automaticamente o passe negro obrigatorio entre os dois lances brancos,
sem consumir tempo nem atribuir incremento as negras nesse passe.
O incremento aplica-se a cada lance real. O passe fica no historico como
`0000` e no PGN como `--`, para permitir reload, takeback e replay corretos.

Importante: esta definicao FSX usa captura/extincao do rei como fim da partida,
nao a imposicao de xeque-mate descrita no texto `new_icons/monster-rules.txt`.
O site preserva as regras do INI fornecido, sem modificar o motor compilado.
Monster reutiliza as pecas normais e usa o logotipo `static/icons/monster.svg`.
Nao e necessario recompilar JS/WASM ou pyffish para esta adicao ao INI.

## Placar da sessao

O lobby e a pagina de jogo mostram resultados por variante real: tu, empates e
adversario, com totais. Conta partidas em que participaste enquanto estavam
ativas neste separador, incluindo as de testes e as sorteadas nos dois modos.
Chess960 tem linha separada. Resultados repetidos por reload/reconexao contam
so uma vez; partidas abortadas, erros de motor e arquivos abertos nao contam.

O placar usa `sessionStorage`, separado por utilizador e separador do browser.
Sobrevive a navegacao/reload; nao altera ratings nem grava estatisticas no MongoDB.
O botao de limpar reinicia os totais sem voltar a contar jogos ja terminados.
Na pagina de jogo, o placar original entre os jogadores continua primeiro;
o novo placar por sessao aparece abaixo, sem substituir o historico original.

## Testar

```bash
PYTHONPATH=server:tests uv run python -m unittest test_fsx test_random_modes test_wsr_rematch
yarn lint
yarn typecheck
yarn dev
yarn md
yarn test --runInBand
```

As fontes vendorizadas nao sao formatadas pelo Ruff do site. A sua proveniencia
e os ajustes de empacotamento estao em `vendor/README.md`.
