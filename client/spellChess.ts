import type * as cg from 'chessgroundx/types';

export type Spell = 'f' | 'j';
export type SpellCast = { spell: Spell; square: cg.Key };
export type SpellState = {
    reserves: Record<cg.Color, Record<Spell, number>>;
    cooldowns: Record<cg.Color, Record<Spell, number>>;
    zones: (SpellCast & { color: cg.Color })[];
};

export function splitSpellMove(move: string): { move: string; cast?: SpellCast } {
    const match = /^([fj])@([a-h][1-8]),(.+)$/.exec(move);
    return match
        ? { move: match[3], cast: { spell: match[1] as Spell, square: match[2] as cg.Key } }
        : { move };
}

export function fsxMoveSan(variant: string, move: string, san: string): string {
    if (variant === 'monster' && move === '0000') return '--';
    const cast = splitSpellMove(move).cast;
    return variant === 'spell-chess' && cast
        ? `${cast.spell}@${cast.square},${san.replace(/\/[FJ](?=[+#]*$)/, '')}`
        : san;
}

export function spellPieceMoves(moves: readonly string[], cast?: SpellCast): string[] {
    const prefix = cast ? `${cast.spell}@${cast.square},` : undefined;
    return moves.filter(move => prefix ? move.startsWith(prefix) : !splitSpellMove(move).cast)
        .map(move => splitSpellMove(move).move);
}

export function spellTargets(moves: readonly string[], spell: Spell): cg.Key[] {
    return [...new Set(moves.flatMap(move => {
        const cast = splitSpellMove(move).cast;
        return cast?.spell === spell ? [cast.square] : [];
    }))];
}

export function readSpellState(fen: string): SpellState {
    const fields = fen.split(/\s+/);
    const pocket = /\[([^\]]*)\]/.exec(fields[0])?.[1] ?? '';
    const tail = fields.slice(6).join(' ');
    const cooldown = /<(\d+)\s+(\d+)\s+(\d+)\s+(\d+)>/.exec(tail);
    const count = (letter: string) => [...pocket].filter(piece => piece === letter).length;
    const zones: SpellState['zones'] = [];
    for (const match of tail.matchAll(/(?:\b([wb]))?([fj]):([a-h][1-8])/g)) {
        zones.push({
            color: (match[1] ?? fields[1]) === 'b' ? 'black' : 'white',
            spell: match[2] as Spell,
            square: match[3] as cg.Key,
        });
    }
    return {
        reserves: { white: { f: count('F'), j: count('J') }, black: { f: count('f'), j: count('j') } },
        cooldowns: {
            white: { f: Number(cooldown?.[1] ?? 0), j: Number(cooldown?.[2] ?? 0) },
            black: { f: Number(cooldown?.[3] ?? 0), j: Number(cooldown?.[4] ?? 0) },
        },
        zones,
    };
}
