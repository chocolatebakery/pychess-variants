import { expect, test } from '@jest/globals';

import {
    canRateCustomStart,
    canRateStart,
    cwdaArmyClassNames,
    cwdaEngineVariant,
    devVariants,
    disabledVariantsForCreateMode,
    isRandomModeOrResultVariant,
    registerCataloguedVariant,
    unregisterCataloguedVariant,
    VARIANTS,
} from '../client/variants';

test.each(['crazyhouse', 'horde', 'seirawan', 'capablanca', 'duck', 'hoppelpoppel'])(
    'Random Dice result %s remains visible while creation uses the random modes',
    name => {
        expect(isRandomModeOrResultVariant(name)).toBe(true);
        expect(disabledVariantsForCreateMode('createGame', '', false)).toContain(name);
        expect(disabledVariantsForCreateMode('playFriend', '', false)).toContain(name);
    },
);

test.each(['duck', 'hoppelpoppel'])(
    'the extra Random Dice variant %s uses an 8x8 board',
    name => {
        expect(VARIANTS[name].board.dimensions).toEqual({ width: 8, height: 8 });
        expect(VARIANTS[name].rules.defaultTimeControl).toBe('incremental');
    },
);

test('Knightmate is available as a catalogued Random Dice result on an 8x8 board', () => {
    registerCataloguedVariant({
        name: 'knightmate',
        displayName: 'Knightmate',
        source: 'fairy-stockfish-builtin',
        fsfBuiltinVariant: 'knightmate',
        clientVariant: 'chess',
        ini: '',
        startFen: 'rmbqkbmr/pppppppp/8/8/8/8/PPPPPPPP/RMBQKBMR w KQkq - 0 1',
        width: 8,
        height: 8,
        pieces: ['p', 'm', 'b', 'r', 'q', 'k'],
        kingRoles: ['k'],
        promotionRoles: ['p'],
        promotionOrder: ['m', 'q', 'r', 'b'],
    });

    try {
        expect(isRandomModeOrResultVariant('knightmate')).toBe(true);
        expect(VARIANTS.knightmate.board.dimensions).toEqual({ width: 8, height: 8 });
        expect(VARIANTS.knightmate.rules.defaultTimeControl).toBe('incremental');
        expect(VARIANTS.knightmate.pieceRow.white).toContain('m-piece');
        expect(VARIANTS.knightmate.promotion.order).toContain('m');
    } finally {
        unregisterCataloguedVariant('knightmate');
    }
});

test('hidden info metadata is set for fogofwar', () => {
    expect(VARIANTS.fogofwar.hiddenInfo).toBe(true);
    expect(VARIANTS.fogofwar.hiddenInfoMode).toBe('fog');
});

test('hidden info metadata is set for jieqi', () => {
    expect(VARIANTS.jieqi.hiddenInfo).toBe(true);
    expect(VARIANTS.jieqi.hiddenInfoMode).toBe('covered_pieces');
});

test('hidden info metadata defaults to none for normal variants', () => {
    expect(VARIANTS.chess.hiddenInfo).toBe(false);
    expect(VARIANTS.chess.hiddenInfoMode).toBe('none');
});

test('only curated alternate starts can be rated', () => {
    expect(canRateStart(VARIANTS.chess, '')).toBe(true);
    expect(canRateCustomStart(VARIANTS.chess, VARIANTS.chess.alternateStart!['No castle'].fen)).toBe(true);
    expect(canRateCustomStart(VARIANTS.chess, VARIANTS.chess.alternateStart!.UpsideDown.fen)).toBe(false);
    expect(canRateCustomStart(VARIANTS.capablanca, VARIANTS.capablanca.alternateStart!.Gothic.fen)).toBe(true);
});

test('custom start rating check normalizes whitespace', () => {
    const noCastle = VARIANTS.chess.alternateStart!['No castle'].fen;
    expect(canRateCustomStart(VARIANTS.chess, `  ${noCastle.replaceAll(' ', '   ')}  `)).toBe(true);
});

test('Chess with Different Armies exposes every ordered non-FIDE matchup', () => {
    const starts = Object.values(VARIANTS.cwda.alternateStart!);

    expect(VARIANTS.cwda._displayName).toBe('cwda');
    expect(Object.keys(VARIANTS.cwda.alternateStart!)[0]).toBe('FIDE — Clobberers');
    expect(starts).toHaveLength(15);
    expect(new Set(starts.map(start => start.fen)).size).toBe(15);
    expect(starts.every(start => start.canRated)).toBe(true);
    expect(VARIANTS.cwda.ratingEnabled).toBe(false);
    expect(canRateStart(VARIANTS.cwda, '')).toBe(false);
    expect(canRateStart(VARIANTS.cwda, starts[0].fen)).toBe(false);
});

test('Chess with Different Armies remains DEV-only until approved', () => {
    expect(devVariants).toContain('cwda');
});

test('Chess with Different Armies resolves color reversals to one engine profile', () => {
    const normal = 'gihokhig/pppppppp/8/8/8/8/PPPPPPPP/DWACKAWD w KQkq - 0 1';
    const reversed = 'dwackawd/pppppppp/8/8/8/8/PPPPPPPP/GIHOKHIG w KQkq - 0 1';

    expect(cwdaEngineVariant(normal)).toBe('cwda-clobberers-knights');
    expect(cwdaEngineVariant(reversed)).toBe('cwda-clobberers-knights');
    expect(cwdaEngineVariant('')).toBe('cwda-fide-clobberers');
});

test('Chess with Different Armies identifies each side for army-specific artwork', () => {
    const fen = 'gihokhig/pppppppp/8/8/8/8/PPPPPPPP/DWACKAWD w KQkq - 0 1';

    expect(cwdaArmyClassNames(fen)).toEqual(['cwda-black-knights', 'cwda-white-clobberers']);
    expect(cwdaArmyClassNames('')).toEqual([]);
});
