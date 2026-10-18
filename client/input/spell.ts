import { h } from 'snabbdom';
import type { VNode } from 'snabbdom';
import type * as cg from 'chessgroundx/types';
import type { DrawShape } from 'chessgroundx/draw';
import type { GameController } from '@/gameCtrl';
import { patch } from '@/document';
import { _ } from '@/i18n';
import { readSpellState, spellPieceMoves, spellTargets } from '@/spellChess';
import type { Spell, SpellCast } from '@/spellChess';

export class SpellInput {
    targeting?: Spell;
    cast?: SpellCast;
    private fen = '';
    private controls: HTMLElement | VNode;
    private opponent: HTMLElement | VNode;

    constructor(private readonly ctrl: GameController) {
        this.controls = this.mount('.pocket-bot', 'spell-controls');
        this.opponent = this.mount('.pocket-top', 'spell-opponent');
    }

    private mount(parent: string, id: string): HTMLElement {
        const el = document.createElement('div');
        el.id = id;
        document.querySelector(parent)?.appendChild(el);
        return el;
    }

    reset(): void {
        this.targeting = undefined;
        this.cast = undefined;
    }

    private canPlay(): boolean {
        return this.ctrl.canUseSpells();
    }

    private rawMoves(): string[] {
        return this.ctrl.ffishBoard.legalMoves().split(' ').filter(Boolean);
    }

    pieceMoves(moves: string[]): string[] {
        return this.targeting ? [] : spellPieceMoves(moves, this.cast);
    }

    select(key: cg.Key): boolean {
        if (!this.targeting) return false;
        if (this.canPlay() && spellTargets(this.rawMoves(), this.targeting).includes(key)) {
            this.cast = { spell: this.targeting, square: key };
            this.targeting = undefined;
            this.ctrl.chessground.unselect();
            this.ctrl.setDests();
        }
        return true;
    }

    complete(move: string): string {
        const compound = this.cast ? `${this.cast.spell}@${this.cast.square},${move}` : move;
        this.reset();
        return compound;
    }

    private begin(spell: Spell): void {
        if (!this.canPlay()) return;
        this.cast = undefined;
        this.targeting = this.targeting === spell ? undefined : spell;
        this.ctrl.chessground.unselect();
        this.ctrl.setDests();
    }

    private cancel(): void {
        this.reset();
        this.ctrl.chessground.unselect();
        this.ctrl.setDests();
    }

    sync(): void {
        if (this.fen !== this.ctrl.fullfen) {
            this.reset();
            this.fen = this.ctrl.fullfen;
        }
        const state = readSpellState(this.ctrl.fullfen);
        const color = this.ctrl.spellColor();
        const other = color === 'white' ? 'black' : 'white';
        const moves = this.rawMoves();
        const label = (spell: Spell) => spell === 'f' ? _('Freeze') : _('Jump');
        const icon = (spell: Spell, side: cg.Color) => h('img.spell-potion', {
            attrs: { src: `${this.ctrl.home}/static/images/pieces/spellchess/merida/${side === 'white' ? 'w' : 'b'}${spell.toUpperCase()}.svg`, alt: '' },
        });
        this.controls = patch(this.controls, h('div#spell-controls.spell-controls', [
            ...(['f', 'j'] as const).map(spell => h('button.spell-button', {
                attrs: { 'aria-pressed': this.targeting === spell || this.cast?.spell === spell ? 'true' : 'false' },
                props: {
                    type: 'button', title: state.cooldowns[color][spell]
                        ? `${label(spell)} (${state.cooldowns[color][spell]})` : label(spell),
                    disabled: !this.canPlay() || !spellTargets(moves, spell).length,
                },
                on: { click: () => this.begin(spell) },
            }, [icon(spell, color), h('span', label(spell)), h('strong', `${state.reserves[color][spell]}`),
                state.cooldowns[color][spell] ? h('span.spell-cooldown', `${state.cooldowns[color][spell]}`) : ''])),
            h('button.spell-cancel', {
                props: { type: 'button', title: _('Cancel spell'), disabled: !this.targeting && !this.cast },
                on: { click: () => this.cancel() },
            }, [h('i.icon.icon-reply', { attrs: { 'aria-label': _('Cancel spell') } })]),
        ]));
        this.opponent = patch(this.opponent, h('div#spell-opponent.spell-reserves',
            (['f', 'j'] as const).map(spell => h('span', { props: { title: label(spell) } }, [
                icon(spell, other), h('strong', `${state.reserves[other][spell]}`),
                state.cooldowns[other][spell] ? h('span.spell-cooldown', `${state.cooldowns[other][spell]}`) : '',
            ]))));
        const shapes: DrawShape[] = state.zones.map(zone => ({
            orig: zone.square, brush: zone.spell === 'f' ? 'blue' : 'green',
        }));
        if (this.cast) shapes.push({ orig: this.cast.square, brush: 'yellow' });
        this.ctrl.chessground.set({
            autoCastle: false,
            draggable: { enabled: !this.targeting },
            premovable: { enabled: false },
            drawable: { autoShapes: shapes },
        });
        document.querySelector('#mainboard')?.classList.toggle('spell-targeting', !!this.targeting);
    }
}
