import { expect, test } from '@jest/globals';
import { readFileSync } from 'node:fs';
import postcss from 'postcss';

import { SVG_VARIANT_ICONS, VARIANTS } from '../client/variants';

const icons = {
    knightmate: 'knightmate', atomar: 'atomar', berolina: 'berolina', extinction: 'extinction',
    kinglet: 'kinglet', threekings: 'threekings', torpedo: 'torpedo', losers: 'losers',
    'rifle-chess': 'riflechess', 'spell-chess': 'spellchess', brotherhood: 'brotherhood', randomdice: 'randomdice', monster: 'monster', cylinder: 'cylinder',
};

test('supplied variant logos have unique SVG mask keys and valid local assets', () => {
    const stylesheet = postcss.parse(readFileSync('static/random-icons.css', 'utf8'));
    expect(new Set(Object.values(SVG_VARIANT_ICONS)).size).toBe(Object.keys(icons).length);
    for (const [variant, filename] of Object.entries(icons)) {
        const icon = SVG_VARIANT_ICONS[variant];
        expect(icon).toHaveLength(1);
        const selector = `[data-icon="\\${icon.codePointAt(0)!.toString(16)}"]`;
        const values: string[] = [];
        stylesheet.walkRules(selector, rule => {
            rule.walkDecls('--variant-icon', declaration => { values.push(declaration.value); });
        });
        expect(values).toEqual([`url('icons/${filename}.svg')`]);
        const svg = readFileSync(`static/icons/${filename}.svg`, 'utf8');
        const document = new DOMParser().parseFromString(svg, 'image/svg+xml');
        expect(document.querySelector('parsererror')).toBeNull();
        expect(document.documentElement.localName).toBe('svg');
    }
    expect(VARIANTS.randomdice.icon()).toBe(SVG_VARIANT_ICONS.randomdice);
    expect(VARIANTS.losers.icon()).toBe(SVG_VARIANT_ICONS.losers);
    expect(VARIANTS.seirawan.icon()).not.toBe(SVG_VARIANT_ICONS.losers);
});

test.each([
    ['knightmate', 'standard', 12], ['berolina', 'merida', 12], ['spellchess', 'merida', 16],
] as const)('%s includes every source SVG in its generated piece CSS', (family, style, count) => {
    const source = postcss.parse(readFileSync(`static/piece/${family}/${style}.css`, 'utf8'));
    const generated = postcss.parse(readFileSync(`static/piece-css/${family}/${style}.css`, 'utf8'));
    const images: string[] = [];
    generated.walkDecls('background-image', declaration => { images.push(declaration.value); });
    expect(images).toHaveLength(count);
    let checked = 0;
    source.walkDecls('background-image', declaration => {
        const prefix = "url('../../";
        expect(declaration.value.startsWith(prefix)).toBe(true);
        const filename = `static/${declaration.value.slice(prefix.length, -2)}`;
        const svg = readFileSync(filename, 'utf8');
        expect(new DOMParser().parseFromString(svg, 'image/svg+xml').querySelector('parsererror')).toBeNull();
        expect(images).toContain(`url('data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}')`);
        checked++;
    });
    expect(checked).toBe(count);
});

test('Knightmate keeps the royal knight and commoner king appearances', () => {
    const css = postcss.parse(readFileSync('static/piece/knightmate/standard.css', 'utf8'));
    for (const [color, prefix] of [['white', 'w'], ['black', 'b']]) {
        const images: Record<string, string> = {};
        for (const role of ['k', 'm']) {
            css.walkRules(`.knightmate piece.${role}-piece.${color}`, rule => {
                rule.walkDecls('background-image', declaration => { images[role] = declaration.value; });
            });
        }
        expect(images.k).toBe(`url('../../images/pieces/knightmate/merida/${prefix}N.svg')`);
        expect(images.m).toBe(`url('../../images/pieces/merida/${prefix}K.svg')`);
    }
});
