import { beforeEach, expect, jest, test } from '@jest/globals';
import { readFileSync } from 'node:fs';
import { fsxMoveSan, readSpellState, spellPieceMoves, spellTargets, splitSpellMove } from '../client/spellChess';
import { fsxVariantsIni, FSX_VARIANTS } from '../client/fsx';
import { uci2LastMove } from '../client/chess';
import { VARIANTS, disabledVariantsForCreateMode, isRandomModeOrResultVariant } from '../client/variants';
import { SpellInput } from '../client/input/spell';
import type { GameController } from '../client/gameCtrl';
import { parsePgnVariantTag, resolvePgnMove } from '../client/pgn';

const start = VARIANTS['spell-chess'].startFen;
const moves = ['e2e4', 'a7a8q', 'f@e7,e2e4', 'j@e5,e2e6', 'f@h8,a7a8q'];

test('FSX INI stays identical on the client and server', () => {
    expect(fsxVariantsIni.trim()).toBe(readFileSync('variants-fsx.ini', 'utf8').trim());
});

test.each([
    ['Rifle Chess', 'rifle-chess'], ['Spell Chess', 'spell-chess'], ['Brotherhood Chess', 'brotherhood'], ['Monster Chess', 'monster'],
])('PGN recognizes the human-readable %s header', (header, variant) => {
    expect(parsePgnVariantTag(header).variant).toBe(variant);
});

test.each([...FSX_VARIANTS])('%s is a Dice result without independent ratings or computed AI', name => {
    expect(isRandomModeOrResultVariant(name)).toBe(true);
    expect(disabledVariantsForCreateMode('createGame', '', false)).toContain(name);
    expect(VARIANTS[name].ratingEnabled).toBe(false);
    expect(VARIANTS[name].aiDisabled).toBe(true);
});

test('spell prefix parsing preserves promotions and distinguishes ordinary moves', () => {
    expect(splitSpellMove('f@h8,a7a8q')).toEqual({ move: 'a7a8q', cast: { spell: 'f', square: 'h8' } });
    expect(splitSpellMove('a7a8q')).toEqual({ move: 'a7a8q' });
    expect(spellPieceMoves(moves)).toEqual(['e2e4', 'a7a8q']);
    expect(spellPieceMoves(moves, { spell: 'j', square: 'e5' })).toEqual(['e2e6']);
    expect(spellTargets(moves, 'f')).toEqual(['e7', 'h8']);
});

test('spell PGN preserves targets and never picks an arbitrary target from ambiguous native SAN', () => {
    expect(fsxMoveSan('spell-chess', 'f@e7,e2e4', 'e4/F')).toBe('f@e7,e4');
    expect(fsxMoveSan('spell-chess', 'j@a3,a1a5', 'Rxa5/J')).toBe('j@a3,Rxa5');
    const board = {
        variant: () => 'spell-chess',
        legalMoves: () => 'e2e4 f@e7,e2e4 f@a1,e2e4',
        sanMove: (move: string) => move.includes(',') ? 'e4/F' : 'e4',
    };
    expect(resolvePgnMove(board, { san: 'f@e7,e4' }, 'ply 1').move).toBe('f@e7,e2e4');
    expect(resolvePgnMove(board, { san: 'f@e7,e2e4' }, 'ply 1').move).toBe('f@e7,e2e4');
    expect(resolvePgnMove(board, { san: 'e4' }, 'ply 1').move).toBe('e2e4');
    expect(() => resolvePgnMove(board, { san: 'e4/F' }, 'ply 1')).toThrow('unsupported');
});

test('last-move highlighting uses the piece leg and spell target without changing Duck moves', () => {
    expect(uci2LastMove('f@h8,a7a8q')).toEqual(['a7', 'a8', 'h8']);
    expect(uci2LastMove('a2a3,a3b3')).toEqual(['a2', 'a3', 'b3']);
});

test('Monster forced passes have lossless PGN notation and no invalid board highlight', () => {
    expect(uci2LastMove('0000')).toBeUndefined();
    expect(fsxMoveSan('monster', '0000', 'a7')).toBe('--');
    const board = { variant: () => 'monster', legalMoves: () => '0000', sanMove: () => 'a7' };
    expect(resolvePgnMove(board, { san: '--' }, 'ply 2')).toEqual({ move: '0000', san: '--' });
    expect(() => resolvePgnMove({ ...board, legalMoves: () => 'e2e4' }, { san: '--' }, 'ply 1')).toThrow('illegal');
});

test('FEN restores each side reserves, cooldowns and active zones', () => {
    expect(readSpellState(start).reserves).toEqual({ white: { f: 5, j: 2 }, black: { f: 5, j: 2 } });
    const state = readSpellState(start + ' wf:e7,bj:c4 <3 1 2 0>');
    expect(state.cooldowns).toEqual({ white: { f: 3, j: 1 }, black: { f: 2, j: 0 } });
    expect(state.zones).toEqual([
        { color: 'white', spell: 'f', square: 'e7' },
        { color: 'black', spell: 'j', square: 'c4' },
    ]);
});

beforeEach(() => { document.body.innerHTML = '<div id="mainboard"></div><div class="pocket-top"></div><div class="pocket-bot"></div>'; });

function controller() {
    const ctrl = {
        home: '', fullfen: start, turnColor: 'white', mycolor: 'white',
        chessground: { state: { movable: { color: 'white' } }, set: jest.fn(), unselect: jest.fn() },
        ffishBoard: { legalMoves: () => moves.join(' ') },
        canUseSpells: jest.fn(() => true), spellColor: () => 'white', setDests: jest.fn(),
    };
    const input = new SpellInput(ctrl as unknown as GameController);
    ctrl.setDests.mockImplementation(() => input.sync());
    input.sync();
    return { ctrl, input };
}

test('choose a potion, target an occupied square, then submit one compound move', () => {
    const { input } = controller();
    document.querySelector<HTMLButtonElement>('#spell-controls button')!.click();
    expect(input.targeting).toBe('f');
    expect(input.pieceMoves(moves)).toEqual([]);
    expect(input.select('e7')).toBe(true);
    expect(input.cast).toEqual({ spell: 'f', square: 'e7' });
    expect(input.pieceMoves(moves)).toEqual(['e2e4']);
    expect(input.complete('e2e4')).toBe('f@e7,e2e4');
    expect(input.cast).toBeUndefined();
});

test('cancel, resync and opponent turns cannot retain or submit a stale spell', () => {
    const { ctrl, input } = controller();
    document.querySelector<HTMLButtonElement>('#spell-controls button')!.click();
    input.select('e7');
    document.querySelector<HTMLButtonElement>('.spell-cancel')!.click();
    expect(input.complete('e2e4')).toBe('e2e4');
    document.querySelector<HTMLButtonElement>('#spell-controls button')!.click();
    input.select('e7');
    ctrl.fullfen = start + ' wf:e7 <3 0 0 0>';
    ctrl.canUseSpells.mockReturnValue(false);
    input.sync();
    expect(input.cast).toBeUndefined();
    expect(document.querySelector<HTMLButtonElement>('#spell-controls button')!.disabled).toBe(true);
});
