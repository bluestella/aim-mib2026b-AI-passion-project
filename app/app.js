/* DALOY Scan — rules-only v1 (plan Phase 3).
 *
 * No machine learning, no backend, no network calls after the first load. The user
 * picks a material by its junkshop trade name and gets the Pathway Card; the rules
 * come from app/data/rules.json, compiled from rules/*.yaml by
 * scripts/build_app_data.py so the app and the Python engine cannot drift.
 *
 * Three invariants this file must not break:
 *
 *  1. Nothing is attributed to the Municipality of Cainta while
 *     `presentable_as_official` is false. Guidance is shown; authorship is not
 *     claimed. (plan §7.8)
 *  2. No precise location is requested or stored. The barangay picker is the whole
 *     location model, and it never leaves localStorage. (plan §7.5)
 *  3. Prices are labelled as unverified estimates until the field survey lands.
 *     (plan §10)
 */

'use strict';

const STORE_KEY = 'daloy.v1';
const STAGE_MS = 900;

let RULES = null;
let state = { barangay: null, bank: {} };
let selection = { material: null, flags: new Set(), contaminated: false };
let flowTimers = [];

/* ── Persistence ─────────────────────────────────────────────────────── */

function load() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) state = Object.assign(state, JSON.parse(raw));
  } catch (err) {
    // A corrupt or unavailable store is not worth an error screen — the app is
    // fully usable without it, it just forgets the barangay.
    console.warn('Local store unavailable; continuing without it.', err);
  }
}

function save() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch (err) {
    console.warn('Could not persist local state.', err);
  }
}

/* ── Small helpers ───────────────────────────────────────────────────── */

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function material(cls) {
  return RULES.materials.find((m) => m.class === cls);
}

/** Trade name first — that is how the item is actually asked for at a junkshop. */
function displayName(m) {
  return m.local_names[0] || m.class;
}

function subName(m) {
  const rest = m.local_names.slice(1);
  return rest.length ? rest.join(', ') : m.class.replace(/_/g, ' ');
}

/* ── Navigation ──────────────────────────────────────────────────────── */

const VIEWS = ['setup', 'picker', 'modifiers', 'card', 'flow', 'bank', 'shops', 'privacy'];
const TABS = ['picker', 'bank', 'shops', 'privacy'];
let current = 'setup';

function go(view) {
  clearFlow();
  current = view;
  VIEWS.forEach((v) => { $('view-' + v).hidden = v !== view; });

  $('tabbar').hidden = !state.barangay;
  $('back').hidden = !(view === 'modifiers' || view === 'card' || view === 'flow');

  document.querySelectorAll('.tabbar button').forEach((b) => {
    b.classList.toggle('active', b.dataset.goto === view);
  });

  // go() owns rendering. Callers navigate and nothing else — rendering before
  // navigating used to schedule the flow animation only for clearFlow() above to
  // cancel it on the very next line.
  if (view === 'picker') renderPicker();
  if (view === 'modifiers') renderModifiers();
  if (view === 'card') renderCard();
  if (view === 'flow') renderFlow();
  if (view === 'bank') renderBank();
  if (view === 'shops') renderShops();

  window.scrollTo(0, 0);
}

function goBack() {
  if (current === 'flow') return go('card');
  if (current === 'card') return go('modifiers');
  if (current === 'modifiers') return go('picker');
  return go('picker');
}

/* ── Setup ───────────────────────────────────────────────────────────── */

function renderSetup() {
  const list = $('barangay-list');
  list.replaceChildren();
  RULES.barangays.forEach((name) => {
    const b = el('button', 'choice');
    b.appendChild(el('span', 'name', name));
    b.addEventListener('click', () => {
      state.barangay = name;
      save();
      go('picker');
    });
    list.appendChild(b);
  });
}

/* ── Picker ──────────────────────────────────────────────────────────── */

function renderPicker() {
  const list = $('material-list');
  list.replaceChildren();

  RULES.materials.forEach((m) => {
    const b = el('button', 'choice');
    b.appendChild(el('span', 'name', displayName(m)));
    b.appendChild(el('span', 'sub', subName(m)));

    // A nominal price on a material most shops refuse is worse than no price: it
    // reads as an invitation to carry the thing across the barangay.
    if (m.often_refused) {
      b.appendChild(el('span', 'tag none', 'Madalas tinatanggihan'));
    } else if (m.price.has_market) {
      b.appendChild(el('span', 'tag value', m.price.display));
    } else {
      b.appendChild(el('span', 'tag none', 'Walang bumibili'));
    }

    b.addEventListener('click', () => {
      selection = { material: m.class, flags: new Set(), contaminated: false };
      go('modifiers');
    });
    list.appendChild(b);
  });

  $('picker-foot').textContent =
    `Barangay ${state.barangay}. Ang mga presyo ay tinatayang halaga lamang — ` +
    'magtanong pa rin sa junkshop.';
}

/* ── Modifiers ───────────────────────────────────────────────────────── */

/* Overrides come from the rules bundle rather than being hardcoded here, so adding
 * one to the YAML surfaces it in the UI without touching this file. */
function renderModifiers() {
  const m = material(selection.material);
  $('mod-title').textContent = displayName(m);

  const list = $('modifier-list');
  list.replaceChildren();

  RULES.overrides.forEach((o) => {
    const label = el('label', 'toggle');
    const input = el('input');
    input.type = 'checkbox';
    // Restore from `selection`: the user can navigate back here from the card, and
    // a box that renders unchecked while the flag is still set would show a verdict
    // the visible controls do not explain.
    input.checked = o.when.contaminated
      ? selection.contaminated
      : selection.flags.has(o.when.user_flag);

    const body = el('div');
    body.appendChild(el('div', 't-name', modifierLabel(o)));
    body.appendChild(el('div', 't-sub', o.reason_tl));

    input.addEventListener('change', () => {
      if (o.when.contaminated) {
        selection.contaminated = input.checked;
      } else if (o.when.user_flag) {
        if (input.checked) selection.flags.add(o.when.user_flag);
        else selection.flags.delete(o.when.user_flag);
      }
    });

    label.append(input, body);
    list.appendChild(label);
  });
}

function modifierLabel(o) {
  if (o.when.contaminated) return 'May dumi ng pagkain o mantika';
  if (o.when.user_flag === 'battery') return 'Baterya ito';
  if (o.when.user_flag === 'electronic') return 'Electronic / may kable ito';
  return o.id;
}

/* ── Resolution ──────────────────────────────────────────────────────── */

/* Mirrors daloy.rules_engine.resolve: first matching override wins, and it replaces
 * both the pathway and the citations. Kept in the same order as the Python so the
 * two answer identically. */
function resolve() {
  const m = material(selection.material);
  let pathway = m.pathway;
  let animation = m.animation;
  let override = null;

  for (const o of RULES.overrides) {
    const matched =
      (o.when.user_flag && selection.flags.has(o.when.user_flag)) ||
      (o.when.contaminated && selection.contaminated);
    if (matched) {
      pathway = o.pathway;
      animation = o.animation;
      override = o;
      break;
    }
  }

  return { material: m, pathway, animation, override };
}

/* ── Pathway card ────────────────────────────────────────────────────── */

function renderCard() {
  const r = resolve();
  const m = r.material;
  const pathway = RULES.pathways[r.pathway];
  const card = $('card');
  card.replaceChildren();

  card.appendChild(el('div', 'eyebrow', 'Ito ay'));
  card.appendChild(el('div', 'what', displayName(m)));
  card.appendChild(el('div', 'trade', subName(m)));

  const verdict = el('div', 'verdict ' + r.animation);
  verdict.appendChild(el('div', 'v-label', pathway.label_tl));
  verdict.appendChild(el('div', 'v-en', pathway.label_en));

  // An override changed the answer — say so instead of showing the price, or the
  // user sees a pathway that contradicts the price tag they just tapped.
  //
  // Otherwise always state the market position, including when there isn't one.
  // "Walang bumibili" is the single most important fact about a sachet, and
  // omitting it here would leave the card's most prominent block silent on it.
  if (r.override) {
    verdict.appendChild(el('div', 'v-en', r.override.reason_tl));
  } else if (m.often_refused) {
    verdict.appendChild(el('div', 'v-price', 'Madalas tinatanggihan'));
    verdict.appendChild(el('div', 'v-en',
      'May nominal na presyo (' + m.price.display + ') pero karamihan ng ' +
      'junkshop ay ayaw tumanggap. Tumawag muna bago magdala.'));
  } else {
    verdict.appendChild(el('div', 'v-price', m.price.display));
  }
  card.appendChild(verdict);

  // An override that changed the pathway also replaces the prep text — the
  // material's own instructions describe the route the user is no longer on.
  const how = el('div', 'how');
  how.appendChild(el('strong', null, 'Paano'));
  how.appendChild(el('div', null,
    (r.override && r.override.prep_tl) ? r.override.prep_tl : m.prep_tl));
  card.appendChild(how);

  if (m.is_critical_class) {
    card.appendChild(
      el('div', 'flag',
        'Ito ang pangunahing bumabara sa mga kanal at sapa ng Cainta. Walang ' +
        'recycling market — ang tanging magagawa ay huwag itong mapunta sa tubig.')
    );
  }

  // Only caveat a price that is actually on screen; an override suppresses it.
  if (!r.override && m.price.has_market && !RULES.verification.phase2_gate_met) {
    card.appendChild(
      el('div', 'note',
        'Tinatayang presyo — wala pang na-verify na junkshop sa Cainta. ' +
        'Magtanong sa tindahan bago magdala.')
    );
  }

  card.appendChild(legalBlock(m));
}

/* The §7.8 guardrail, rendered. While `presentable_as_official` is false the app
 * shows the citation but explicitly disclaims authorship. */
function legalBlock(m) {
  const legal = el('div', 'legal');
  if (!m.citations.length) return legal;

  const names = m.citations.map((c) => c.citation).join('; ');

  if (m.presentable_as_official) {
    legal.appendChild(el('div', null, 'Batay sa: ' + names));
  } else {
    legal.appendChild(el('div', null, 'Kaugnay na batas: ' + names));
    legal.appendChild(
      el('div', 'unverified',
        'Hindi pa nabe-verify sa orihinal na dokumento. Hindi ito opisyal na ' +
        'pahayag ng Pamahalaang Bayan ng Cainta.')
    );
  }
  return legal;
}

/* ── Flow simulation ─────────────────────────────────────────────────── */

function clearFlow() {
  flowTimers.forEach(clearTimeout);
  flowTimers = [];
}

function renderFlow() {
  clearFlow();
  const r = resolve();
  const flow = RULES.flow[r.animation];

  $('flow-title').textContent = flow.label_tl;

  const list = $('flow-stages');
  list.className = 'flow ' + r.animation;
  list.replaceChildren();

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  flow.stages.forEach((stage, i) => {
    const li = el('li');
    if (stage.terminal) li.classList.add('terminal');
    li.appendChild(el('div', 's-label', stage.label_tl));
    li.appendChild(el('div', 's-detail', stage.detail_tl));
    list.appendChild(li);

    if (reduced) {
      li.classList.add('on');
    } else {
      flowTimers.push(setTimeout(() => li.classList.add('on'), i * STAGE_MS));
    }
  });

  $('flow-caveat').textContent =
    'Schematic ito — dayagram ng pangkalahatang direksyon, hindi mapa. Hindi pa ' +
    'namin nave-verify kung aling sapa ang dumadaloy mula sa Barangay ' +
    state.barangay + ', kaya wala kaming pinapangalanang sapa.';
}

/* ── Bote Bank ───────────────────────────────────────────────────────── */

function addToBank(cls) {
  state.bank[cls] = (state.bank[cls] || 0) + 1;
  save();
}

function renderBank() {
  const entries = Object.entries(state.bank).filter(([, n]) => n > 0);
  const totals = $('bank-totals');
  const ledger = $('bank-ledger');
  totals.replaceChildren();
  ledger.replaceChildren();

  const items = entries.reduce((sum, [, n]) => sum + n, 0);

  // Diverted mass, not peso value. Prices are unverified, so a peso total would be
  // a made-up number presented as an achievement.
  let grams = 0;
  entries.forEach(([cls, n]) => {
    const m = material(cls);
    if (m && m.typical_unit_mass_g) grams += m.typical_unit_mass_g * n;
  });

  const t1 = el('div', 'total');
  t1.appendChild(el('div', 't-num', String(items)));
  t1.appendChild(el('div', 't-lab', 'piraso na naitabi'));
  totals.appendChild(t1);

  const t2 = el('div', 'total');
  t2.appendChild(el('div', 't-num', grams >= 1000
    ? (grams / 1000).toFixed(1) + ' kg'
    : Math.round(grams) + ' g'));
  t2.appendChild(el('div', 't-lab', 'tinatayang bigat'));
  totals.appendChild(t2);

  if (!entries.length) {
    const empty = el('div', 'empty');
    empty.appendChild(el('strong', null, 'Wala pa rito.'));
    empty.appendChild(el('div', null,
      'Mag-scan, tapos pindutin ang "Idagdag sa Bote Bank".'));
    ledger.appendChild(empty);
  }

  entries
    .sort((a, b) => b[1] - a[1])
    .forEach(([cls, n]) => {
      const m = material(cls);
      const li = el('li');
      li.appendChild(el('span', 'l-name', m ? displayName(m) : cls));
      li.appendChild(el('span', 'l-count', String(n)));

      const drop = el('button', 'l-drop', '×');
      drop.setAttribute('aria-label', 'Bawasan');
      drop.addEventListener('click', () => {
        state.bank[cls] = Math.max(0, (state.bank[cls] || 0) - 1);
        save();
        renderBank();
      });
      li.appendChild(drop);
      ledger.appendChild(li);
    });

  $('bank-note').textContent =
    'Tinatayang bigat lamang, batay sa karaniwang timbang bawat piraso. Hindi ' +
    'namin ipinapakita ang halaga sa piso dahil wala pang na-verify na presyo.';
}

/* ── Junkshops ───────────────────────────────────────────────────────── */

/* There are zero surveyed shops. An empty map with a "no results" toast would imply
 * there are no junkshops in Cainta, which is false — the data simply does not exist
 * yet. Say that instead. */
function renderShops() {
  const body = $('shops-body');
  body.replaceChildren();

  if (RULES.verification.verified_shops > 0) {
    body.appendChild(el('p', null,
      RULES.verification.verified_shops + ' na-verify na junkshop.'));
    return;
  }

  const empty = el('div', 'empty');
  empty.appendChild(el('strong', null, 'Wala pa kaming listahan.'));
  empty.appendChild(el('div', null,
    'Hindi ito nangangahulugang walang junkshop sa Cainta — marami. Ang ibig ' +
    'sabihin, hindi pa namin nabibisita at nave-verify ang mga ito, at ayaw ' +
    'naming magpadala kayo sa isang tindahang sarado na o hindi tumatanggap ng ' +
    'dala ninyo.'));
  body.appendChild(empty);

  body.appendChild(el('p', 'fineprint',
    'Sa susunod na bahagi ng proyekto, bibisitahin ang 30–60 junkshop sa Cainta ' +
    'para itala ang lokasyon, presyo, at kung ano ang tinatanggap nila.'));
}

/* ── Provisional banner ──────────────────────────────────────────────── */

function renderProvisional() {
  const v = RULES.verification;
  if (v.phase1_gate_met && v.phase2_gate_met) return;

  const bits = [];
  if (!v.phase1_gate_met) {
    bits.push('Hindi pa nabe-verify ang mga ordinansa sa orihinal na dokumento');
  }
  if (!v.phase2_gate_met) {
    bits.push('tinatayang presyo lamang ang ipinapakita');
  }
  $('provisional-text').textContent = bits.join('; ') + '.';
  $('provisional').hidden = false;

  $('privacy-legal').textContent =
    'Ang mga ordinansang binabanggit ay galing sa planning document ng proyekto, ' +
    'at ' + v.legal_sources_verified + ' sa ' + v.legal_sources_total +
    ' ang nabe-verify sa orihinal na dokumento. Kaya hindi namin sinasabing ' +
    'opisyal na pahayag ito ng Pamahalaang Bayan ng Cainta. Kung may pagkakaiba, ' +
    'ang opisyal na dokumento ng Bayan ang masusunod.';
}

/* ── Wiring ──────────────────────────────────────────────────────────── */

function wire() {
  $('back').addEventListener('click', goBack);
  $('nav-info').addEventListener('click', () => go('privacy'));

  document.querySelectorAll('[data-goto]').forEach((node) => {
    node.addEventListener('click', (e) => {
      e.preventDefault();
      go(node.dataset.goto);
    });
  });

  $('mod-continue').addEventListener('click', () => go('card'));
  $('act-again').addEventListener('click', () => go('picker'));
  $('act-flow').addEventListener('click', () => go('flow'));
  $('flow-back').addEventListener('click', () => go('card'));
  $('flow-replay').addEventListener('click', renderFlow);

  $('act-save').addEventListener('click', (e) => {
    addToBank(selection.material);
    e.target.textContent = 'Naidagdag ✓';
    setTimeout(() => { e.target.textContent = 'Idagdag sa Bote Bank'; }, 1400);
  });

  $('bank-clear').addEventListener('click', () => {
    state.bank = {};
    save();
    renderBank();
  });
}

async function boot() {
  try {
    const response = await fetch('data/rules.json');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    RULES = await response.json();
  } catch (err) {
    $('main').replaceChildren(
      el('h2', null, 'Hindi ma-load ang datos'),
      el('p', 'lede', 'Kailangang i-serve ang app mula sa isang web server, ' +
        'hindi bilang file:// — kung hindi, hindi mababasa ang data/rules.json.')
    );
    console.error(err);
    return;
  }

  load();
  wire();
  renderProvisional();
  renderSetup();
  go(state.barangay ? 'picker' : 'setup');

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch((err) => {
      // Offline support is a bonus, not a requirement. Never block boot on it.
      console.warn('Service worker registration failed.', err);
    });
  }
}

boot();
