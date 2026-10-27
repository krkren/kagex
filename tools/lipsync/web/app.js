// KAGEX Lip Sync: pick voices and make their vowel data (.lip beside each voice)
import { app } from './lib/appserve.js';

let state = null;            // GET /api/lipsync/state
const picked = new Set();     // voice names
const typed = new Map();      // voice name -> the line typed for it (instead of the scripts')
const open = new Set();       // voice names whose track is shown

const $ = (s) => document.querySelector(s);
function el(tag, attrs = {}, ...children) {
	const e = document.createElement(tag);
	for (const [k, v] of Object.entries(attrs || {})) {
		if (v === undefined || v === null || v === false) continue;
		if (k === 'class') e.className = v;
		else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
		else e.setAttribute(k, v === true ? '' : v);
	}
	for (const c of children.flat()) if (c !== null && c !== undefined) e.append(c instanceof Node ? c : document.createTextNode(String(c)));
	return e;
}

const STATES = {
	none: 'No vowel data',
	current: 'Vowel data',
	stale: 'Out of date',
	manual: 'Hand-written',
	missing: 'Voice not found',
};
const MOUTHS = { a: 'a', i: 'i', u: 'u', e: 'e', o: 'o', n: 'closed', '-': 'other' };

const voices = () => (state && state.voices) || [];
const lineOf = (v) => (v.lines && v.lines.length ? v.lines[0] : null);
// a game in more than one language gives each voice its line in each: the source language's first
const sameLanguage = (v) => { const l = lineOf(v); return l ? v.lines.filter((x) => (x.language || '') === (l.language || '')) : []; };
const otherLanguages = (v) => { const l = lineOf(v); return l ? v.lines.filter((x) => (x.language || '') !== (l.language || '')) : []; };
const characterOf = (v) => (lineOf(v) ? lineOf(v).character : '');

function shown() {
	const f = $('#filter').value.trim().toLowerCase();
	const ch = $('#character').value;
	const st = $('#status').value;
	return voices().filter((v) => {
		if (ch && characterOf(v) !== ch) return false;
		if (st && v.status !== st) return false;
		if (!f) return true;
		const l = lineOf(v);
		return [v.name, characterOf(v), ...(v.lines || []).map((x) => x.text), typed.get(v.name) || ''].some((s) => s.toLowerCase().includes(f));
	});
}

//---------------------------------------------------------------------------
// The list
//---------------------------------------------------------------------------
function render() {
	const list = shown();
	const rows = $('#rows');
	rows.replaceChildren();
	for (const v of list) {
		const l = lineOf(v);
		const isPicked = picked.has(v.name);
		const box = el('input', { type: 'checkbox', 'aria-label': 'Select ' + v.name });
		box.checked = isPicked;
		box.disabled = v.status === 'missing';
		box.addEventListener('change', () => { box.checked ? picked.add(v.name) : picked.delete(v.name); updateButtons(); tr.classList.toggle('picked', box.checked); });
		const input = el('input', { type: 'text', class: 'line-input' + (typed.has(v.name) ? ' typed' : ''), spellcheck: 'false',
			placeholder: l ? (l.reading || l.text) : 'No line in the scripts: type what the voice says' });
		input.value = typed.get(v.name) || '';
		const others = otherLanguages(v);
		input.title = 'What the voice says. Empty: the line from the scripts' + (l && l.reading !== l.text ? ' (as read: ' + l.reading + ')' : '') +
			(others.length ? ', or the first of its other languages\' that fits the voice: ' + others.map((x) => x.language + ': ' + (x.reading || x.text)).join(' / ') : '');
		input.addEventListener('input', () => {
			const t = input.value;
			t.trim() ? typed.set(v.name, t) : typed.delete(v.name);
			input.classList.toggle('typed', typed.has(v.name));
		});
		const stale = v.status === 'current' && v.track && typed.has(v.name) && typed.get(v.name).trim() !== v.track.text;
		const status = el('span', { class: 'state ' + v.status, title: v.track ? 'Made from: ' + v.track.text : '' }, STATES[v.status] || v.status);
		const showBtn = (v.status === 'current' || v.status === 'stale' || v.status === 'manual')
			? el('button', { class: 'show', onclick: () => { open.has(v.name) ? open.delete(v.name) : open.add(v.name); render(); } }, open.has(v.name) ? 'Hide' : 'Show')
			: null;
		const tr = el('tr', { class: isPicked ? 'picked' : '' },
			el('td', { class: 'pick' }, box),
			el('td', {}, el('div', { class: 'voice-name' },
				v.file ? el('button', { class: 'play', title: 'Play', onclick: () => play(v) }, '▶') : null,
				el('span', {}, v.name))),
			el('td', {}, characterOf(v) || el('span', { class: 'muted' }, '—')),
			el('td', {}, input, l ? el('div', { class: 'script muted' }, l.script + (sameLanguage(v).length > 1 ? ` (and ${sameLanguage(v).length - 1} more lines)` : '') +
				(otherLanguages(v).length ? ' · also in ' + [...new Set(otherLanguages(v).map((x) => x.language))].join(', ') : '')) : null),
			el('td', {}, status, showBtn, stale ? el('div', { class: 'script muted' }, 'made from another line') : null));
		rows.append(tr);
		if (open.has(v.name)) rows.append(el('tr', { class: 'track' }, el('td'), el('td', { colspan: 4 }, trackView(v))));
	}
	$('#empty').hidden = list.length > 0;
	$('#empty').textContent = voices().length === 0
		? (state && state.linesRead ? 'The game has no voices: its scripts name none, and no folder is called voice.' : 'Reading the game\'s scripts…')
		: 'No voice matches.';
	const all = list.filter((v) => v.status !== 'missing');
	$('#pickAll').checked = all.length > 0 && all.every((v) => picked.has(v.name));
	updateButtons();
	summary();
}

function summary() {
	const vs = voices();
	const count = (s) => vs.filter((v) => v.status === s).length;
	const parts = [`${vs.length} voices`, `${count('current')} with vowel data`];
	if (count('stale')) parts.push(`${count('stale')} out of date`);
	if (count('manual')) parts.push(`${count('manual')} hand-written`);
	if (count('missing')) parts.push(`${count('missing')} named in the scripts but not found`);
	$('#summary').textContent = parts.join(' · ');
}

function updateButtons() {
	const names = [...picked];
	$('#make').disabled = !state || !state.project || names.length === 0;
	$('#make').textContent = names.length ? `Make vowel data (${names.length})` : 'Make vowel data';
	$('#remove').disabled = !names.some((n) => { const v = voices().find((x) => x.name === n); return v && v.status !== 'none' && v.status !== 'missing'; });
}

function fillCharacters() {
	const sel = $('#character');
	const was = sel.value;
	const names = [...new Set(voices().map(characterOf).filter((c) => c))].sort();
	sel.replaceChildren(el('option', { value: '' }, 'Every character'), ...names.map((n) => el('option', { value: n }, n)));
	if (names.includes(was)) sel.value = was;
}

//---------------------------------------------------------------------------
// A voice's track: the mouths over time, played along
//---------------------------------------------------------------------------
const audio = new Audio();
let playing = null;   // { name, view }

function play(v, view) {
	audio.pause();
	audio.src = '/api/lipsync/audio?name=' + encodeURIComponent(v.name);
	playing = { name: v.name, view: view || null };
	audio.play().catch(() => {});
}

function trackView(v) {
	const bar = el('div', { class: 'timeline' });
	const now = el('span', { class: 'now' });
	const legend = el('div', { class: 'legend' },
		...['a', 'i', 'u', 'e', 'o'].map((m) => el('span', { style: `--c: var(--m-${m})` }, m)),
		el('span', { style: '--c: var(--m-n)' }, 'closed'), el('span', { style: '--c: var(--m-x)' }, 'another sound'), el('span', { style: '--c: var(--bg)' }, 'silent'),
		el('button', { class: 'play', onclick: () => play(v, view) }, '▶ Play along'), now);
	const view = { bar, now, marks: [], length: 0 };
	app.get('/api/lipsync/track', { name: v.name }).then((marks) => {
		view.marks = marks;
		view.length = Math.max(1, marks.length ? marks[marks.length - 1][0] + 300 : 1);
		const probe = new Audio('/api/lipsync/audio?name=' + encodeURIComponent(v.name));
		probe.addEventListener('loadedmetadata', () => { if (isFinite(probe.duration)) { view.length = probe.duration * 1000; draw(view); } });
		draw(view);
	}).catch((e) => { bar.replaceWith(el('div', { class: 'muted' }, String(e.message || e))); });
	return el('div', {}, bar, legend);
}

function draw(view) {
	const { bar, marks, length } = view;
	bar.replaceChildren();
	for (let k = 0; k < marks.length; k++) {
		const [ms, mouth, open] = marks[k];
		const end = k + 1 < marks.length ? marks[k + 1][0] : length;
		if (open === 0 && mouth !== 'n') continue;
		const cls = 'aiueon'.includes(mouth) ? 'm-' + mouth : 'm-x';
		const seg = el('div', { class: 'seg ' + cls + (open === 1 ? ' half' : ''), title: `${ms} ms: ${MOUTHS[mouth] || mouth}${open >= 0 ? ', open ' + open : ''}` },
			'aiueo'.includes(mouth) ? mouth : '');
		seg.style.left = (ms / length * 100) + '%';
		seg.style.width = (Math.max(0, end - ms) / length * 100) + '%';
		bar.append(seg);
	}
	view.cursor = el('div', { class: 'cursor' });
	view.cursor.hidden = true;
	bar.append(view.cursor);
}

function tick() {
	if (playing && playing.view && !audio.paused) {
		const v = playing.view;
		const t = audio.currentTime * 1000;
		v.cursor.hidden = false;
		v.cursor.style.left = (t / v.length * 100) + '%';
		let cur = null;
		for (const m of v.marks) if (m[0] <= t) cur = m;
		v.now.textContent = cur ? (cur[2] === 0 && cur[1] !== 'n' ? 'shut' : MOUTHS[cur[1]] || cur[1]) : '';
	}
	requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

//---------------------------------------------------------------------------
// Jobs: reading the scripts, making tracks
//---------------------------------------------------------------------------
let dialog = null;

function openDialog(title) {
	if (dialog) return dialog;
	const bar = el('div', { class: 'progress indeterminate' }, el('div'));
	const message = el('div', {}, 'Starting…');
	const log = el('pre', { class: 'job-log' });
	const cancel = el('button', {}, 'Cancel');
	const close = el('button', { class: 'primary', hidden: true }, 'Close');
	const t = el('div', { class: 'dialog-title' }, title);
	const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' }, t, bar, message, log, el('div', { class: 'dialog-buttons' }, cancel, close)));
	document.body.append(dlg);
	cancel.addEventListener('click', () => app.post('/api/job/cancel', {}).catch(() => {}));
	close.addEventListener('click', () => { dlg.remove(); dialog = null; });
	dialog = { dlg, bar, message, log, cancel, close, title: t, done: false };
	return dialog;
}

async function showJob(st) {
	if (!st || (st.name !== 'read' && st.name !== 'make')) return;
	const running = st.state === 'running';
	if (st.name === 'read') {
		// reading is quick: no dialog, just the list once it's there
		$('#read').disabled = running;
		if (!running) {
			await reload();
			const r = st.result || {};
			if (st.error || r.error) notice('Couldn\'t read the scripts: ' + (st.error || r.error), true);
			else if (r.problems && r.problems.length) notice('Some scripts couldn\'t be read:\n' + r.problems.join('\n'));
			else notice('');
		}
		return;
	}
	const d = openDialog('Making vowel data');
	d.bar.className = 'progress' + (running && !(st.ratio >= 0) ? ' indeterminate' : '');
	d.bar.firstChild.style.width = (st.ratio >= 0 ? st.ratio * 100 : running ? 30 : 100) + '%';
	d.message.textContent = st.message || '';
	if (running || d.done) return;
	d.done = true;
	d.cancel.hidden = true;
	d.close.hidden = false;
	const r = st.result || {};
	d.title.textContent = st.state === 'canceled' ? 'Canceled' : r.ok ? 'Made' : 'Made, with problems';
	if (st.error || r.error) d.log.append((st.error || r.error) + '\n');
	for (const x of r.results || []) {
		if (x.ok) {
			d.log.append(`${x.name}: ${x.marks} marks (${x.language === 'ja' ? 'Japanese' : 'English'})\n`);
			for (const w of x.warnings || []) d.log.append(`  ${w}\n`);
		} else {
			d.log.append(`${x.name}: ${x.error}\n`);
		}
	}
	await reload();
}

function jobLog(line) {
	if (!dialog) return;
	dialog.log.append(String(line) + '\n');
	dialog.log.scrollTop = dialog.log.scrollHeight;
}

async function startRead() {
	try {
		$('#read').disabled = true;
		await app.post('/api/lipsync/read', {});
	} catch (e) {
		$('#read').disabled = false;
		notice('Couldn\'t read the scripts: ' + (e.message || e), true);
	}
}

async function startMake() {
	const items = [...picked].map((name) => ({ name, text: (typed.get(name) || '').trim() }));
	const hand = items.filter((it) => (voices().find((v) => v.name === it.name) || {}).status === 'manual');
	if (hand.length && !(await confirmBox('Replace hand-written tracks?',
		`${hand.map((h) => h.name).join(', ')} ${hand.length === 1 ? 'has a track' : 'have tracks'} kagex-lipsync didn't make. Replace ${hand.length === 1 ? 'it' : 'them'}?`, 'Replace'))) return;
	try {
		await app.post('/api/lipsync/make', { voices: items });
		openDialog('Making vowel data');
	} catch (e) {
		alertBox('Couldn\'t start', String(e.message || e));
	}
}

async function removeTracks() {
	const names = [...picked].filter((n) => { const v = voices().find((x) => x.name === n); return v && v.status !== 'none' && v.status !== 'missing'; });
	if (!names.length) return;
	if (!(await confirmBox('Remove vowel data', `Delete the .lip of ${names.length} voice${names.length === 1 ? '' : 's'}? Their mouths then open and shut by loudness alone.`, 'Delete'))) return;
	try {
		await app.post('/api/lipsync/remove', { names });
	} catch (e) {
		alertBox('Couldn\'t remove', String(e.message || e));
	}
	await reload();
}

function notice(text, bad) {
	const n = $('#notice');
	n.hidden = !text;
	n.textContent = text || '';
	n.classList.toggle('bad', !!bad);
}

//---------------------------------------------------------------------------
// Dialogs
//---------------------------------------------------------------------------
function alertBox(title, text) {
	const ok = el('button', { class: 'primary' }, 'OK');
	const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' },
		el('div', { class: 'dialog-title' }, title), el('div', {}, text), el('div', { class: 'dialog-buttons' }, ok)));
	ok.addEventListener('click', () => dlg.remove());
	document.body.append(dlg);
	ok.focus();
}

function confirmBox(title, text, yes) {
	return new Promise((resolve) => {
		const no = el('button', {}, 'Cancel');
		const go = el('button', { class: 'primary' }, yes);
		const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' },
			el('div', { class: 'dialog-title' }, title), el('div', {}, text), el('div', { class: 'dialog-buttons' }, no, go)));
		no.addEventListener('click', () => { dlg.remove(); resolve(false); });
		go.addEventListener('click', () => { dlg.remove(); resolve(true); });
		document.body.append(dlg);
		go.focus();
	});
}

// A folder from this computer (the browser has no native dialog for that)
function pickFolder(initial) {
	return new Promise(async (resolve) => {
		const pathInput = el('input', { type: 'text', spellcheck: 'false' });
		const list = el('div', { class: 'picker-list' });
		const roots = el('div', { class: 'picker-roots' });
		const ok = el('button', { class: 'primary' }, 'Choose this folder');
		const cancel = el('button', {}, 'Cancel');
		const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' },
			el('div', { class: 'dialog-title' }, 'Choose the game\'s folder (the one with data/)'), roots, pathInput, list,
			el('div', { class: 'muted' }, 'Double-click a folder to open it.'), el('div', { class: 'dialog-buttons' }, cancel, ok)));
		document.body.append(dlg);
		const close = (v) => { dlg.remove(); resolve(v); };
		cancel.addEventListener('click', () => close(null));
		ok.addEventListener('click', () => close(pathInput.value));
		const go = async (path) => {
			let r;
			try { r = await app.get('/api/fs/list', { path }); } catch (e) { list.textContent = String(e.message || e); return; }
			pathInput.value = r.path;
			list.replaceChildren();
			if (r.parent) list.append(el('div', { class: 'picker-item dir', ondblclick: () => go(r.parent) }, '..'));
			for (const e of r.entries.filter((x) => x.dir).sort((a, b) => a.name.localeCompare(b.name)))
				list.append(el('div', { class: 'picker-item dir', ondblclick: () => go(e.path) }, e.name));
		};
		pathInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') go(pathInput.value); });
		try {
			const rr = await app.get('/api/fs/roots');
			for (const root of rr.roots) roots.append(el('button', { onclick: () => go(root.path) }, root.label || root.path));
		} catch (e) { /* the path can still be typed */ }
		go(initial || '.');
	});
}

//---------------------------------------------------------------------------
// Start
//---------------------------------------------------------------------------
async function reload() {
	state = await app.get('/api/lipsync/state');
	$('#version').textContent = state.version || '';
	const fatal = !state.project ? (state.error || 'No game found') + '\nUse Open… to choose the folder that holds your game\'s data folder.'
		: !state.models ? `The speech models aren't at ${state.modelsDir}: kagex-lipsync needs the lipsync folder that comes beside it.` : '';
	$('#fatal').hidden = !fatal;
	$('#fatal').textContent = fatal;
	$('#projectPath').replaceChildren(el('bdi', { dir: 'ltr' }, state.project ? state.project.root : ''));
	$('#read').disabled = !state.project;
	// a pick of a voice that's gone
	for (const n of [...picked]) if (!voices().some((v) => v.name === n)) picked.delete(n);
	fillCharacters();
	render();
	if (state.readError) notice('Couldn\'t read the scripts: ' + state.readError, true);
}

$('#filter').addEventListener('input', render);
$('#character').addEventListener('change', render);
$('#status').addEventListener('change', render);
$('#pickAll').addEventListener('change', (e) => {
	for (const v of shown()) if (v.status !== 'missing') e.target.checked ? picked.add(v.name) : picked.delete(v.name);
	render();
});
$('#selectShown').addEventListener('click', () => { for (const v of shown()) if (v.status !== 'missing') picked.add(v.name); render(); });
$('#selectNone').addEventListener('click', () => { picked.clear(); render(); });
$('#read').addEventListener('click', startRead);
$('#make').addEventListener('click', startMake);
$('#remove').addEventListener('click', removeTracks);
$('#openProject').addEventListener('click', async () => {
	const dir = await pickFolder(state && state.project ? state.project.root : '.');
	if (dir == null) return;
	try {
		await app.post('/api/lipsync/open', { path: dir });
		picked.clear();
		typed.clear();
		open.clear();
		await reload();
		startRead();
	} catch (e) {
		alertBox('No game there', String(e.message || e));
	}
});

await app.ready();
app.on('job', showJob);
app.on('joblog', jobLog);
await reload();
// the lines come from the game's own scripts: read them as the window opens
const job = await app.get('/api/job').catch(() => null);
if (job && job.state === 'running') showJob(job);
else if (state.project && !state.linesRead) startRead();
