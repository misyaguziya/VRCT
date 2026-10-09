import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import { VrWindow } from './VrWindow';
import settingsStyles from './VrSettingsWindow.module.scss';
import LanguageSvg from '@images/mui_language.svg?react';
import XMarkSvg from '@images/x_mark.svg?react';
import WarningSvg from '@images/warning.svg?react';
import { useLanguageSettings } from '@logics_main';
import { useI18n } from '@useI18n';
import { useIsOpenedConfigPage } from '@logics_common';
import { LANGUAGE_RESPONSE_WAIT_MS } from '../../logics/main/languageMutations';
import styles from './VrLanguageWindow.module.scss';

const keys = ['1', '2', '3'];
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
const same = (a, b) => a?.language === b?.language && a?.country === b?.country;
const unique = entries => entries.filter((entry, index) => entries.findIndex(other => same(entry, other)) === index);
const engineLabel = engine => engine?.label?.replace('\n', ' ') ?? '';

// Shares the confirmed settings components; language changes wait for their final backend response.
export function VrLanguageWindow({ onClose }) {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const c = (key, variables) => t(key === 'busy' ? 'vr_panel.settings.changing' : `vr_panel.language.${key}`, variables);
    const settings = useLanguageSettings();
    const { currentSelectedPresetTabNumber: tab, currentSelectedYourLanguages: your, currentSelectedTargetLanguages: target,
        currentSelectedTranslationEngines: selectedEngines, currentTranslationEngines: engines, currentSelectableLanguageList: selectable, currentLanguageMutation: mutation } = settings;
    const preset = tab.data;
    const source = your.data?.[preset]?.[1];
    const targetSlots = target.data?.[preset];
    const targets = keys.filter(key => targetSlots?.[key]?.enable).map(key => targetSlots[key]);
    const ready = Boolean(source && targetSlots && Array.isArray(selectable.data));
    const [waiting, setWaiting] = useState(false);
    const [unconfirmed, setUnconfirmed] = useState(false);
    const syncError = !mutation.data.inFlight && !mutation.data.isResyncing && [tab, your, target, selectedEngines, engines].some(store => store.state === 'error');
    const busy = waiting || Boolean(mutation.data.inFlight) || mutation.data.isResyncing || [tab, your, target, selectedEngines, engines].some(store => store.state !== 'ok');
    const locked = currentIsOpenedConfigPage.data === true;
    const selectedEngine = engines.data.find(engine => engine.id === selectedEngines.data?.[preset]);
    const sameLanguage = targets.some(entry => entry.language === source?.language);
    const duplicates = unique(targets).length !== targets.length;
    const [view, setView] = useState({ kind: 'main' });
    const [notice, setNotice] = useState(null);
    const [error, setError] = useState(false);
    const [unavailableOpen, setUnavailableOpen] = useState(!selectedEngine?.is_available);
    const previousPreset = useRef(preset);
    const previousView = useRef('main///');
    const action = useRef(null);
    const origin = useRef('your');
    const mainButtons = useRef({});
    const backButton = useRef(null);
    const mainBody = useRef(null);
    const mainScroll = useRef(0);
    const pickerSnapshot = useRef(null);
    const recoveringOwnChange = useRef(false);
    const currentPickerSnapshot = JSON.stringify({ source, targets });
    const viewKey = `${view.kind}/${view.stage ?? ''}/${view.letter ?? ''}/${view.index ?? ''}/${preset}`;
    const waitTimer = useRef(null);
    const retryButton = useRef(null);
    const errorFocus = useRef(null);
    useEffect(() => () => clearTimeout(waitTimer.current), []);

    useEffect(() => {
        if (previousPreset.current === preset) return;
        previousPreset.current = preset;
        const ownPresetChange = action.current?.nextPreset === preset;
        if (!ownPresetChange) {
            recoveringOwnChange.current = false;
            action.current = null;
            clearTimeout(waitTimer.current);
            setWaiting(false);
            setUnconfirmed(false);
            setNotice({ key: 'external', n: preset });
        }
        setView({ kind: 'main' });
        setError(false);
        origin.current = `preset:${preset}`;
    }, [preset]);
    useEffect(() => {
        const accepted = action.current;
        const response = mutation.data.lastVrResult;
        if (!accepted || response?.requestId !== accepted.id) return;
        if (response.kind === 'unconfirmed') { setUnconfirmed(true); return; }
        action.current = null;
        pickerSnapshot.current = currentPickerSnapshot;
        clearTimeout(waitTimer.current);
        setWaiting(false);
        setUnconfirmed(false);
        if (accepted.preset !== preset && accepted.nextPreset !== preset) return;
        if (response.kind !== 'success') {
            recoveringOwnChange.current = true;
            errorFocus.current = accepted.trigger;
            setError(true);
            setNotice(null);
            return;
        }
        setError(false);
        setNotice({ key: 'success' });
        if (accepted.returnToMain) setView({ kind: 'main' });
        else if (accepted.focusKey) mainButtons.current[accepted.focusKey]?.focus({ preventScroll: true });
    }, [mutation.data.lastVrResult, preset]);
    useLayoutEffect(() => {
        if (busy || !error || !errorFocus.current) return;
        const trigger = errorFocus.current;
        errorFocus.current = null;
        (trigger.isConnected && !trigger.matches(':disabled') ? trigger : backButton.current ?? mainButtons.current.your)?.focus({ preventScroll: true });
    }, [busy, error]);
    useLayoutEffect(() => {
        if (syncError) retryButton.current?.focus({ preventScroll: true });
    }, [syncError]);
    useLayoutEffect(() => {
        if (recoveringOwnChange.current) {
            if (busy) return;
            pickerSnapshot.current = currentPickerSnapshot;
            recoveringOwnChange.current = false;
            return;
        }
        if (view.kind === 'main' || action.current || pickerSnapshot.current === currentPickerSnapshot) return;
        // An index is meaningful only while the source/target rows being edited
        // have not changed externally. Never apply it to a shifted list.
        pickerSnapshot.current = currentPickerSnapshot;
        setView({ kind: 'main' });
        setError(false);
        setNotice({ key: 'settings_updated' });
    }, [currentPickerSnapshot, view.kind, busy]);
    useLayoutEffect(() => {
        if (previousView.current === viewKey) return;
        previousView.current = viewKey;
        if (view.kind === 'main') {
            if (mainBody.current) mainBody.current.scrollTop = mainScroll.current;
            const preferred = mainButtons.current[origin.current];
            const fallback = origin.current === 'add' ? mainButtons.current[`target:${targets.length - 1}`] : mainButtons.current.your;
            (preferred && !preferred.matches(':disabled') ? preferred : fallback)?.focus({ preventScroll: true });
        } else {
            backButton.current?.focus({ preventScroll: true });
        }
    }, [viewKey, view.kind]);
    useEffect(() => {
        if (selectedEngine && !selectedEngine.is_available) setUnavailableOpen(true);
    }, [selectedEngine?.id, selectedEngine?.is_available]);

    const mainRef = name => element => { mainButtons.current[name] = element; };
    const open = (next, name) => {
        if (busy || locked || !ready) return;
        origin.current = name;
        mainScroll.current = mainBody.current?.scrollTop ?? 0;
        pickerSnapshot.current = currentPickerSnapshot;
        setNotice(null);
        setError(false);
        setView(next);
    };
    const save = (perform, { returnToMain = false, focusKey, nextPreset } = {}) => {
        if (action.current || busy || locked || !ready) return;
        action.current = { preset, returnToMain, focusKey, nextPreset, trigger: document.activeElement };
        setWaiting(true);
        setUnconfirmed(false);
        setError(false);
        setNotice(null);
        action.current.id = perform();
        if (!action.current.id) {
            action.current = null;
            setWaiting(false);
            setError(true);
            return;
        }
        clearTimeout(waitTimer.current);
        waitTimer.current = setTimeout(() => setUnconfirmed(true), LANGUAGE_RESPONSE_WAIT_MS);
    };
    const back = () => {
        if (busy) return;
        setError(false);
        if (view.stage === 'list') setView({ ...view, stage: 'letters', letter: undefined });
        else if (view.stage === 'letters') setView({ ...view, stage: 'saved' });
        else setView({ kind: 'main' });
    };
    const remove = index => save(() => settings.setTargetLanguagesInOrder(targets.filter((_, position) => position !== index)), { focusKey: `target:${Math.min(index, targets.length - 2)}` });
    const choose = entry => {
        if (busy) return;
        if (view.kind === 'your') {
            if (same(source, entry)) return;
            save(() => settings.setSelectedYourLanguages(entry), { returnToMain: true });
        } else if (!targets.some(other => same(other, entry))) {
            if (view.kind === 'target-replace' && !targets[view.index]) return;
            const next = view.kind === 'target-add' ? [...targets, entry] : targets.map((old, index) => index === view.index ? entry : old);
            if (next.length > 3) return;
            save(() => settings.setTargetLanguagesInOrder(next), { returnToMain: true });
        }
    };
    const saved = ready ? unique(['1', '2', '3'].flatMap(number => [your.data[number]?.[1], ...keys.map(key => target.data[number]?.[key])])
        .filter(entry => entry && selectable.data.some(option => same(entry, option)))) : [];
    for (const entry of [source, ...targets]) {
        if (entry?.language && !saved.some(other => same(entry, other))) saved.push(entry);
    }
    const title = view.kind === 'your' ? c('edit_your') : view.kind === 'target-add' ? c('add_title') : view.kind === 'target-replace' ? c('change_target', { n: view.index + 1 }) : t('main_page.translator');
    const status = syncError ? c('sync_error') : unconfirmed || mutation.data.inFlight?.kind === 'unconfirmed' ? c('unconfirmed') : busy ? c('busy') : error ? c('error') : notice ? c(notice.key, { n: notice.n }) : '';
    const languageSelected = entry => view.kind === 'your' ? same(entry, source) : targets.some(other => same(other, entry));
    const selectionLabel = entry => view.kind === 'your' ? c('selected') : c('selected_slots', { n: targets.flatMap((other, index) => same(other, entry) ? [index + 1] : []).join(', ') });
    const languageChoices = view.stage === 'list' ? (selectable.data ?? []).filter(entry => entry.language[0].toUpperCase() === view.letter) : saved;
    useLayoutEffect(() => {
        // Feedback reduces the list height. Keep a focused choice visible without
        // moving the window or the main screen's remembered scroll position.
        const focused = document.activeElement;
        const list = focused?.closest(`.${styles.picker_scroll}`);
        if (!list) return;
        const row = focused.getBoundingClientRect();
        const bounds = list.getBoundingClientRect();
        const scale = list.clientHeight / bounds.height;
        if (row.bottom > bounds.bottom) list.scrollTop += (row.bottom - bounds.bottom) * scale;
        else if (row.top < bounds.top) list.scrollTop -= (bounds.top - row.top) * scale;
    }, [status, busy, viewKey]);

    return <VrWindow Icon={LanguageSvg} title={t('vr_panel.window_language')} onClose={onClose}>
        <div className={clsx(settingsStyles.window_body, styles.language_window)} data-vr-language="" onKeyDown={event => {
            if (event.key === 'Escape' && view.kind !== 'main' && !busy && !locked) { event.preventDefault(); back(); }
        }}>
            <span className={styles.sr_only} role="status" aria-atomic="true">{syncError ? c('sync_error') : !ready ? c('sync') : status || c('selected_count', { n: targets.length })}</span>
            {syncError && <button ref={retryButton} className={clsx(settingsStyles.button, styles.retry)} disabled={locked} onClick={() => settings.refreshLanguageSettings()}>{c('retry_sync')}</button>}
            {!ready && <div className={styles.waiting} aria-busy={!syncError}><p>{c(syncError ? 'sync_error' : 'sync')}</p></div>}
            <fieldset className={styles.main} ref={mainBody} hidden={!ready || view.kind !== 'main'} disabled={!ready || locked || syncError} aria-busy={busy && !syncError}>
                <div className={styles.presets}>
                    <span className={clsx(settingsStyles.label, styles.preset_label)}>{c('preset_number', { n: preset })}</span>
                    <div className={settingsStyles.segment}>{['1', '2', '3'].map(number => <button key={number} ref={mainRef(`preset:${number}`)}
                        className={clsx(settingsStyles.button, styles.preset, number === preset && settingsStyles.is_on)} aria-label={c('preset_number', { n: number })} aria-pressed={number === preset} aria-disabled={busy ? true : undefined}
                        onClick={() => number !== preset && save(() => settings.setSelectedPresetTabNumber(number), { nextPreset: number, focusKey: `preset:${number}` })}>{number}</button>)}</div>
                    {status && <span className={`${styles.status} ${error || syncError ? styles.error : ''}`}>{status}</span>}
                </div>
                <div className={styles.source_row}>
                    <button className={clsx(settingsStyles.row, settingsStyles.clickable, settingsStyles.select, styles.source)} ref={mainRef('your')} aria-disabled={busy ? true : undefined} onClick={() => open({ kind: 'your', stage: 'saved' }, 'your')}>
                        <span className={settingsStyles.label}>{t('main_page.your_language')}</span><LanguageText entry={source} className={styles.selected_value} /><span className={settingsStyles.chevron} aria-hidden="true">›</span>
                    </button>
                    <button className={clsx(settingsStyles.button, styles.swap)} ref={mainRef('swap')} aria-label={c('swap_name')} aria-disabled={busy ? true : undefined}
                        onClick={() => save(() => settings.swapSelectedLanguages())}><span>{c('swap')}</span><span className={styles.country}>{c('swap_hint')}</span></button>
                </div>
                <section className={styles.targets}>
                    <div className={styles.target_heading}><h2 className={settingsStyles.section_label}>{t('main_page.target_language')}<span>{c('range')}</span></h2><span className={styles.count}>{targets.length} / 3{duplicates && <span> · {c('duplicate')}</span>}</span></div>
                    <div className={styles.selected_rows}>{targets.map((entry, index) => <div className={clsx(settingsStyles.row, styles.target_row)} key={index}>
                        <button className={styles.target_change} ref={mainRef(`target:${index}`)} aria-label={`${c('change_target', { n: index + 1 })}: ${entry.language} / ${entry.country}`} aria-disabled={busy ? true : undefined}
                            onClick={() => open({ kind: 'target-replace', index, stage: 'saved' }, `target:${index}`)}>
                            <span className={styles.order}>{index + 1}</span><LanguageText entry={entry} /><span className={settingsStyles.chevron} aria-hidden="true">›</span>
                        </button>
                        <button className={clsx(settingsStyles.button, styles.remove)} disabled={targets.length === 1} aria-disabled={busy && targets.length > 1 ? true : undefined}
                            aria-label={targets.length === 1 ? c('min_reason') : c('remove', { n: index + 1, language: entry.language, country: entry.country })}
                            onClick={() => targets.length > 1 && remove(index)}>{targets.length === 1 ? <span>{c('required')}</span> : <XMarkSvg aria-hidden="true" />}</button>
                    </div>)}</div>
                    {targets.length >= 3 ? <p className={styles.limit}>{c('full')}</p> : <button className={clsx(settingsStyles.button, styles.add)} ref={mainRef('add')} aria-disabled={busy ? true : undefined}
                        onClick={() => open({ kind: 'target-add', stage: 'saved' }, 'add')}><span aria-hidden="true">＋</span>{c('add')}</button>}
                </section>
                <button className={clsx(settingsStyles.row, settingsStyles.clickable, settingsStyles.select)} ref={mainRef('engine')} aria-disabled={busy ? true : undefined} onClick={() => open({ kind: 'engine' }, 'engine')}>
                    <span className={settingsStyles.label}>{t('main_page.translator')}{(sameLanguage || !selectedEngine?.is_available) && <span className={styles.engine_note}><WarningSvg aria-hidden="true" />{sameLanguage ? c('same_short') : c('unavailable')}</span>}</span>
                    <span className={settingsStyles.select_value}>{engineLabel(selectedEngine)}</span><span className={settingsStyles.chevron} aria-hidden="true">›</span>
                </button>
            </fieldset>
            {ready && view.kind !== 'main' && <fieldset className={styles.picker} disabled={locked || syncError} aria-busy={busy && !syncError}>
                <div className={settingsStyles.picker_head}>
                    <button className={clsx(settingsStyles.button, settingsStyles.back)} ref={backButton} aria-disabled={busy ? true : undefined} onClick={() => !locked && back()}>‹ {t('common.go_back_button_label')}</button>
                    <div className={clsx(settingsStyles.picker_title, styles.context)}><span>{c('preset_number', { n: preset })}</span><h2>{title}</h2></div>
                </div>
                {status && <p className={`${styles.feedback} ${error || syncError ? styles.error : ''}`}>{status}{busy && !syncError && <span> {c('busy_hint')}</span>}</p>}
                <div className={styles.picker_scroll}>
                    {view.kind === 'engine' ? <>
                        {sameLanguage && <p className={styles.warning}><WarningSvg aria-hidden="true" />{c('same_reason')}</p>}
                        <h3 className={settingsStyles.section_label}>{c('available')}</h3>
                        <div className={styles.choice_grid}>{engines.data.filter(engine => engine.is_available).map(engine => <EngineChoice key={engine.id} engine={engine} current={selectedEngine?.id} busy={busy} t={t} c={c}
                            onPick={() => save(() => settings.setSelectedTranslationEngines(engine.id), { returnToMain: true })} />)}</div>
                        <details className={styles.unavailable} open={unavailableOpen} onToggle={event => setUnavailableOpen(event.currentTarget.open)}>
                            <summary data-vr-hoverable="" className={clsx(settingsStyles.row, settingsStyles.disclosure_toggle)} tabIndex={locked || syncError ? -1 : undefined} aria-disabled={locked || busy ? true : undefined}
                                onClick={event => { if (locked || busy) event.preventDefault(); }}><span className={settingsStyles.label}>{c('unavailable')}</span><span className={styles.count}>{engines.data.filter(engine => !engine.is_available).length}</span><span className={settingsStyles.chevron} aria-hidden="true">{unavailableOpen ? '⌄' : '›'}</span></summary>
                            <p className={styles.helper}>{c('unavailable_hint')}</p>
                            <div className={styles.choice_grid}>{engines.data.filter(engine => !engine.is_available).map(engine => <EngineChoice key={engine.id} engine={engine} current={selectedEngine?.id} busy={busy} t={t} c={c} />)}</div>
                        </details>
                    </> : view.stage === 'letters' ? <>
                        <h3 className={settingsStyles.section_label}>{c('letters_title')}</h3><div className={styles.letters}>{letters.map(letter => <button className={settingsStyles.button} key={letter} disabled={!selectable.data.some(entry => entry.language[0].toUpperCase() === letter)} aria-disabled={busy ? true : undefined}
                            onClick={() => !busy && setView({ ...view, stage: 'list', letter })}>{letter}</button>)}</div>
                    </> : <>
                        {view.stage === 'saved' && <button className={clsx(settingsStyles.row, settingsStyles.clickable, styles.all_languages)} aria-disabled={busy ? true : undefined} onClick={() => !busy && setView({ ...view, stage: 'letters' })}><span>A–Z</span>{c('all_languages')}<span className={settingsStyles.chevron} aria-hidden="true">›</span></button>}
                        <h3 className={settingsStyles.section_label}>{view.stage === 'list' ? c('letter_title', { letter: view.letter }) : c('saved')}</h3>
                        {view.stage === 'saved' && <p className={styles.helper}>{c('saved_hint')}</p>}
                        <div className={styles.choice_grid}>{languageChoices.map(entry => <button key={`${entry.language}/${entry.country}`} className={clsx(settingsStyles.row, settingsStyles.clickable, settingsStyles.option, styles.choice, languageSelected(entry) && settingsStyles.is_selected)}
                            aria-pressed={languageSelected(entry)} disabled={!selectable.data.some(option => same(entry, option)) || (!busy && (languageSelected(entry) || (view.kind === 'target-add' && targets.length >= 3)))} aria-disabled={busy ? true : undefined}
                            aria-label={`${entry.language} / ${entry.country}${languageSelected(entry) ? ` · ${selectionLabel(entry)}` : ''}`} onClick={() => choose(entry)}>
                            <LanguageText entry={entry} />{languageSelected(entry) && <span className={styles.check} aria-hidden="true">✓</span>}
                        </button>)}</div>
                    </>}
                </div>
            </fieldset>}
        </div>
    </VrWindow>;
}

function LanguageText({ entry, className }) {
    return <span className={clsx(settingsStyles.label, className)}><span>{entry?.language}</span><span className={settingsStyles.sub}>{entry?.country}</span></span>;
}
function EngineChoice({ engine, current, busy, t, c, onPick }) {
    const selected = engine.id === current;
    return <button className={clsx(settingsStyles.row, settingsStyles.clickable, settingsStyles.option, styles.choice, selected && settingsStyles.is_selected)} disabled={!engine.is_available || (selected && !busy)} aria-pressed={selected} aria-disabled={busy && engine.is_available ? true : undefined}
        aria-label={`${engineLabel(engine)}${selected ? ` · ${c('selected')}` : ''}`} onClick={() => !busy && onPick?.()}>
        <span className={settingsStyles.label}><span>{engineLabel(engine)}</span><span className={settingsStyles.sub}>{engine.is_default ? t('common.default_label') : selected ? c('selected') : '\u00a0'}</span></span>
        {selected && <span className={styles.check} aria-hidden="true">✓</span>}
    </button>;
}
