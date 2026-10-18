import { h, VNode } from 'snabbdom';
import { _ } from '../i18n';
import { VARIANTS } from '../variants';

export const MANUAL_TEST_VARIANTS = ['monster', 'rifle-chess', 'spell-chess'] as const;

export function manualTestsView(start: (variant: string, color: string, minutes: number, increment: number) => void): VNode {
    let color = 'w';
    return h('section.manual-tests', [
        h('h3', _('Tests') + ' / Random-Mover'),
        h('div.manual-test-settings', [
            h('fieldset.manual-test-colors', [h('legend', _('Color')),
                ...[['w', _('White')], ['r', _('Random')], ['b', _('Black')]].map(([value, label]) => h('label', [
                    h('input', { props: { type: 'radio', name: 'test-color', value, checked: value === color },
                        on: { change: () => { color = value; } } }), h('span', label),
                ])),
            ]),
            h('label', [_('Minutes'), h('input#test-minutes', { props: { type: 'number', min: 1, max: 180, value: 5 } })]),
            h('label', [_('Increment'), h('input#test-increment', { props: { type: 'number', min: 0, max: 60, value: 3 } })]),
        ]),
        ...MANUAL_TEST_VARIANTS.map(key => h('button.manual-test-start', {
            attrs: { type: 'button', 'data-variant': key },
            on: { click: () => {
                const minutes = document.getElementById('test-minutes') as HTMLInputElement;
                const increment = document.getElementById('test-increment') as HTMLInputElement;
                if (!minutes.reportValidity() || !increment.reportValidity()) return;
                start(key, color, Number(minutes.value), Number(increment.value));
            } },
        }, [h('span', { attrs: { 'data-icon': VARIANTS[key].icon(false), 'aria-hidden': 'true' } }),
            h('span', VARIANTS[key].displayName(false)), h('i.icon.icon-bot', { attrs: { 'aria-hidden': 'true' } })])),
    ]);
}
