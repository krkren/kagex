// KAGEX Release: the settings screen. Edits release.json; the tool checks it as you go.
import { app } from './lib/appserve.js';

let state = null;        // GET /api/release/state
let settings = null;     // the settings being edited
let savedText = '';      // settings as last saved (to tell unsaved changes)
let issues = [];         // from /api/release/check
let plan = null;
const hostStatus = {};   // platform id -> status (requirements on this computer)

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
const get = (obj, path) => path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
function set(obj, path, value) {
	const keys = path.split('.');
	let o = obj;
	for (const k of keys.slice(0, -1)) o = o[k] ??= {};
	o[keys.at(-1)] = value;
}
const formatSize = (n) => n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : n < 1073741824 ? (n / 1048576).toFixed(1) + ' MB' : (n / 1073741824).toFixed(2) + ' GB';

//---------------------------------------------------------------------------
// What the screen shows
//---------------------------------------------------------------------------
const DATA_XP3 = ['xp3', 'data.xp3 (one archive)'];
const DATA_FOLDER = ['folder', 'data folder (the files as they are)'];

const SECTIONS = [
	{
		id: 'game', title: 'Game',
		intro: 'How the game is named on each platform. The organization and app names name the save folder on Linux and macOS, so they should be your own.',
		fields: [
			{ path: 'identity.title', label: 'Title', type: 'text', help: 'The window title, the macOS app and the store listings use it' },
			{ path: 'identity.shortName', label: 'Short name', type: 'text', help: 'Under the icon on phone and tablet home screens (about 12 characters)' },
			{ path: 'identity.exeName', label: 'File name', type: 'text', help: 'The executable on Windows and Linux (with its .cf), and the package names' },
			{ path: 'identity.version', label: 'Version', type: 'text', help: 'Numbers like 1.0 or 1.2.3' },
			{ path: 'identity.copyright', label: 'Copyright', type: 'text' },
			{ path: 'identity.orgName', label: 'Organization name', type: 'text' },
			{ path: 'identity.appName', label: 'App name', type: 'text' },
			{ path: 'identity.icon', label: 'Icon', type: 'file', help: 'A PNG, 1024x1024; each platform gets the sizes it needs' },
		],
	},
	{ id: 'platforms', title: 'Platforms', intro: 'Choose what to build. Each platform shows whether this computer has what building it takes.', render: renderPlatforms },
	{
		id: 'media', title: 'Media',
		intro: 'Lossless sources can be converted to smaller files. Lossy files (Ogg, Opus, JPEG) are never converted again. Conversions are cached, so later builds are quick.',
		fields: [
			{ path: 'media.audio.convert', label: 'WAV and FLAC become', type: 'select', options: [['opus', 'Opus (recommended)'], ['vorbis', 'Ogg Vorbis'], ['keep', 'Kept as they are (FLAC is converted to WAV)']] },
			{ path: 'media.audio.opusKbps', label: 'Opus bitrate', type: 'kbps', showIf: (s) => s.media.audio.convert === 'opus', help: 'By the folder the sound is in (under data/); * is everything else' },
			{ path: 'media.audio.vorbisQuality', label: 'Vorbis quality', type: 'number', min: 0, max: 10, showIf: (s) => s.media.audio.convert === 'vorbis', help: '0 to 10; 5 is about 160 kbps' },
			{ path: 'media.images.opaque', label: 'Opaque images become', type: 'select', options: [['tlg6', 'TLG6 (recommended)'], ['tlg5', 'TLG5 (decodes faster)'], ['png', 'PNG'], ['jpeg', 'JPEG (lossy)'], ['keep', 'Kept as they are']] },
			{ path: 'media.images.alpha', label: 'Transparent images become', type: 'select', options: [['tlg6', 'TLG6 (recommended)'], ['tlg5', 'TLG5 (decodes faster)'], ['png', 'PNG'], ['jpeg-mask', 'JPEG and a mask image (lossy)'], ['keep', 'Kept as they are']] },
			{ path: 'media.images.jpegQuality', label: 'JPEG quality', type: 'number', min: 1, max: 100, showIf: (s) => s.media.images.opaque === 'jpeg' || s.media.images.alpha === 'jpeg-mask' },
			{ path: 'media.references', label: 'Names with extensions', type: 'select', options: [['keep', 'Keep those files unconverted'], ['rewrite', 'Convert them and rewrite the scripts']], help: 'Scripts usually name files without an extension. Where one is written out (bgm01.wav), the file is kept as it is, or converted with the name in the script changed' },
		],
	},
	{
		id: 'contents', title: 'Contents',
		intro: 'What goes into data.',
		fields: [
			{ path: 'contents.framework', label: 'Framework', type: 'check', text: 'Copy template/system in as data/system (when the game has no data/system)' },
			{ path: 'contents.font', label: 'Font', type: 'check', text: 'Include Noto Sans JP (Japanese text where the player has no Japanese font)' },
			{ path: 'contents.licenses', label: 'Licenses', type: 'check', text: 'Include the engine\'s license files (its libraries ask for them)' },
			{ path: 'contents.plugins', label: 'Plugins', type: 'select', options: [['all', 'All the engine\'s plugins'], ['linked', 'Only the ones the scripts link']] },
			{ path: 'contents.compileScripts', label: 'Scripts', type: 'check', text: 'Compile the TJS scripts to bytecode (this computer\'s engine does it)', help: 'The packages then carry no readable TJS (strings and names still show), and they start a little faster. Errors in compiled scripts name the function but not the line, and @if switches are decided when building' },
			{ path: 'contents.exclude', label: 'Leave out', type: 'lines', help: 'One pattern per line: *.psd matches anywhere, bgimage/raw/** a folder\'s contents, work/ a folder' },
			{ path: 'contents.extraFiles', label: 'Extra files', type: 'lines', help: 'Files next to data/ to put beside the executable (a readme, a manual), one per line' },
		],
	},
	{
		id: 'output', title: 'Output',
		fields: [
			{ path: 'output.folder', label: 'Output folder', type: 'folder', help: 'Each build goes to <file name>-<version>-<platform> in here' },
			{ path: 'output.archive', label: 'Archive', type: 'select', options: [['auto', 'zip, or tar.gz for Linux (keeps the executable flag)'], ['zip', 'zip'], ['tar.gz', 'tar.gz'], ['none', 'None (folders only)']] },
			{ path: 'output.checksums', label: 'Checksums', type: 'check', text: 'Write SHA256SUMS next to the packages' },
			{ path: 'output.check', label: 'Test run', type: 'check', text: 'Start this computer\'s build for a few seconds afterwards (without a window where it can) and look for script errors' },
			{ path: 'output.patchFrom', label: 'Patch from', type: 'file', help: 'A file list an earlier build wrote (<file name>-<version>-files.json): makes patch.zip of what changed since, which the game loads from next to it or from its save folder. Make it from the full release\'s list, so each patch replaces the last' },
			{ path: 'engine.debug', label: 'Engine', type: 'check', text: 'Debug engine (keeps the console and debug keys; for testers, not for players)' },
		],
	},
	{
		id: 'signing', title: 'Signing',
		intro: 'Check the game files for tampering before the game starts (Windows, Linux and macOS). The game carries your public key and verifies the archive, the engine and any patches; a damaged or differently signed file stops it. The web, Android and iOS builds rely on the platform instead.',
		render: renderSigning,
	},
	{
		id: 'encryption', title: 'Encryption',
		intro: 'Encrypts every file in data.xp3, so the game\'s scripts and pictures can\'t be read out of the package; the engine decrypts them as it reads, with the key written into each build\'s engine. The engine packages need the xp3crypt plugin built in. The key ships inside the game, so this keeps the files out of casual view; it doesn\'t stop a determined person.',
		fields: [
			{ type: 'note', label: '', text: 'This kagex-release was built without xp3crypt, so it can\'t encrypt.', showIf: () => !state.canEncrypt },
			{ path: 'archive.encrypt', label: 'Encrypt', type: 'check', text: 'Encrypt the files in data.xp3 (platforms whose data is data.xp3 or bound into the executable)', showIf: () => state.canEncrypt },
			{ path: 'archive.keyFile', label: 'Key file', type: 'keyfile', showIf: (s) => state.canEncrypt && s.archive.encrypt,
			  help: 'Create key… makes a new random key; Browse… picks one you already have. Keep it outside the game\'s folder and back it up: a game can only be rebuilt or patched with the key it was released with, and anyone who has it can read the encrypted files. KAGEX_ARCHIVE_KEY overrides it (for CI)' },
			{ path: 'archive.hideNames', label: 'Hide names', type: 'check', text: 'Also hide the file names (one archive, data.xpc, with hashed names)', showIf: (s) => state.canEncrypt && s.archive.encrypt,
			  help: 'The game ships as one encrypted archive whose file names are hashed, so a generic tool sees neither the files nor their names. Desktop only, and the data mode can\'t be "bind". The game reads it through the plugin\'s xpcrypt:// medium' },
		],
	},
	{ id: 'plan', title: 'Check', intro: 'What a build would make, and anything that would stop it.', render: renderPlan },
];

const SIGNING_FIELDS = [
	{ path: 'enabled', label: 'Signing', type: 'check', text: 'Sign the release and check it at start-up' },
	{ path: 'privateKey', label: 'Private key', type: 'file', showIf: (s) => s.enabled, help: 'Your RSA private key. Keep it secret and out of version control. The KAGEX_SIGNING_KEY environment variable overrides it, for CI' },
	{ path: 'splitArchives', label: 'Split large archives', type: 'check', showIf: (s) => s.enabled, text: 'Put large media folders in their own archives (done automatically once the data passes 2 GB)' },
];

const PLATFORM_FIELDS = {
	windows: [
		{ path: 'data', label: 'Data', type: 'select', options: [DATA_XP3, DATA_FOLDER, ['bind', 'Bound into the exe (one file)']] },
		{ path: 'versionInfo', label: 'Icon and version', type: 'check', text: 'Put the icon, title, version and copyright into the exe (when this tool runs on Windows)' },
	],
	linux: [
		{ path: 'data', label: 'Data', type: 'select', options: [DATA_XP3, DATA_FOLDER, ['bind', 'Bound into the executable (one file)']] },
		{ path: 'desktopEntry', label: 'Menu entry', type: 'check', text: 'Include a .desktop file and the icon' },
	],
	steam: [
		{ path: 'data', label: 'Data', type: 'select', options: [DATA_XP3, DATA_FOLDER, ['bind', 'Bound into the executable (one file)']] },
	],
	macos: [
		{ path: 'data', label: 'Data', type: 'select', options: [DATA_XP3, DATA_FOLDER] },
		{ path: 'bundleId', label: 'Bundle ID', type: 'text', help: 'Like com.studio.game' },
		{ path: 'signing', label: 'Signing', type: 'select', options: [['adhoc', 'Ad hoc (no Apple account; players allow it once)'], ['developer-id', 'Developer ID (Apple Developer Program)']] },
		{ path: 'identity', label: 'Certificate', type: 'text', showIf: (p) => p.signing === 'developer-id', help: 'Developer ID Application: Your Name (TEAMID)' },
		{ path: 'notarize', label: 'Notarize', type: 'check', text: 'Send it to Apple for notarization (opens without warnings)', showIf: (p) => p.signing === 'developer-id' },
		{ path: 'notaryProfile', label: 'Notary profile', type: 'text', showIf: (p) => p.signing === 'developer-id' && p.notarize, help: 'The keychain profile saved with xcrun notarytool store-credentials' },
		{ path: 'format', label: 'Package', type: 'select', options: [['zip', 'zip'], ['dmg', 'Disk image (.dmg)']] },
	],
	web: [
		{ path: 'data', label: 'Data', type: 'select', options: [['files', 'Files, each loaded when the game needs it (recommended)'], ['xp3', 'data.xp3, loaded before the game starts']] },
		{ path: 'url', label: 'Site address', type: 'text', help: 'Where the game will be, like https://studio.example/game/: link previews (Discord, Slack, X) need it for their image' },
		{ path: 'description', label: 'Description', type: 'text', help: 'One or two sentences under the title in link previews and search results' },
		{ path: 'preview', label: 'Preview image', type: 'file', help: 'The picture in link previews: a PNG or JPEG, 1200x630 is best. Empty: the icon' },
	],
	android: [
		{ path: 'format', label: 'Package', type: 'select', options: [['apk', 'APK (install directly)'], ['aab', 'App bundle (.aab, for Google Play)']] },
		{ path: 'data', label: 'Data', type: 'select', options: [DATA_XP3, DATA_FOLDER] },
		{ path: 'applicationId', label: 'Application ID', type: 'text', help: 'Like com.studio.game; it can\'t change once the game is on Google Play' },
		{ path: 'versionCode', label: 'Version code', type: 'number', min: 0, help: '0 = from the version (1.2.3 is 10203); each upload to Google Play needs a higher one' },
		{ path: 'keystore', label: 'Keystore', type: 'file', help: 'Empty: a debug key (for testing). The passwords are asked for when building' },
		{ path: 'keyAlias', label: 'Key alias', type: 'text', showIf: (p) => !!p.keystore },
	],
	ios: [
		{ path: 'target', label: 'Build for', type: 'select', options: [['device', 'iPhone and iPad (.ipa, signed)'], ['simulator', 'The iOS Simulator (unsigned)']] },
		{ path: 'data', label: 'Data', type: 'select', options: [DATA_XP3, DATA_FOLDER] },
		{ path: 'bundleId', label: 'Bundle ID', type: 'text', help: 'Like com.studio.game; it must match the provisioning profile' },
		{ path: 'buildNumber', label: 'Build number', type: 'number', min: 0, help: '0 = from the version' },
		{ path: 'identity', label: 'Certificate', type: 'text', showIf: (p) => p.target === 'device', help: 'Apple Development: ... or Apple Distribution: ... (in your keychain)' },
		{ path: 'profile', label: 'Provisioning profile', type: 'file', showIf: (p) => p.target === 'device' },
	],
};

//---------------------------------------------------------------------------
// Fields
//---------------------------------------------------------------------------
const fieldIssues = new Map();   // settings path -> element showing its problems

function relativePath(p) {
	const root = state.project.root.replace(/\/+$/, '');
	if (p === root) return '.';
	if (p.startsWith(root + '/')) return p.slice(root.length + 1);
	return p;
}

// A settings path as an absolute one (settings paths are relative to the game's folder)
function absolutePath(p) {
	if (p.startsWith('/') || /^[A-Za-z]:[\\/]/.test(p)) return p;
	return state.project.root.replace(/\/+$/, '') + '/' + p;
}

function parentFolder(p) {
	const t = p.replace(/[\\/]+$/, '');
	const i = Math.max(t.lastIndexOf('/'), t.lastIndexOf('\\'));
	return i > 0 ? t.slice(0, i) : t;
}

function input(f, path, value, onChange) {
	switch (f.type) {
		case 'check': {
			const box = el('input', { type: 'checkbox', checked: !!value, onchange: (e) => onChange(e.target.checked) });
			return el('label', { class: 'check' }, box, f.text || '');
		}
		case 'select': {
			const s = el('select', { onchange: (e) => onChange(e.target.value) },
				f.options.map(([v, t]) => el('option', { value: v, selected: v === value }, t)));
			return el('div', { class: 'field' }, s);
		}
		case 'number': {
			const n = el('input', { type: 'number', value: value ?? 0, min: f.min, max: f.max,
				oninput: (e) => { const v = parseInt(e.target.value, 10); if (!Number.isNaN(v)) onChange(v); } });
			return el('div', { class: 'field' }, n);
		}
		case 'lines': {
			const t = el('textarea', { rows: Math.max(3, (value || []).length + 1), spellcheck: 'false',
				oninput: (e) => onChange(e.target.value.split('\n').map((x) => x.trim()).filter((x) => x)) });
			t.value = (value || []).join('\n');
			return t;
		}
		case 'kbps': {
			const rows = Object.entries(value || {});
			const table = el('table', { class: 'kv' });
			const emit = () => {
				const out = {};
				for (const tr of table.querySelectorAll('tr[data-row]')) {
					const k = tr.querySelector('input[type=text]').value.trim();
					const v = parseInt(tr.querySelector('input[type=number]').value, 10);
					if (k && !Number.isNaN(v)) out[k] = v;
				}
				onChange(out);
			};
			const addRow = (k, v) => {
				const tr = el('tr', { 'data-row': '' },
					el('td', {}, el('input', { type: 'text', value: k, placeholder: 'folder', oninput: emit })),
					el('td', {}, el('input', { type: 'number', value: v, min: 6, max: 510, oninput: emit }), ' kbps'),
					el('td', {}, el('button', { title: 'Remove', onclick: () => { tr.remove(); emit(); } }, '×')));
				const addButtonRow = table.querySelector('tr.add');
				if (addButtonRow) addButtonRow.before(tr); else table.append(tr);
			};
			for (const [k, v] of rows) addRow(k, v);
			table.append(el('tr', { class: 'add' }, el('td', { colspan: 3 }, el('button', { onclick: () => { addRow('', 96); } }, 'Add a folder'))));
			return table;
		}
		case 'file':
		case 'folder': {
			const t = el('input', { type: 'text', value: value ?? '', spellcheck: 'false', oninput: (e) => onChange(e.target.value) });
			const b = el('button', { onclick: async () => {
				const start = t.value ? state.project.root + '/' + t.value : state.project.root;
				const picked = f.type === 'file' ? await pickPath(start, true) : await pickPath(start, false);
				if (picked != null) { t.value = relativePath(picked); onChange(t.value); }
			} }, 'Browse…');
			return el('div', { class: 'field' }, t, b);
		}
		case 'keyfile': {
			// the archive key: picked, or made here (outside the game's folder by default)
			const t = el('input', { type: 'text', value: value ?? '', spellcheck: 'false', placeholder: 'No key chosen', oninput: (e) => onChange(e.target.value) });
			const choose = (p) => { t.value = relativePath(p); onChange(t.value); };
			const outside = parentFolder(state.project.root);
			const browse = el('button', { onclick: async () => {
				const picked = await pickPath(t.value ? absolutePath(t.value) : outside, true);
				if (picked != null) choose(picked);
			} }, 'Browse…');
			const create = el('button', { onclick: async () => {
				const folder = await pickPath(t.value ? parentFolder(absolutePath(t.value)) : outside, false);
				if (folder == null) return;
				const name = await promptBox('Create a key', 'A new random key is saved in ' + folder + '. Keep it out of the game\'s repository, and back it up.',
					'File name', (get(settings, 'identity.exeName') || 'game') + '.key', 'Create');
				if (!name) return;
				try {
					const r = await app.post('/api/release/archive-keygen', { path: folder.replace(/[\\/]+$/, '') + '/' + name });
					choose(r.path);
					alertBox('Key created', 'Saved a new key to ' + r.path + '. Back it up: a game released with it can only be rebuilt or patched with the same key, and anyone who has it can read the encrypted files.');
				} catch (e) {
					alertBox('Couldn\'t create the key', String(e.message || e));
				}
			} }, 'Create key…');
			return el('div', { class: 'field' }, t, browse, create);
		}
		case 'note':
			return el('div', { class: 'muted' }, f.text || '');
		default: {
			const t = el('input', { type: 'text', value: value ?? '', spellcheck: 'false', oninput: (e) => onChange(e.target.value) });
			return el('div', { class: 'field' }, t);
		}
	}
}

// Renders fields into a grid. base: the settings path the fields are relative to ('' or
// 'platforms.android'); scope: the object showIf gets
function renderFields(grid, fields, base) {
	grid.replaceChildren();
	const scope = base ? get(settings, base) : settings;
	for (const f of fields) {
		if (f.showIf && !f.showIf(scope)) continue;
		if (!f.path) {   // text only (a note), no setting
			grid.append(el('label', {}, f.label || ''), input(f, '', undefined, () => {}));
			continue;
		}
		const path = base ? base + '.' + f.path : f.path;
		grid.append(el('label', {}, f.label));
		grid.append(input(f, path, get(settings, path), (v) => {
			set(settings, path, v);
			changed();
			if (fields.some((x) => x.showIf)) renderFields(grid, fields, base);   // dependent fields
			if (base.startsWith('platforms.')) refreshHost(base.split('.')[1]);
		}));
		if (f.help) grid.append(el('div', { class: 'help' }, f.help));
		const iss = el('div', { class: 'issue' });
		fieldIssues.set(path, iss);
		grid.append(iss);
	}
	showFieldIssues();
}

//---------------------------------------------------------------------------
// Platforms
//---------------------------------------------------------------------------
function statusBadge(id) {
	const st = hostStatus[id];
	if (!st) return el('span', { class: 'status pending' }, 'checking…');
	return st.possible ? el('span', { class: 'status ok' }, 'can build here') : el('span', { class: 'status bad' }, 'can\'t build here');
}

function renderPlatforms(body) {
	body.replaceChildren();
	for (const p of state.platforms) {
		const base = 'platforms.' + p.id;
		const enabled = !!get(settings, base + '.enabled');
		const head = el('div', { class: 'platform-head' },
			el('input', { type: 'checkbox', id: 'pl-' + p.id, checked: enabled, onchange: (e) => {
				set(settings, base + '.enabled', e.target.checked);
				changed();
				renderPlatforms(body);
			} }),
			el('label', { class: 'name', for: 'pl-' + p.id }, p.title),
			el('span', { 'data-status': p.id }, statusBadge(p.id)));
		const card = el('div', { class: 'platform' }, head);
		if (enabled) {
			const reqs = el('ul', { class: 'reqs', 'data-reqs': p.id });
			fillReqs(reqs, p.id);
			const grid = el('div', { class: 'grid' });
			renderFields(grid, PLATFORM_FIELDS[p.id] || [], base);
			card.append(el('div', { class: 'platform-body' }, reqs, grid));
		}
		body.append(card);
	}
}

function fillReqs(ul, id) {
	ul.replaceChildren();
	const st = hostStatus[id];
	if (!st) return;
	for (const r of st.requirements) ul.append(el('li', { class: r.ok ? 'ok' : 'bad' }, el('b', {}, r.name), ': ', r.detail));
	for (const n of st.notes) ul.append(el('li', { class: 'note' }, n));
}

function showHost(id) {
	for (const e of document.querySelectorAll(`[data-status="${id}"]`)) e.replaceChildren(statusBadge(id));
	for (const e of document.querySelectorAll(`[data-reqs="${id}"]`)) fillReqs(e, id);
}

const hostTimers = {};
function refreshHost(id) {
	clearTimeout(hostTimers[id]);
	hostTimers[id] = setTimeout(async () => {
		try {
			const list = await app.post('/api/release/host', { settings, platform: id });
			for (const st of list) { hostStatus[st.id] = st; showHost(st.id); }
		} catch (e) { /* shown on the next check */ }
	}, 600);
}

//---------------------------------------------------------------------------
// Signing
//---------------------------------------------------------------------------
function renderSigning(body) {
	body.replaceChildren();
	const grid = el('div', { class: 'grid' });
	body.append(grid);
	renderFields(grid, SIGNING_FIELDS, 'signing');
	if (get(settings, 'signing.enabled')) {
		const status = el('span', { class: 'muted' });
		const btn = el('button', { onclick: () => createKeyPair(status) }, 'Create key pair…');
		body.append(el('div', { class: 'platform-body' }, btn, ' ', status));
	}
}

async function createKeyPair(status) {
	const dir = await pickPath(state.project.root, false);
	if (dir == null) return;
	status.textContent = 'Generating…';
	try {
		const r = await app.post('/api/release/keygen', { bits: 2048, privatePath: dir + '/signing-private.txt', publicPath: dir + '/signing-public.txt' });
		set(settings, 'signing.privateKey', relativePath(r.privatePath));
		changed();
		build();   // re-render so the key field shows the new path
		alertBox('Key pair created', 'Private key: ' + r.privatePath + '\nPublic key: ' + r.publicPath +
			'\n\nKeep the private key secret and out of version control — back it up, or you can\'t sign updates that verify against the same public key. It is now set as the signing key.');
	} catch (e) {
		status.textContent = '';
		alertBox('Could not create the key', String(e.message || e) + '\n\nChoose a folder without a signing-private.txt already in it.');
	}
}

//---------------------------------------------------------------------------
// Check: problems and the plan
//---------------------------------------------------------------------------
function renderPlan(body) {
	body.replaceChildren();
	const errors = issues.filter((i) => i.level === 'error');
	if (issues.length) {
		body.append(el('ul', { class: 'issues' }, issues.map((i) =>
			el('li', { class: i.level }, i.level === 'error' ? 'Error: ' : 'Warning: ', i.message, ' ',
				el('a', { href: '#', onclick: (e) => { e.preventDefault(); focusField(i.field); } }, '(' + i.field + ')')))));
	} else {
		body.append(el('p', {}, 'No problems found.'));
	}
	if (!plan) return;
	const d = plan.data;
	body.append(el('p', {},
		`Game files: ${d.files} (${formatSize(d.bytes)}), ${d.excluded} left out. Framework: ${d.framework}. `,
		`To convert: ${d.convertImages} images, ${d.convertAudio} sounds.`,
		d.compileScripts ? ` To compile: ${d.compileScripts} scripts.` : ''));
	const outs = el('div', { class: 'outputs' });
	for (const o of plan.outputs) {
		const st = hostStatus[o.platform];
		outs.append(el('div', { class: 'output' },
			el('div', { class: 'name' }, o.title, ' ', st && !st.possible ? el('span', { class: 'status bad' }, 'can\'t build here') : null),
			o.folder ? el('div', {}, 'Folder: ', el('code', {}, o.folder + '/')) : null,
			o.package ? el('div', {}, 'Package: ', el('code', {}, o.package)) : null,
			el('div', { class: 'muted' }, o.contents.join(' · '))));
	}
	body.append(outs);
	if (d.byExtension?.length) {
		body.append(el('details', {}, el('summary', {}, 'Files by type'),
			el('table', { class: 'plan' }, el('tr', {}, el('th', {}, 'Type'), el('th', {}, 'Files'), el('th', {}, 'Size')),
				d.byExtension.map((x) => el('tr', {}, el('td', {}, x.ext), el('td', { class: 'num' }, x.files), el('td', { class: 'num' }, formatSize(x.bytes)))))));
	}
	if (errors.length) body.append(el('p', { class: 'muted' }, 'Fix the errors above before building.'));
}

function focusField(field) {
	const target = fieldIssues.get(field);
	if (target) {
		target.scrollIntoView({ behavior: 'smooth', block: 'center' });
		const prev = target.previousElementSibling?.previousElementSibling;
		prev?.querySelector?.('input,select,textarea')?.focus();
		return;
	}
	const section = field.startsWith('platforms') ? 'platforms' : field.split('.')[0];
	document.getElementById('sec-' + ({ identity: 'game', engine: 'output' }[section] || section))?.scrollIntoView({ behavior: 'smooth' });
}

function showFieldIssues() {
	for (const [path, e] of fieldIssues) {
		const mine = issues.filter((i) => i.field === path);
		e.className = 'issue' + (mine.some((i) => i.level === 'error') ? ' error' : mine.length ? ' warning' : '');
		e.textContent = mine.map((i) => i.message).join(' ');
	}
	// counts in the side bar
	for (const sec of SECTIONS) {
		const badge = document.querySelector(`[data-badge="${sec.id}"]`);
		if (!badge) continue;
		const prefix = { game: ['identity'], platforms: ['platforms'], media: ['media'], contents: ['contents'], output: ['output', 'engine'], signing: ['signing'], encryption: ['archive'], plan: [''] }[sec.id] || [];
		const mine = issues.filter((i) => prefix.some((p) => i.field.startsWith(p)));
		const errs = mine.filter((i) => i.level === 'error').length;
		badge.textContent = errs || mine.length || '';
		badge.className = 'badge' + (errs ? ' bad' : mine.length ? ' warn' : '');
		badge.hidden = !mine.length;
	}
}

let checkTimer = 0;
function scheduleCheck() {
	clearTimeout(checkTimer);
	checkTimer = setTimeout(async () => {
		try {
			const r = await app.post('/api/release/check', { settings });
			issues = r.issues;
			plan = r.plan;
		} catch (e) {
			issues = [{ level: 'error', field: '', message: String(e.message || e) }];
		}
		showFieldIssues();
		renderPlan($('#sec-plan .body'));
	}, 300);
}

//---------------------------------------------------------------------------
// Saving
//---------------------------------------------------------------------------
const dirty = () => JSON.stringify(settings) !== savedText;
function showSaveState() {
	$('#saveState').textContent = !state.exists && !dirty() ? 'release.json not saved yet' : dirty() ? 'Unsaved changes' : 'Saved';
	$('#save').disabled = state.exists && !dirty();
}
function changed() {
	showSaveState();
	scheduleCheck();
}
async function save() {
	try {
		await app.post('/api/release/save', { settings });
		savedText = JSON.stringify(settings);
		state.exists = true;
		showSaveState();
	} catch (e) {
		alertBox('Could not save', String(e.message || e));
	}
}
window.addEventListener('keydown', (e) => {
	if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); save(); }
});
window.addEventListener('beforeunload', (e) => { if (settings && dirty()) { e.preventDefault(); e.returnValue = ''; } });

//---------------------------------------------------------------------------
// Building
//---------------------------------------------------------------------------
let buildDialog = null;

async function startBuild() {
	if (issues.some((i) => i.level === 'error')) {
		alertBox('Can\'t build yet', 'Fix the errors the Check section lists first.');
		return;
	}
	if (dirty() || !state.exists) await save();
	// keystore passwords are asked for each build and never saved
	const secrets = {};
	const android = settings.platforms.android;
	if (android.enabled && android.keystore) {
		const pw = await passwordBox('Android signing', `The passwords of ${android.keystore} (key "${android.keyAlias}"). They aren't saved.`,
			[['androidStorePassword', 'Keystore password'], ['androidKeyPassword', 'Key password (empty: the same)']]);
		if (!pw) return;
		Object.assign(secrets, pw);
	}
	try {
		await app.post('/api/release/build', { settings, secrets });
	} catch (e) {
		alertBox('Could not start the build', String(e.message || e));
		return;
	}
	openBuildDialog();
}

function openBuildDialog() {
	if (buildDialog) return;
	const bar = el('div', { class: 'progress indeterminate' }, el('div'));
	const message = el('div', {}, 'Starting…');
	const log = el('pre', { class: 'build-log' });
	const results = el('div', { class: 'results' });
	const cancel = el('button', {}, 'Cancel');
	const close = el('button', { class: 'primary', hidden: true }, 'Close');
	const title = el('div', { class: 'dialog-title' }, 'Building');
	const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog build-dialog' },
		title, bar, message, results, log, el('div', { class: 'dialog-buttons' }, cancel, close)));
	document.body.append(dlg);
	cancel.addEventListener('click', () => app.post('/api/job/cancel', {}).catch(() => {}));
	close.addEventListener('click', () => { dlg.remove(); buildDialog = null; });
	buildDialog = { bar, message, log, results, cancel, close, title, shown: false };
}

function showJob(st) {
	if (!st || st.name !== 'build') return;
	if (st.state === 'running') openBuildDialog();
	const d = buildDialog;
	if (!d) return;
	const running = st.state === 'running';
	d.bar.className = 'progress' + (running && !(st.ratio >= 0) ? ' indeterminate' : '');
	d.bar.firstChild.style.width = (st.ratio >= 0 ? st.ratio * 100 : running ? 30 : 100) + '%';
	d.message.textContent = st.message || '';
	if (running || d.shown) return;
	d.shown = true;
	d.cancel.hidden = true;
	d.close.hidden = false;
	const r = st.result || {};
	const ok = st.state === 'done' && r.ok;
	d.title.textContent = st.state === 'canceled' ? 'Build canceled' : ok ? 'Built' : 'Built with problems';
	if (st.error || r.error) d.results.append(el('div', { class: 'result bad' }, el('span', { class: 'mark' }, '✗'), el('div', { class: 'what' }, st.error || r.error)));
	for (const o of r.outputs || []) {
		const where = o.package || o.folder;
		d.results.append(el('div', { class: 'result ' + (o.ok ? 'ok' : 'bad') },
			el('span', { class: 'mark' }, o.ok ? '✓' : '✗'),
			el('div', { class: 'what' }, el('b', {}, o.title), ' ',
				o.ok ? [el('span', { class: 'muted' }, formatSize(o.bytes)), el('br'), el('code', {}, where)] : [el('br'), o.error]),
			o.ok ? el('button', { onclick: () => app.post('/api/release/reveal', { path: where }).catch(() => {}) }, 'Show') : null));
	}
	if (r.check) {
		const c = r.check;
		const tested = c.ran && !c.inconclusive;
		d.results.append(el('div', { class: 'result ' + (!tested ? '' : c.ok ? 'ok' : 'bad') },
			el('span', { class: 'mark' }, !tested ? 'i' : c.ok ? '✓' : '✗'),
			el('div', { class: 'what' }, el('b', {}, 'Test run'), ' ', c.message, (c.errors || []).map((e) => [el('br'), el('code', {}, e)])),
			c.log ? el('button', { onclick: () => app.post('/api/release/reveal', { path: c.log }).catch(() => {}) }, 'Log') : null));
	}
	if (r.media && (r.media.images || r.media.sounds)) {
		const m = r.media;
		d.results.append(el('div', { class: 'result ok' }, el('span', { class: 'mark' }, '✓'),
			el('div', { class: 'what' }, el('b', {}, 'Media'), ` ${m.images} images and ${m.sounds} sounds converted`,
				m.fromCache ? ` (${m.fromCache} from earlier builds)` : '', `: ${formatSize(m.bytesBefore)} → ${formatSize(m.bytesAfter)}`,
				m.rewrittenScripts ? `; names rewritten in ${m.rewrittenScripts} scripts` : '')));
	}
	if (r.scripts) {
		const sc = r.scripts;
		d.results.append(el('div', { class: 'result ok' }, el('span', { class: 'mark' }, '✓'),
			el('div', { class: 'what' }, el('b', {}, 'Scripts'), ` ${sc.compiled} compiled to bytecode`,
				sc.kept.length ? `, ${sc.kept.length} kept as source (below)` : ''),
			sc.log ? el('button', { onclick: () => app.post('/api/release/reveal', { path: sc.log }).catch(() => {}) }, 'Log') : null));
	}
	for (const n of r.notes || []) d.results.append(el('div', { class: 'result' }, el('span', { class: 'mark' }, 'i'), el('div', { class: 'what' }, n)));
	if (r.outputFolder) d.results.append(el('div', {}, el('button', { onclick: () => app.post('/api/release/reveal', { path: r.outputFolder }).catch(() => {}) }, 'Open the output folder')));
}

function jobLog(line) {
	const d = buildDialog;
	if (!d) return;
	d.log.append(String(line) + '\n');
	d.log.scrollTop = d.log.scrollHeight;
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

function passwordBox(title, text, fields) {
	return new Promise((resolve) => {
		const inputs = fields.map(([key, label]) => [key, el('input', { type: 'password', autocomplete: 'off', 'aria-label': label })]);
		const cancel = el('button', {}, 'Cancel');
		const go = el('button', { class: 'primary' }, 'Build');
		const grid = el('div', { class: 'grid' }, inputs.map(([key, input], i) => [el('label', {}, fields[i][1]), el('div', { class: 'field' }, input)]));
		const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' },
			el('div', { class: 'dialog-title' }, title), el('div', { class: 'muted' }, text), grid, el('div', { class: 'dialog-buttons' }, cancel, go)));
		const done = (v) => { dlg.remove(); resolve(v); };
		cancel.addEventListener('click', () => done(null));
		go.addEventListener('click', () => done(Object.fromEntries(inputs.map(([k, i]) => [k, i.value]))));
		for (const [, i] of inputs) i.addEventListener('keydown', (e) => { if (e.key === 'Enter') go.click(); });
		document.body.append(dlg);
		inputs[0][1].focus();
	});
}

// One line of text (null when canceled)
function promptBox(title, text, label, initial, yes) {
	return new Promise((resolve) => {
		const box = el('input', { type: 'text', spellcheck: 'false', 'aria-label': label });
		box.value = initial || '';
		const cancel = el('button', {}, 'Cancel');
		const go = el('button', { class: 'primary' }, yes || 'OK');
		const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' },
			el('div', { class: 'dialog-title' }, title), el('div', { class: 'muted' }, text),
			el('div', { class: 'grid' }, el('label', {}, label), el('div', { class: 'field' }, box)),
			el('div', { class: 'dialog-buttons' }, cancel, go)));
		const done = (v) => { dlg.remove(); resolve(v); };
		cancel.addEventListener('click', () => done(null));
		go.addEventListener('click', () => { const v = box.value.trim(); if (v) done(v); });
		box.addEventListener('keydown', (e) => { if (e.key === 'Enter') go.click(); if (e.key === 'Escape') cancel.click(); });
		document.body.append(dlg);
		box.focus();
		box.select();
	});
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

// A file or folder from this computer (the browser has no native dialog for that)
function pickPath(initial, files) {
	return new Promise(async (resolve) => {
		const pathInput = el('input', { type: 'text', spellcheck: 'false' });
		const list = el('div', { class: 'picker-list' });
		const roots = el('div', { class: 'picker-roots' });
		const ok = el('button', { class: 'primary' }, files ? 'Choose' : 'Choose this folder');
		const cancel = el('button', {}, 'Cancel');
		const dlg = el('div', { class: 'modal' }, el('div', { class: 'dialog' },
			el('div', { class: 'dialog-title' }, files ? 'Choose a file' : 'Choose a folder'),
			roots, pathInput, list,
			el('div', { class: 'muted' }, files ? 'Click a file to choose it; double-click a folder to open it.' : 'Double-click a folder to open it.'),
			el('div', { class: 'dialog-buttons' }, cancel, ok)));
		document.body.append(dlg);
		let selected = null;
		const close = (v) => { dlg.remove(); resolve(v); };
		cancel.addEventListener('click', () => close(null));
		ok.addEventListener('click', () => {
			if (!files) return close(pathInput.value);
			if (selected) close(selected);
		});
		const open = async (path) => {
			let r;
			try { r = await app.get('/api/fs/list', { path }); }
			catch (e) {
				// a file was given: open its folder
				const slash = path.lastIndexOf('/');
				if (slash > 0 && path !== initial.slice(0, slash)) return open(path.slice(0, slash));
				list.textContent = String(e.message || e);
				return;
			}
			pathInput.value = r.path;
			selected = null;
			list.replaceChildren();
			if (r.parent) list.append(el('div', { class: 'picker-item dir', ondblclick: () => open(r.parent) }, '..'));
			const sorted = r.entries.slice().sort((a, b) => (b.dir - a.dir) || a.name.localeCompare(b.name));
			for (const e of sorted) {
				if (e.dir) list.append(el('div', { class: 'picker-item dir', ondblclick: () => open(e.path) }, e.name));
				else if (files) {
					const item = el('div', { class: 'picker-item' }, e.name);
					item.addEventListener('click', () => {
						selected = e.path;
						for (const x of list.querySelectorAll('.selected')) x.classList.remove('selected');
						item.classList.add('selected');
					});
					item.addEventListener('dblclick', () => close(e.path));
					list.append(item);
				}
			}
		};
		pathInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') open(pathInput.value); });
		try {
			const rr = await app.get('/api/fs/roots');
			for (const root of rr.roots) roots.append(el('button', { onclick: () => open(root.path) }, root.label || root.path));
		} catch (e) { /* the path can still be typed */ }
		open(initial || '.');
	});
}

//---------------------------------------------------------------------------
// Start
//---------------------------------------------------------------------------
function build() {
	const nav = $('#nav'), main = $('#main');
	nav.replaceChildren();
	main.replaceChildren();
	fieldIssues.clear();
	for (const sec of SECTIONS) {
		nav.append(el('a', { href: '#sec-' + sec.id, onclick: (e) => {
			e.preventDefault();
			document.getElementById('sec-' + sec.id).scrollIntoView({ behavior: 'smooth' });
		} }, sec.title, el('span', { class: 'badge', 'data-badge': sec.id, hidden: true })));
		const body = el('div', { class: sec.fields ? 'grid body' : 'body' });
		main.append(el('section', { class: 'card', id: 'sec-' + sec.id },
			el('h2', {}, sec.title), sec.intro ? el('p', { class: 'intro' }, sec.intro) : null, body));
		if (sec.fields) renderFields(body, sec.fields, '');
		else sec.render(body);
	}
	// highlight the section in view
	const io = new IntersectionObserver((entries) => {
		for (const en of entries) {
			if (!en.isIntersecting) continue;
			for (const a of nav.querySelectorAll('a')) a.classList.toggle('active', a.getAttribute('href') === '#' + en.target.id);
		}
	}, { rootMargin: '-60px 0px -60% 0px' });
	for (const s of main.querySelectorAll('section')) io.observe(s);
}

async function load() {
	state = await app.get('/api/release/state');
	$('#version').textContent = state.version;
	if (!state.project) {
		$('#fatal').hidden = false;
		$('#fatal').textContent = (state.error || 'No game found') + '\nUse Open… to choose the folder that holds your game\'s data folder.';
		$('#projectPath').textContent = '';
		$('#save').disabled = true;
		$('#build').disabled = true;
		return;
	}
	$('#build').disabled = false;
	$('#fatal').hidden = !state.error;
	$('#fatal').textContent = state.error || '';
	// cut from the start when it doesn't fit (the end of a path says the most)
	$('#projectPath').replaceChildren(el('bdi', { dir: 'ltr' }, state.file));
	$('#projectPath').title = state.file;
	settings = state.settings;
	savedText = state.exists ? JSON.stringify(settings) : '';
	build();
	showSaveState();
	scheduleCheck();
	// what this computer can build, for every platform (takes a moment)
	app.post('/api/release/host', { settings }).then((list) => {
		for (const st of list) { hostStatus[st.id] = st; showHost(st.id); }
		renderPlan($('#sec-plan .body'));
	}).catch(() => {});
}

$('#save').addEventListener('click', save);
$('#build').addEventListener('click', startBuild);
$('#openProject').addEventListener('click', async () => {
	if (settings && dirty() && !(await confirmBox('Unsaved changes', 'Open another game without saving these settings?', 'Open'))) return;
	const dir = await pickPath(state?.project?.root || '.', false);
	if (dir == null) return;
	try {
		await app.post('/api/release/open', { path: dir });
		for (const k of Object.keys(hostStatus)) delete hostStatus[k];
		await load();
	} catch (e) {
		alertBox('No game there', String(e.message || e));
	}
});

await app.ready();
await load();
app.on('job', showJob);
app.on('joblog', jobLog);
// a build that was running when the window was opened again
app.get('/api/job').then(showJob).catch(() => {});
