import { expect, jest, test } from '@jest/globals';
import type { VNode } from 'snabbdom';

jest.unstable_mockModule('../client/main', () => ({ model: {} }));
jest.unstable_mockModule('chessgroundx', () => ({ Chessground: jest.fn() }));

const { LobbyController } = await import('../client/lobby');

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
