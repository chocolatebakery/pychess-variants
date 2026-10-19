# Logotipos e pecas dos modos Random

Atualizado em 2026-10-19: integrado o pack `random_wild_svg_pack_complete`
e o novo logotipo Cylinder.
Os 31 SVGs foram movidos para as pastas do projeto, sem alterar os desenhos.
O README original ficou em `static/images/pieces/random-wild-pack.md`.

Random Dice tem agora 29 entradas quando FSX esta instalado; Wild 29 mantem
as suas 6 entradas. A integracao dos motores esta em `FSX-no-Site.md`.

## 1. Logotipos integrados

| Variante | SVG em `static/icons/` | Estado |
|---|---|---|
| Knightmate | `knightmate.svg` | Ativo |
| Atomar | `atomar.svg` | Ativo |
| Berolina Chess | `berolina.svg` | Ativo |
| Extinction Chess | `extinction.svg` | Ativo |
| Kinglet | `kinglet.svg` | Ativo |
| Three Kings | `threekings.svg` | Ativo |
| Torpedo Chess | `torpedo.svg` | Ativo |
| Losers | `losers.svg` | Ativo; ja nao reutiliza Seirawan |
| Rifle Chess | `riflechess.svg` | Ativo no Dice com FSX |
| Spell Chess | `spellchess.svg` | Ativo no Dice com FSX |
| Brotherhood | `brotherhood.svg` | Ativo no Dice com FSX |
| Monster Chess | `monster.svg` | Copiado de `../new_icons/monster.svg`; ativo no Dice |
| Cylinder Chess | `cylinder.svg` | SVG fornecido, ativo no Dice com FSX |
| Spartan | `spartan.svg` | Recursos e icone nativo existentes preservados |

Random Dice passou a usar `static/icons/randomdice.svg`, uma versao com os
pontos transparentes derivada do `dice.svg` existente, que foi preservado.
Substitui o antigo simbolo droid. Nao veio um logotipo Wild 29 neste pack: esse
modo conserva o simbolo generico plus-square. Giveaway continua com o simbolo
light; pode futuramente reutilizar `antichess.svg` ou receber desenho proprio.

Os novos logotipos sao mascaras SVG em `static/random-icons.css`, com cor
herdada do tema. Os pequenos identificadores de icone continuam com um unico
carater privado, definido em `client/variants.ts` e `server/variants.py`.
A fonte antiga nao foi modificada; as outras variantes mantem os seus icones.

O mapeamento e definido no codigo, nao no campo legado `icon` do MongoDB.
A folha de estilo e carregada pelo template base, incluindo paginas de partidas,
lobby, perfil, historico e listas que usam `data-icon`.

## 2. Pecas integradas

### Berolina

- Peoes marcados do pack: `static/images/pieces/berolina/merida/wP.svg` e `bP.svg`.
- As outras pecas reutilizam o Merida normal.
- Familia `berolina`, estilo `merida`, em `static/piece/berolina/merida.css`.
- O builtin Berolina passa a escolher esse set, em vez do fallback com letras.
- Sets carregados pelo utilizador continuam a ter prioridade.

Ja existiam outros peoes Berolina em `static/images/pieces/alfaerie/`. Nao foram
removidos: este set usa os novos desenhos Merida fornecidos no pack.

### Knightmate

- Papel `k`: cavalos royais marcados do pack, em
  `static/images/pieces/knightmate/merida/wN.svg` e `bN.svg`.
- Papel `m`: reis normais Merida, como pedido anteriormente.
- Restantes pecas: Merida normal.
- A familia e o estilo existentes `knightmate/standard` foram preservados.

### Spell Chess

Os 16 SVGs foram movidos para `static/images/pieces/spellchess/merida/`:
as seis pecas normais por cor e `wF/bF` (Freeze), `wJ/bJ` (Jump).
O set tem CSS de origem em `static/piece/spellchess/merida.css`, CSS gerado e
familia `spellchess`, disponivel para metadata builtin de `spell-chess`.

Spell Chess esta agora ligado ao terceiro motor, com controlos de Freeze/Jump,
reservas, cooldowns e zonas persistidas no FEN. Rifle e Brotherhood reutilizam
pecas normais e tambem estao no Dice, tal como Monster e Cylinder. Sem FSX
instalado, estas cinco entradas sao excluidas do sorteio.

Extinction, Kinglet, Three Kings e Torpedo continuam a reutilizar pecas normais.
Monster e Cylinder tambem usam o set normal; nao exigem novos SVGs de pecas
nem recompilacao. Spartan usa a familia `spartan` ja existente, com estilos
`spartan0` e `spartan1`, incluindo todas as pecas especiais das negras.
Os recursos existentes de Orda, Seirawan, Capablanca, Duck, Hoppel-Poppel e
Makruk foram mantidos.

## 3. Regenerar estilos depois de alterar pecas

```bash
python3 piece_image_to_css.py static/piece/knightmate/standard.css
python3 piece_image_to_css.py static/piece/berolina/merida.css
python3 piece_image_to_css.py static/piece/spellchess/merida.css
```

Nao editar manualmente `static/piece-css/`: os ficheiros sao gerados.
Incluir no commit os SVGs, os CSS de origem e os CSS gerados.

## 4. Verificacao e motores

Os testes de recursos verificam SVGs, mapeamentos de icones, cobertura dos sets,
CSS gerado e preservacao dos papeis do Knightmate. Os testes de browser cobrem
as variantes ativas em desktop/telemovel e nos dois temas.

Compilar FSX nao instala recursos visuais nem implementa a UI dos feiticos.
As instrucoes dos motores estao em `../Fairy-Stockfish-X-master/Compilar-Windows.md`
e `../Fairy-Stockfish-X-master/Compilar-Linux.md`.
