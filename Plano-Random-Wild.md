# Random Wild — plano do projeto

**Versão:** 1.0 · **Data:** 4 de outubro de 2026  
**Base:** PyChess Variants · **Utilização prevista:** dois amigos, partidas ocasionais  
**Alojamento escolhido:** Render Free + MongoDB Atlas Free

## 1. Objetivo e decisões fixadas

Criar um fork do PyChess Variants para jogar dois modos de variantes aleatórias:

| Modo | Conteúdo | Sorteio |
|---|---|---|
| **Wild 29** | As 12 variantes do pool histórico ICC, com as regras correspondentes | Pesos históricos descritos no ficheiro fornecido |
| **Random Dice** | Pool próprio, inicialmente com seis variantes e extensível | Pesos iguais por defeito; configuráveis |

Decisões do projeto:

- Reutilizar lobby, tabuleiros, relógios, partidas, WebSockets, perfis e histórico do PyChess.
- Em ambos os modos, **cada rematch escolhe outra variante**. Sem botão para repetir a mesma.
- A variante anterior fica excluída do sorteio desse rematch.
- O modo, o pool e o controlo de tempo mantêm-se; os jogadores trocam de cor.
- O sorteio acontece no servidor, depois de os dois jogadores aceitarem jogar.
- Começar com partidas casuais. Ratings de Wild/Dice são uma extensão posterior.
- Não tratar `wild29` ou `randomdice` como regras de tabuleiro: são modos que selecionam uma variante real.
- Wild 29 completo é um requisito da versão final. Um protótipo com menos variantes será identificado como experimental.

O nome geral do site e a identidade visual podem ser decididos depois. “Random Wild” é o nome de trabalho; “Random Dice” fica como nome do modo personalizado.

## 2. O que foi confirmado e o que ainda falta confirmar

Este documento é um plano de implementação, não uma certificação de que todas as regras ICC já foram reconstruídas.

Foi inspecionado o ZIP fornecido, cujo comentário de arquivo identifica a revisão `cd78fd1629caaf63256e45bc73d27dbd9654c2ba`. Foram confirmados:

- Backend Python/aiohttp, MongoDB e integração Fairy-Stockfish.
- `render-build.sh` e `Procfile` já existentes.
- Uso de `MONGO_HOST` e da porta definida por `PORT`.
- Definições de Atomic, Orda, Three-check e King of the Hill.
- Entradas de catálogo para `losers` e `giveaway`; isto não substitui testar a disponibilidade e as regras nas dependências realmente instaladas.
- O rematch atual reutiliza a variante e, normalmente, o FEN inicial. Isso precisa de adaptação para os dois modos aleatórios.

O texto `random-wild.txt` contém a lista de pesos e notas estratégicas. **Não contém uma especificação integral das regras**. Os pesos são atribuídos a MACTEP nessa fonte; falta corroboração documental primária. Os endereços históricos de ajuda ICC tentados nesta preparação não ficaram acessíveis.

Para os casos ainda incertos, a regra de trabalho será: localizar documentação ICC ou um arquivo fiel, escrever a especificação e só depois implementar. Sem equivalências inventadas a partir do nome.

## 3. Wild 29: pool completo

“Todas as variantes” significa as 12 integrantes do Wild 29 histórico indicado na fonte fornecida. Não significa implementar todos os Wilds 1–28; por exemplo, Bughouse não pertence a este pool.

| ICC Wild | Variante | Peso | Probabilidade na primeira partida | Caminho de implementação |
|---|---|---:|---:|---|
| 3 | Wild 3 — posição/material aleatórios | 1 | 1/24 = 4,17% | Reconstruir o gerador ICC e as restrições exatas |
| 4 | Wild 4 — posição/material aleatórios | 1 | 1/24 = 4,17% | Reconstruir o gerador ICC; distinguir de Wild 3 |
| 5 | Reversed | 2 | 2/24 = 8,33% | Confirmar posição inicial e regras; avaliar configuração/FEN |
| 8 | Advanced Pawns | 1 | 1/24 = 4,17% | Confirmar posição e regras dos peões; definição ICC própria |
| 9 | Two Kings | 1 | 1/24 = 4,17% | Investigar tratamento dos dois reis e condição de vitória |
| 17 | Loser's Chess | 3 | 3/24 = 12,50% | Candidato `losers`, com testes de conformidade ICC |
| 18 | Power Chess | 1 | 1/24 = 4,17% | Confirmar material/posição inicial; avaliar configuração/FEN |
| 22 | Chess960 / Fischer Random | 2 | 2/24 = 8,33% | `chess` + `chess960=true`; validar roque e geração |
| 23 | Crazyhouse | 3 | 3/24 = 12,50% | `crazyhouse`; validar particularidades ICC |
| 25 | Three Checks | 3 | 3/24 = 12,50% | `3check`; validar contagem e condições finais |
| 26 | Giveaway | 3 | 3/24 = 12,50% | Candidato `giveaway`; não substituir por Antichess |
| 27 | Atomic | 3 | 3/24 = 12,50% | `atomic`; validar particularidades ICC |
| **Total** | **12 variantes** | **24** | **100%** | |

Os nomes de Wild 3/4 são identificadores de trabalho, não descrições completas dos seus algoritmos históricos.

### 3.1. Ficha obrigatória de regras por variante

Antes de dar uma variante ICC como concluída, criar uma ficha com:

1. Fonte, versão histórica e eventuais divergências entre fontes.
2. FEN inicial ou algoritmo exato de geração; distribuição das posições, se documentada.
3. Movimento, captura e prioridade das capturas obrigatórias.
4. Estatuto do rei, xeque, mate e movimentos legais sob xeque.
5. Roque, promoção, movimento duplo de peão e en passant.
6. Vitória, empate, afogamento, repetição, regra de lances sem progresso e material insuficiente.
7. Casos especiais de fim por tempo e de apresentação do resultado.
8. Posições de referência com lances legais/ilegais e resultados esperados.

É possível precisar de ajustes nas regras de fim de partida do PyChess, além da configuração do motor.

### 3.2. Investigação específica dos seis casos menos diretos

| Variante | Questões que têm de ficar resolvidas |
|---|---|
| Wild 3 | Material permitido, distribuição, correspondência entre os lados, casas dos reis, bispos e direitos de roque |
| Wild 4 | Diferenças exatas face ao Wild 3; igualdade de material, independência dos lados e legalidade inicial |
| Wild 5 | Filas iniciais, direção dos peões, promoções imediatas, roque, en passant e segurança inicial dos reis |
| Wild 8 | Filas dos peões, movimento duplo, en passant e posição exata das restantes peças |
| Wild 9 | Que reis são reais, quais os xeques relevantes, se a condição final depende de um ou ambos, roque e promoção |
| Wild 18 | Número e casas das damas, presença das outras peças, roque e posição dos peões |

**Atenção ao Wild 8:** o `advancedpawn` encontrado no `variants.ini` upstream do Fairy-Stockfish coloca peões nas filas 3/6. O texto fornecido descreve `cxd5` como lance inicial do ICC Wild 8. Isto é uma discrepância concreta: a definição upstream não pode ser usada como equivalente sem investigar.

**Atenção ao Wild 9:** Two Kings não será substituído por Extinction, Three Kings ou uma variante com dois reis não reais só por ter aparência semelhante.

### 3.3. Losers, Giveaway e Antichess são distintos

O código upstream consultado define `losers` a partir das regras de xadrez, com captura obrigatória e condições invertidas de mate/afogamento, além de vitória ao ficar apenas com uma peça. Define `giveaway` com rei não real, captura obrigatória e roque; `antichess` deriva dele retirando o roque.

Estas definições são bons candidatos técnicos, não prova suficiente de toda a conformidade histórica ICC. Vamos testar a prioridade entre captura e resposta a xeque em Losers, promoções, afogamento e finalização. Random Dice usará **Loser's Chess**, como pedido, sem o trocar por Giveaway.

### 3.4. Critério para declarar Wild 29 completo

- Todas as 12 variantes disponíveis, com as fichas e os casos de referência concluídos.
- Nenhuma retirada silenciosamente do pool por falta de suporte.
- Pesos 1/2/3 reproduzidos e configurados numa versão fixa do pool.
- FENs válidos, peças corretamente apresentadas e legalidade igual no cliente e no servidor.
- Histórico, carregamento da partida e resultados coerentes.
- Se uma regra histórica continuar por esclarecer, o modo fica experimental com essa pendência indicada.

## 4. Random Dice: pool inicial e expansão

| Variante pedida | Identificador candidato | Estado de preparação | Peso inicial |
|---|---|---|---:|
| Atomic | `atomic` | Presente no ZIP | 1 |
| Orda, tal como no PyChess | `orda` | Presente no ZIP; manter peças e regras do PyChess | 1 |
| Loser's Chess | `losers` | Entrada de catálogo; validar integração completa | 1 |
| 3Check | `3check` | Presente no ZIP | 1 |
| King of the Hill | `kingofthehill` | Presente no ZIP | 1 |
| Rifle Chess | `rifle` — identificador proposto | Suporte por confirmar; prever extensão/fork | 1 |

O pool final inicial contém estas seis variantes. Durante o desenvolvimento, Rifle pode ficar pendente e o protótipo usar as outras cinco, claramente identificado como incompleto.

Com as seis ativas e pesos iguais: primeira partida com probabilidade 1/6 para cada variante; num rematch, cada uma das cinco restantes tem probabilidade 1/5.

Orda é assimétrico: um lado joga com o exército clássico e o outro com o exército Orda. Trocar as cores no rematch não garante uma partida de Orda para o outro lado, porque a variante também muda. Não acrescentar uma repetição forçada para equilibrar exércitos.

### 4.1. Como acrescentar mais variantes

Começar com um ficheiro de configuração versionado no repositório. Não é necessário construir um painel administrativo para dois jogadores.

Cada entrada terá:

- Identificador estável da variante no pool, nome visível e peso inteiro positivo.
- Variante real do motor, sinalizador Chess960 e estratégia de geração do FEN.
- Estado de disponibilidade e referência para as regras.
- Versão da definição e recursos gráficos necessários.

Só ativar uma nova entrada quando servidor, cliente, peças e finais estiverem validados. Dar ao utilizador a possibilidade de adicionar/remover variantes e ajustar pesos por configuração. Um editor visual pode vir depois.

Manter Wild 29 fixo e separado: acrescentar variantes ao Random Dice nunca altera o pool histórico.

## 5. Rifle Chess: plano de integração

Não foi encontrada uma entrada Rifle nas definições PyChess inspecionadas nem no `variants.ini` upstream consultado. Isto não prova ausência em todos os forks ou extensões. Primeiro verificar o motor e as bibliotecas exatas que forem instalados.

A interpretação de trabalho a confirmar é **captura à distância: a peça capturante permanece na casa de origem e a peça adversária é removida**. O nome Rifle, por si só, não resolve todas as regras.

### 5.1. Especificação antes de programar

Confirmar com a variante pretendida:

- Se todas as peças disparam e se o rei segue as mesmas regras de captura.
- Xeque e mate versus captura efetiva do rei.
- En passant: casas, remoção da peça e localização final do capturante.
- Promoção de peões em capturas e em movimentos sem captura.
- Roque e perda de direitos quando uma torre dispara sem se deslocar.
- Efeito de disparos sobre o contador de progresso, repetição e finais por tempo.
- Representação do lance para distinguir disparo de deslocação quando necessário.

### 5.2. Ordem de implementação

1. Verificar se o Fairy instalado permite representar a regra por configuração. Não presumir que Betza ou `variants.ini` bastam.
2. Se permitir, criar a definição e os testes sem fork do núcleo.
3. Se não permitir, criar um fork pequeno do Fairy-Stockfish, com mudanças isoladas para Rifle.
4. Adaptar geração de lances, aplicação/desfazer, ataques, legalidade, hash, notação e resultados conforme necessário.
5. Compilar a biblioteca Python **pyffish** usada pelo servidor.
6. Compilar/sincronizar o módulo **ffish-es6/WASM** usado pelo navegador.
7. Adaptar o tabuleiro: num disparo, remover o alvo e restaurar/manter o capturante na origem; validar animação e premoves.
8. Validar exportação, replay e análise. O motor WASM de análise deve suportar Rifle ou essa análise ficará explicitamente indisponível.

**Um executável UCI modificado, sozinho, não integra Rifle no site.** Servidor e cliente precisam de concordar nas regras. Bots e NNUE para Rifle são trabalho posterior; não são necessários para os dois humanos jogarem.

## 6. Sorteio e rematches

### 6.1. Fluxo

1. Um jogador cria convite/seek para Wild 29 ou Random Dice e escolhe o tempo.
2. O amigo aceita.
3. O servidor fixa a versão do pool, seleciona uma entrada e gera o FEN adequado.
4. A partida é criada com a variante real e com os metadados do modo.
5. Ambos veem o modo, a variante sorteada e um acesso breve às regras.
6. No fim, um jogador oferece rematch; o outro aceita.
7. O servidor exclui a entrada anterior, sorteia outra, troca as cores e cria a nova partida.

No Wild 22, selecionar Chess960 é uma etapa; gerar a posição Chess960 é outra. Num rematch de outro Wild, nunca reutilizar o FEN antigo ou o sinalizador Chess960 anterior.

### 6.2. Pesos quando não há repetição

Na primeira partida Wild 29, usar os 24 tickets da tabela. No rematch, retirar **todos** os tickets da variante anterior e sortear entre os restantes.

Exemplo: depois de Atomic, retirar os seus 3 tickets. Ficam 21. Cada variante de peso 1 passa a 1/21, cada uma de peso 2 a 2/21 e cada uma de peso 3 a 3/21.

Esta é a regra escolhida para o projeto. **Não afirmar que as probabilidades continuam 1/24, 2/24 e 3/24 em todos os rematches**, nem que a proibição de repetição foi documentalmente confirmada como regra ICC. Preservamos o pool e as regras históricas e explicitamos esta política de rematch.

### 6.3. Casos de erro e consistência

- Validar pesos e exigir pelo menos duas entradas distintas ativas.
- Se não houver alternativa válida, recusar o rematch com mensagem clara; não repetir silenciosamente.
- Resolver o sorteio uma única vez; aceitar duas mensagens simultâneas não pode criar duas partidas.
- Reutilizar o bloqueio/identificador de rematch existente no PyChess.
- Não ressorteiar em refresh, reconexão ou carregamento do histórico.
- Não aceitar variante/FEN escolhidos arbitrariamente pelo cliente para estes modos.
- Uma variante indisponível impede publicar o pool Wild 29 completo; não redistribuir os seus pesos em segredo.

## 7. Alterações previstas no código

Os caminhos abaixo foram localizados no ZIP. São pontos de entrada para trabalho futuro, não alterações já realizadas.

| Local | Alteração prevista |
|---|---|
| Novo módulo, por exemplo `server/random_modes.py` | Carregar/validar pools, resolver pesos, excluir variante anterior e devolver configuração real |
| `server/seek.py` | Metadados de modo/pool nos seeks, convites e serialização |
| `server/wsl.py` | Receber criação/aceitação, validar o modo e encaminhar pelo fluxo comum |
| `server/utils.py` — `new_game()` | Resolver modo antes de validar FEN e de construir `Game`; persistir a seleção |
| `server/game.py` — `Game` / `save_game()` | Guardar metadados e incluí-los no estado e na persistência final |
| `server/utils.py` — `load_game()` / `load_game_from_doc()` | Restaurar seleção e contexto sem novo sorteio |
| `server/wsr.py` — `handle_rematch()` | Propagar modo, excluir entrada anterior, limpar configuração antiga e manter idempotência |
| `server/typing_defs.py` / `server/ws_types.py` | Atualizar os contratos de documentos e mensagens |
| `server/variants.py` / `server/catalogued_variants.py` / `variants.ini` | Registar variantes ICC e Rifle conforme necessário |
| `client/lobby.ts` e módulos relacionados | Seleção de Wild 29/Random Dice e apresentação de seeks |
| `client/roundCtrl.ts` e módulos relacionados | Modo + variante atual, regras e rematch com novo sorteio |
| `client/variants.ts`, definições WASM e recursos de peças | UI e legalidade das variantes acrescentadas |
| Histórico, perfis e exportação | Mostrar modo de origem sem perder a variante real |

Não sobrecarregar um campo que identifica regras de tabuleiro com o nome do modo. Onde a estrutura atual exigir uma variante no seek, adaptar os tipos/validação de forma explícita e auditar os consumidores desse campo.

## 8. Persistência e versões

Manter o formato normal do PyChess para a variante efetiva, Chess960, FEN, lances e resultado. Acrescentar um bloco opcional `randomContext`, com nomes a confirmar na implementação:

```json
{
  "mode": "wild29",
  "poolId": "icc-wild29",
  "poolVersion": 1,
  "entryId": "icc-wild27",
  "rulesVersion": "icc-wild27-v1",
  "noImmediateRepeat": true,
  "previousGameId": null
}
```

Guardar o contexto desde a criação, não apenas no fim. A partida real continua a ser Atomic neste exemplo. Os campos propostos são uma extensão; não existem já com estes nomes no ZIP.

O pool usado numa série de rematches fica preso à versão inicial. Alterações de configuração aplicam-se a novas séries. Guardar definições antigas e, para variantes personalizadas, um snapshot ou referência imutável suficiente para replay. Se uma versão deixar de estar disponível, interromper a série com explicação.

Partidas antigas sem `randomContext` mantêm comportamento normal. PGN conserva a variante real e o FEN quando necessário; adicionar tags próprias para modo/pool sem substituir `Variant` por “Wild 29”.

## 9. Render + MongoDB Atlas

### 9.1. Arquitetura escolhida

| Componente | Serviço |
|---|---|
| Código e versões | Repositório GitHub do fork |
| Aplicação Python e frontend compilado | Um Web Service Render Free |
| Contas, partidas e dados persistentes | MongoDB Atlas Free |
| Endereço inicial e HTTPS | Subdomínio `onrender.com` atribuído pelo Render |
| Desenvolvimento | Ambiente local; Docker Compose do projeto quando adequado |

Não alojar MongoDB no filesystem efémero do Render. Não acrescentar VPS, domínio pago ou serviço de bots para o primeiro objetivo.

O Render pode dormir após 15 minutos sem pedidos HTTP nem mensagens WebSocket recebidas; o primeiro acesso pode levar cerca de um minuto. Pode também reiniciar o serviço. A atividade WebSocket recebida conta para evitar o sleep; uma ligação apenas aberta não é garantia suficiente. Testar os heartbeats reais do PyChess e períodos de reflexão longos.

O Atlas Free oferece cerca de 0,5 GB e não inclui backups geridos. Pode pausar após 30 dias sem ligações; preparar a retoma se o projeto ficar parado. Para dois jogadores, esta arquitetura é uma escolha inicial razoável, sujeita a validar memória e funcionamento reais. [S1–S4]

### 9.2. Deploy inicial

1. Criar o fork a partir da revisão fornecida e conservar uma base sem alterações.
2. Criar Atlas Free, utilizador da aplicação e configuração de acesso de rede para as saídas do Render.
3. Criar Render Web Service ligado ao repositório, uma instância e um processo servidor.
4. Fixar as versões compatíveis: o ZIP pede Python ≥3.14, Node 24.x e Yarn 1.x. Não assumir que os defaults do Render servem.
5. Usar `bash render-build.sh` como candidato de build; o script instala Python, instala Yarn e compila frontend/documentação.
6. Usar `python3 server/server.py` como candidato de arranque; o `Procfile` contém esse comando.
7. Confirmar bind em todas as interfaces, `PORT`, acesso às dependências nativas e carregamento de WASM.
8. Configurar o endereço público, sessões e OAuth; testar com dois navegadores/utilizadores.
9. Validar uma partida normal, rematch normal e persistência antes de introduzir modos aleatórios.

### 9.3. Configuração prevista

| Variável/definição | Finalidade |
|---|---|
| `MONGO_HOST` | URI Atlas com TLS; guardar como segredo do serviço |
| `URI` | Endereço HTTPS real da aplicação |
| `PROD=true` | Ativar o modo de produção do projeto |
| `FERNET_KEY` | Chave própria e estável para as sessões; não usar o default |
| `PORT` | Fornecida pelo Render; já lida pelo servidor |
| `ALLOWED_ORIGINS` | Rever para a origem e recursos do nosso deployment |
| OAuth | Rever `server/oauth_config.py`, IDs e callback do novo endereço |
| `ADMINS` | Utilizadores administrativos, se forem necessários |

Começar com o login já existente, preferencialmente Lichess se ambos o usarem. Não inventar um sistema de passwords para esta primeira versão. Confirmar o callback no domínio próprio: não assumir que a configuração `pychess.org` funciona no fork.

O uso por dois amigos não torna o endereço privado. Se quisermos impedir terceiros de jogar, acrescentar uma allowlist dos dois utilizadores, aplicada no servidor aos convites e partidas.

### 9.4. Memória, reinícios e continuidade

- Medir consumo no arranque e com duas sessões, uma partida e vários rematches.
- Ocultar funções dispensáveis sem uma reescrita extensa; reduzir tarefas de fundo apenas se as medições justificarem.
- Evitar bots e análise pesada no servidor na primeira versão. Análise local no navegador pode ser opcional.
- Testar desconexão, reconexão, sleep e restart. Dados na MongoDB não garantem, sozinhos, a retoma do relógio de uma partida ativa.
- Se partidas ativas não recuperarem corretamente, definir e mostrar o comportamento de interrupção; considerar checkpoints apenas se necessários.
- Não criar pings artificiais para manter o serviço sempre acordado.
- Fazer cópias ocasionais com `mongodump`, sobretudo antes de alterações de esquema; testar uma restauração.

Render Free não fica aprovado só porque a página abre. O teste decisivo é os dois jogadores conseguirem jogar e fazer vários rematches com relógios e estado coerentes.

## 10. Fases e critérios de conclusão

| Fase | Entrega | Critério para avançar |
|---|---|---|
| 0 — Base | Fork identificado, dependências e decisões registadas | Build reproduzível e revisão base preservada |
| 1 — Alojamento | PyChess original no Render + Atlas | Dois utilizadores entram, jogam e recuperam histórico |
| 2 — Motor de sorteio | Modo aleatório com pequeno pool técnico | Uma seleção no servidor; metadata persistida; sem duplicação |
| 3 — Random Dice | Cinco variantes disponíveis e rematches novos | Todas funcionam; Rifle explicitamente pendente |
| 4 — Regras ICC | Dossiê das 12 variantes e casos de referência | Ambiguidades resolvidas ou documentadas como bloqueantes |
| 5 — Wild 29 | Todas as variantes e pesos integrados | Conformidade, UI, histórico e rematch validados |
| 6 — Rifle | Definição/fork, Python, WASM e tabuleiro | Capturas, replay e resultados concordam nos dois lados |
| 7 — Versão hobby concluída | Wild 29 completo + Random Dice com seis variantes | Sessão real dos dois jogadores e checklist abaixo aprovada |
| 8 — Expansões | Mais variantes, pesos e polimento | Só acrescentar o que for útil ao uso real |

As fases 4 e 6 podem ser investigadas durante a construção do protótipo. Os seis casos ICC menos diretos e Rifle são as maiores incertezas de esforço. Não fixar datas antes dessas investigações e do primeiro build no Render.

## 11. Validação

### Sorteio e criação

- Os pesos Wild 29 somam 24 e todas as 12 entradas estão presentes.
- Testar limites do sorteio com RNG controlado; não depender de um teste estatístico aleatório instável.
- Exclusão completa da entrada anterior em rematches.
- Pools vazios, peso inválido e ausência de alternativa dão erro claro.
- Refresh e reconexão preservam a seleção.
- Aceitação simultânea cria apenas uma partida.

### Regras, frontend e dados

- Casos de referência de cada Wild: capturas, xeque, roque, promoção, en passant e finais relevantes.
- Concordância pyffish ↔ ffish-es6; Orda apresenta todas as peças especiais.
- Rifle mantém o capturante na origem e remove o alvo em todos os tipos de captura permitidos.
- Chess960 não herda posição/direitos de outra variante.
- Save/load, histórico e PGN preservam variante real, contexto e FEN.
- Rematches mantêm pool/tempo, trocam cores e escolhem variante distinta.
- Partidas fora dos modos aleatórios conservam o comportamento atual.

### Qualidade do fork

Seguir `AGENTS.md` do projeto quando começarmos a alterar código: verificações frontend (`yarn lint`, `yarn typecheck`, `yarn md`, `yarn test`), verificações Python e testes dirigidos ao que mudou. Acrescentar verificação no navegador para comportamento visível. Este turno produz apenas o plano; esses testes ainda não foram executados.

## 12. Depois da primeira versão

Extensões possíveis, sem bloquear o objetivo dos dois amigos:

- Novas variantes escolhidas pelo utilizador no Random Dice.
- Editor de pool/pesos e conjuntos temáticos.
- Histórico de sorteios da sessão e resultados entre os dois jogadores.
- Ratings separados por modo, sem atualizar automaticamente o rating da variante sorteada.
- Bots, análise específica de Rifle e torneios aleatórios, se vierem a interessar.

Preservar a licença AGPL-3.0, atribuições e ligação ao código correspondente ao fork. Consultar o `LICENSE` do ZIP antes da publicação.

## 13. Checklist da versão pretendida

- [ ] Render + Atlas operacionais e configuração reproduzível.
- [ ] Os dois jogadores entram e conseguem iniciar uma partida por convite.
- [ ] Wild 29 tem as 12 variantes, regras verificadas e pesos documentados.
- [ ] Random Dice tem Atomic, Orda, Losers, 3Check, King of the Hill e Rifle.
- [ ] Cada rematch seleciona outra variante; não existe opção de repetir a mesma.
- [ ] Servidor e cliente concordam nos lances e resultados.
- [ ] Histórico e replay sobrevivem a redeploy/restart.
- [ ] Reconexão e comportamento dos relógios foram testados.
- [ ] Novas variantes podem ser adicionadas por configuração.
- [ ] Segredos, OAuth, origem pública e backup estão configurados.
- [ ] Pendências históricas ou de suporte estão identificadas; não são apresentadas como concluídas.

## 14. Fontes e rastreabilidade

**Materiais fornecidos**

- `random-wild.txt`: composição/pesos do Wild 29 atribuídos a MACTEP, nomes e notas estratégicas. Não é um regulamento completo.
- `pychess-variants-master.zip`: revisão indicada acima; código e ficheiros mencionados nas secções 2, 7 e 9.

**Documentação externa consultada nesta preparação**

- **S1 — Render Free:** https://render.com/docs/free — sleep, filesystem efémero, reinícios e limites gratuitos.
- **S2 — Render WebSockets:** https://render.com/changelog/free-web-services-now-remain-active-while-receiving-websocket-messages — alteração de 24/02/2026.
- **S3 — Atlas Free:** https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/ — limitações, backups e pausa por inatividade.
- **S4 — Atlas, comparação de clusters:** https://www.mongodb.com/docs/atlas/manage-clusters/ — capacidade do plano Free.
- **S5 — Fairy-Stockfish, variantes:** https://fairy-stockfish.github.io/variants/ — variantes incorporadas e extensões.
- **S6 — Fairy-Stockfish, definições:** https://github.com/fairy-stockfish/Fairy-Stockfish/blob/master/src/variant.cpp — candidatos Losers, Giveaway e Antichess.
- **S7 — Fairy-Stockfish, configuração:** https://github.com/fairy-stockfish/Fairy-Stockfish/blob/master/src/variants.ini — definição Advanced Pawn consultada.

**Fontes ICC a recuperar durante a investigação**

- Ajuda histórica geral: `http://www6.chessclub.com/help/wild`.
- Ajuda por variante, incluindo `https://www.chessclub.com/help/Wild17` e equivalentes.
- Arquivos históricos dessas páginas ou documentação ICC preservada, se as páginas originais continuarem indisponíveis.

As referências upstream são mutáveis. Na implementação, fixar os commits/versões realmente usados e arquivar as especificações recuperadas. Os planos gratuitos também serão revalidados no momento do deploy.
