// Contrôle manuel dans un vrai navigateur (menu, simulateur, clavier, images, service worker, console).
// Prérequis : npm run build && npm run serve (port 8788), et Chromium lancé avec :
//   chromium --headless=new --remote-debugging-port=9334 --remote-allow-origins='*' --user-data-dir=/tmp/profil-test about:blank
// Usage : node tests/browser-check.mjs http://127.0.0.1:8788/
const BASE = process.argv[2];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t = await (await fetch('http://127.0.0.1:9334/json/new?about:blank', { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map(); const logs = [];
ws.onmessage = (m) => { const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  else if (msg.method === 'Runtime.consoleAPICalled') logs.push(`${msg.params.type}: ${msg.params.args.map(a=>a.value??a.description).join(' ')}`);
  else if (msg.method === 'Runtime.exceptionThrown') logs.push('EXCEPTION ' + JSON.stringify(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text));
  else if (msg.method === 'Log.entryAdded') logs.push(`log ${msg.params.entry.level}: ${msg.params.entry.text} ${msg.params.entry.url||''}`);
};
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, (m) => m.error ? rej(new Error(method+': '+m.error.message)) : res(m.result)); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails.exception?.description)); return r.result.value; };
const results = []; const check = (name, ok, info = '') => { results.push(ok); console.log(`${ok ? 'PASS' : 'FAIL'} ${name} ${info}`); };
await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');

// Desktop
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: BASE }); await sleep(2000);
await ev(`(async()=>{ for (let y=0;y<document.body.scrollHeight;y+=600){ window.scrollTo(0,y); await new Promise(r=>setTimeout(r,120)); } window.scrollTo(0,0); })()`);
await sleep(800);
check('toutes les images chargées', await ev(`[...document.images].every(i=>i.complete && i.naturalWidth>0)`), await ev(`[...document.images].map(i=>i.src.split('/').pop()+':'+i.naturalWidth).join(' ')`));
check('en-tête sur une ligne (desktop)', await ev(`document.querySelector('.header-bar').getBoundingClientRect().height < 90`), String(await ev(`Math.round(document.querySelector('.header-bar').getBoundingClientRect().height)`)));
check('pas de débordement horizontal 1440', await ev(`document.documentElement.scrollWidth <= document.documentElement.clientWidth`));
check('un seul h1', await ev(`document.querySelectorAll('h1').length===1`));
const headings = await ev(`[...document.querySelectorAll('h1,h2,h3')].map(h=>h.tagName).join(',')`);
check('hiérarchie des titres sans saut', !/H1,H3|H2,H4|H1,H4/.test(headings), headings);
check('images avec alt', await ev(`[...document.images].every(i=>i.hasAttribute('alt'))`));
check('chaque champ a un label', await ev(`[...document.querySelectorAll('input,select')].every(e=>document.querySelector('label[for="'+e.id+'"]'))`));

// Simulateur
check('champ personnalisé masqué au départ', (await ev(`getComputedStyle(document.getElementById('est-params-label')).display`)) === 'none');
check('simulateur : résumé initial', (await ev(`document.getElementById('est-summary').textContent`)).includes('Q6 sur la RAM'), await ev(`document.getElementById('est-summary').textContent`));
await ev(`(()=>{const s=document.getElementById('est-preset'); s.value='7'; s.dispatchEvent(new Event('change',{bubbles:true})); const v=document.getElementById('est-vram'); v.value='12'; v.dispatchEvent(new Event('input',{bubbles:true}));})()`);
const sum2 = await ev(`document.getElementById('est-summary').textContent`);
check('simulateur : 7 Md + 12 Gio VRAM → GPU', /sur la VRAM \(GPU\)/.test(sum2), sum2);
await ev(`(()=>{const s=document.getElementById('est-preset'); s.value='custom'; s.dispatchEvent(new Event('change',{bubbles:true})); const p=document.getElementById('est-params'); p.value='400'; p.dispatchEvent(new Event('input',{bubbles:true})); const r=document.getElementById('est-ram'); r.value='8'; r.dispatchEvent(new Event('input',{bubbles:true})); const v=document.getElementById('est-vram'); v.value='0'; v.dispatchEvent(new Event('input',{bubbles:true}));})()`);
check('simulateur : modèle trop grand', (await ev(`document.getElementById('est-summary').textContent`)).includes('aucune précision ne tient'));
check('champ personnalisé affiché', (await ev(`getComputedStyle(document.getElementById('est-params-label')).display`)) !== 'none');
check('lignes du tableau = 6', await ev(`document.querySelectorAll('#est-table tbody tr').length===6`));

// Clavier : premier Tab = lien d'évitement visible
await send('Page.navigate', { url: BASE }); await sleep(1500);
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
check('Tab → lien d\'évitement focalisé', await ev(`document.activeElement.classList.contains('skip-link')`));
check('focus visible (outline)', await ev(`getComputedStyle(document.activeElement).outlineStyle==='solid' && parseFloat(getComputedStyle(document.activeElement).outlineWidth)>=2`));

// Mobile : menu
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await send('Page.navigate', { url: BASE }); await sleep(1500);
check('menu fermé au départ', await ev(`getComputedStyle(document.getElementById('menu-principal')).display==='none'`));
await ev(`document.querySelector('.menu-toggle').click()`); await sleep(200);
check('menu ouvert (aria-expanded + visible)', await ev(`document.querySelector('.menu-toggle').getAttribute('aria-expanded')==='true' && getComputedStyle(document.getElementById('menu-principal')).display==='flex'`));
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }); await sleep(200);
check('Échap ferme le menu et rend le focus', await ev(`document.querySelector('.menu-toggle').getAttribute('aria-expanded')==='false' && document.activeElement===document.querySelector('.menu-toggle')`));
check('pas de débordement horizontal 390', await ev(`document.documentElement.scrollWidth <= document.documentElement.clientWidth`));
check('cibles tactiles ≥ 44 px (boutons principaux)', await ev(`[...document.querySelectorAll('.btn:not(.btn-small), .menu-toggle')].every(b=>b.getBoundingClientRect().height>=44 || b.getBoundingClientRect().height===0)`));

// Service worker
await send('Emulation.clearDeviceMetricsOverride');
await send('Page.navigate', { url: BASE }); await sleep(2500);
const sw = await ev(`(async()=>{ const reg = await navigator.serviceWorker.ready; const names = await caches.keys(); const cache = await caches.open(names[0]); const keys = (await cache.keys()).map(r=>new URL(r.url).pathname); return JSON.stringify({scope: new URL(reg.scope).pathname, names, keys}); })()`);
console.log('SW', sw);
const swo = JSON.parse(sw);
check('service worker actif, scope /', swo.scope === '/');
check('cache nommé huggor-landing-*', swo.names.length===1 && swo.names[0].startsWith('huggor-landing-'));
check('cache = ressources statiques du site uniquement', swo.keys.every((k)=>k.startsWith('/')) && swo.keys.includes('/styles.css'));
// manifest + icônes
const man = await ev(`(async()=>{ const m = await (await fetch('/manifest.webmanifest')).json(); const st = await Promise.all(m.icons.map(async i=>[i.src,(await fetch(i.src)).status])); return JSON.stringify({name:m.name,start:m.start_url,scope:m.scope,display:m.display,icons:st}); })()`);
console.log('MANIFEST', man);
check('manifeste + icônes 200', JSON.parse(man).icons.every(([,s])=>s===200));
console.log('LOGS', JSON.stringify(logs));
check('console sans erreur ni avertissement', logs.filter(l=>!l.startsWith('log info')).length===0);
console.log(results.every(Boolean) ? 'ALL PASS' : 'SOME FAIL');
await fetch(`http://127.0.0.1:9334/json/close/${t.id}`); ws.close();
