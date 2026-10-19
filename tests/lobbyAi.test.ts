import { expect, jest, test } from '@jest/globals';
import type { VNode } from 'snabbdom';
import type { PyChessModel } from '../client/types';

jest.unstable_mockModule('../client/main', () => ({ model: {} }));
jest.unstable_mockModule('chessgroundx', () => ({ Chessground: jest.fn() }));

const { LobbyController, lobbyView } = await import('../client/lobby');

test('the lobby exposes a Play with AI button that opens the AI dialog', () => {
    const ctrl = Object.create(LobbyController.prototype) as LobbyController;
    ctrl.playAI = jest.fn();

    const button = ctrl.renderSeekButtons()[2];
    const children = button.children as VNode[];

    expect(children[0].sel).toBe('span.icon.icon-bot');
    expect(children[0].data?.attrs?.['aria-hidden']).toBe('true');
    expect(children[2].text).toBe('Play with AI');
    button.data?.on?.click(new MouseEvent('click'), button);
    expect(ctrl.playAI).toHaveBeenCalledTimes(1);
});

test('the lobby retains normal game creation and the session score without a manual testing block', () => {
    const model = {
        username: 'tester', assetURL: '/static', anon: 'False',
        puzzle: JSON.stringify({ v: 'chess', f: '8/8/8/8/8/8/8/8 w - - 0 1' }),
        blogs: '[]', corrGames: '[]', timeline: '[]',
    } as PyChessModel;
    const selectors: string[] = [];
    const visit = (node: VNode) => {
        if (node.sel) selectors.push(node.sel);
        for (const child of node.children ?? []) if (child && typeof child === 'object') visit(child);
    };
    lobbyView(model).forEach(visit);
    expect(selectors).toContain('div.seekbuttons');
    expect(selectors).toContain('section#session-score.session-score');
    expect(selectors.some(selector => selector.includes('manual-test'))).toBe(false);
});
