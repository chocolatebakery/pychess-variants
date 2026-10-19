import { beforeEach, expect, test } from '@jest/globals';
import { clearSessionScores, recordSessionResult, refreshSessionScore, sessionScores, sessionScoreKey, trackSessionGame } from '../client/sessionScore';

beforeEach(() => sessionStorage.clear());

test('records white and black results by actual variant, once across reloads', () => {
    trackSessionGame('p', 'a', 'monster', false);
    expect(recordSessionResult('p', 'a', 2, '1-0', 'white')).toBe(true);
    trackSessionGame('p', 'a', 'monster', false);
    expect(recordSessionResult('p', 'a', 2, '1-0', 'white')).toBe(false);
    trackSessionGame('p', 'b', 'monster', false);
    recordSessionResult('p', 'b', 2, '1-0', 'black');
    trackSessionGame('p', 'c', 'monster', false);
    recordSessionResult('p', 'c', 5, '1/2-1/2', 'black');
    expect(sessionScores('p')).toEqual([{ variant: 'monster', win: 1, draw: 1, loss: 1 }]);
    expect(sessionScores('other')).toEqual([]);
});

test('separates Chess960, ignores archives, unfinished, aborted and invalid games', () => {
    expect(recordSessionResult('p', 'archive', 2, '1-0', 'white')).toBe(false);
    trackSessionGame('p', 'live', 'chess', true);
    for (const [status, result] of [[-1, '*'], [0, '*'], [10, '1-0']] as const)
        expect(recordSessionResult('p', 'live', status, result, 'white')).toBe(false);
    recordSessionResult('p', 'live', 2, '0-1', 'black');
    expect(sessionScores('p')).toEqual([{ variant: 'chess960', win: 1, draw: 0, loss: 0 }]);
});

test('reset does not count old results again, but live/new games still count', () => {
    trackSessionGame('p', 'old', 'rifle-chess', false);
    recordSessionResult('p', 'old', 2, '1-0', 'white');
    trackSessionGame('p', 'live', 'spell-chess', false);
    clearSessionScores('p');
    expect(sessionScores('p')).toEqual([]);
    expect(recordSessionResult('p', 'old', 2, '1-0', 'white')).toBe(false);
    recordSessionResult('p', 'live', 2, '0-1', 'black');
    expect(sessionScores('p')).toEqual([{ variant: 'spell-chess', win: 1, draw: 0, loss: 0 }]);
});

test('invalid stored state cannot break game rendering', () => {
    for (const value of ['bad json', 'null', '[]', '{"a":{"variant":"missing","outcome":"win"}}']) {
        sessionStorage.setItem(sessionScoreKey('p'), value);
        expect(sessionScores('p')).toEqual([]);
    }
});

test('scoreboard updates replace existing rows instead of duplicating them', () => {
    document.body.innerHTML = '<section id="session-score"><header>Old score</header><table></table></section>';
    trackSessionGame('p', 'a', 'monster', false);
    recordSessionResult('p', 'a', 2, '1-0', 'white');
    refreshSessionScore('p');
    refreshSessionScore('p');
    expect(document.querySelectorAll('#session-score table')).toHaveLength(1);
    expect(document.querySelectorAll('#session-score tbody tr')).toHaveLength(1);
    clearSessionScores('p');
    refreshSessionScore('p');
    expect(document.querySelectorAll('#session-score table')).toHaveLength(1);
    expect(document.querySelectorAll('#session-score tbody tr')).toHaveLength(0);
});
