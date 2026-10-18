import { h, VNode } from 'snabbdom';
import { patch } from './document';
import { _ } from './i18n';
import { VARIANTS, variantKey } from './variants';
import { confirmDialog } from './confirmDialog';

type Outcome = 'win' | 'draw' | 'loss';
interface SessionGame { variant: string; outcome?: Outcome; hidden?: boolean }
type SessionGames = Record<string, SessionGame>;
export interface VariantScore { variant: string; win: number; draw: number; loss: number }

export const sessionScoreKey = (username: string) => `session-score:v1:${username}`;

function readGames(username: string): SessionGames {
    try {
        const data: unknown = JSON.parse(sessionStorage.getItem(sessionScoreKey(username)) ?? '{}');
        if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
        return Object.fromEntries(Object.entries(data).filter(([, game]) =>
            game && typeof game.variant === 'string' && VARIANTS[game.variant.replace(/960$/, '')] &&
            (game.outcome === undefined || ['win', 'draw', 'loss'].includes(game.outcome)),
        ));
    } catch {
        return {};
    }
}

function writeGames(username: string, games: SessionGames) {
    try { sessionStorage.setItem(sessionScoreKey(username), JSON.stringify(games)); } catch { /* Storage may be disabled. */ }
}

export function trackSessionGame(username: string, gameId: string, variant: string, chess960: boolean) {
    const games = readGames(username);
    if (!games[gameId]) {
        games[gameId] = { variant: variantKey(variant, chess960) };
        writeGames(username, games);
    }
}

export function recordSessionResult(username: string, gameId: string, status: number, result: string, color: string): boolean {
    const games = readGames(username);
    const game = games[gameId];
    // Only games joined live in this tab count; archives, aborts and engine errors do not.
    if (!game || game.outcome || status <= 0 || status === 10 || !['1-0', '0-1', '1/2-1/2'].includes(result)) return false;
    game.outcome = result === '1/2-1/2' ? 'draw' :
        ((result === '1-0') === (color === 'white') ? 'win' : 'loss');
    writeGames(username, games);
    return true;
}

export function sessionScores(username: string): VariantScore[] {
    const scores = new Map<string, VariantScore>();
    for (const game of Object.values(readGames(username))) {
        if (!game.outcome || game.hidden) continue;
        const score = scores.get(game.variant) ?? { variant: game.variant, win: 0, draw: 0, loss: 0 };
        score[game.outcome]++;
        scores.set(game.variant, score);
    }
    return [...scores.values()].sort((a, b) => a.variant.localeCompare(b.variant));
}

export function clearSessionScores(username: string) {
    const games = readGames(username);
    // Retain completed IDs so revisiting a game cannot count it again after reset.
    for (const game of Object.values(games)) if (game.outcome) game.hidden = true;
    writeGames(username, games);
}

export function refreshSessionScore(username: string) {
    const el = document.getElementById('session-score');
    if (el) {
        el.replaceChildren();
        patch(el, sessionScoreView(username));
    }
}

export function sessionScoreView(username: string): VNode {
    const scores = sessionScores(username);
    const total = scores.reduce((sum, score) => ({ win: sum.win + score.win, draw: sum.draw + score.draw, loss: sum.loss + score.loss }),
        { win: 0, draw: 0, loss: 0 });
    const cells = (score: { win: number; draw: number; loss: number }) => [h('td', String(score.win)), h('td', String(score.draw)), h('td', String(score.loss))];
    return h('section#session-score.session-score', [
        h('header', [h('h3', _('Session score')), h('button.icon.icon-trash-o', {
            attrs: { type: 'button', title: _('Clear session score'), 'aria-label': _('Clear session score'), disabled: scores.length === 0 },
            on: { click: async () => {
                if (await confirmDialog({ text: _('Clear session score?'), confirmText: _('Clear'), cancelText: _('Cancel') })) {
                    clearSessionScores(username);
                    refreshSessionScore(username);
                }
            } },
        })]),
        h('table', [
            h('thead', [h('tr', [h('th', _('Variant')), h('th', _('You')), h('th', _('Draws')),
                h('th', [h('abbr', { attrs: { title: _('Opponent') } }, _('Opp.'))])])]),
            h('tbody', scores.map(score => {
                const variant = VARIANTS[score.variant.replace(/960$/, '')];
                return h('tr', [h('th', variant.displayName(false) + (score.variant.endsWith('960') ? ' 960' : '')), ...cells(score)]);
            })),
            h('tfoot', [h('tr', [h('th', _('Total')), ...cells(total)])]),
        ]),
    ]);
}
