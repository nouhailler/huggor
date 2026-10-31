import { GIB, COMFORTABLE_MARGIN, estimate } from '/estimator.js';

// Menu mobile
const toggle = document.querySelector('.menu-toggle');
const nav = document.getElementById('menu-principal');
if (toggle && nav) {
  const setOpen = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('open', open);
  };
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  nav.addEventListener('click', (event) => {
    if (event.target.closest('a')) setOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
}

// Copie des commandes (boutons .copy-button, cible indiquée par data-target)
for (const copyButton of document.querySelectorAll('.copy-button')) {
  copyButton.addEventListener('click', async () => {
    const target = document.getElementById(copyButton.dataset.target);
    try {
      await navigator.clipboard.writeText(target?.textContent?.trim() ?? '');
      copyButton.textContent = 'Copié';
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(target);
      selection.removeAllRanges();
      selection.addRange(range);
      copyButton.textContent = 'Sélectionné : Ctrl+C';
    }
    setTimeout(() => { copyButton.textContent = 'Copier'; }, 2500);
  });
}

// Simulateur illustratif
const form = document.getElementById('estimator-form');
if (form) {
  const preset = document.getElementById('est-preset');
  const paramsLabel = document.getElementById('est-params-label');
  const paramsInput = document.getElementById('est-params');
  const ramInput = document.getElementById('est-ram');
  const vramInput = document.getElementById('est-vram');
  const summary = document.getElementById('est-summary');
  const chart = document.getElementById('est-chart');
  const tableBody = document.querySelector('#est-table tbody');

  const number = (input, fallback) => {
    const value = Number.parseFloat(String(input.value).replace(',', '.'));
    return Number.isFinite(value) && value >= 0 ? value : fallback;
  };
  const gio = (bytes) => `≈ ${(bytes / GIB).toFixed(1).replace('.', ',')} Gio`;
  const VERDICTS = { ok: '✓ Tient confortablement', warning: '! À la limite', no: '✗ Ne tient pas' };
  const PATHS = { gpu: 'sur la VRAM (GPU)', cpu: 'sur la RAM (CPU)' };

  const render = () => {
    const billions = preset.value === 'custom' ? number(paramsInput, 0) : Number.parseFloat(preset.value);
    const ram = number(ramInput, 0);
    const vram = number(vramInput, 0);
    const result = estimate(billions, ram, vram);
    tableBody.replaceChildren();
    chart.replaceChildren();

    if (!result.precisions.length) {
      summary.textContent = 'Indiquez un nombre de paramètres positif pour lancer l\'estimation.';
      return;
    }

    const memories = result.precisions.map((item) => item.memoryBytes);
    const scale = Math.max(...memories, ram * GIB, vram * GIB) * 1.04;
    for (const item of result.precisions) {
      const row = document.createElement('tr');
      const cells = [item.label, gio(item.memoryBytes), VERDICTS[item.status]];
      cells.forEach((text, index) => {
        const cell = document.createElement(index === 0 ? 'th' : 'td');
        if (index === 0) cell.scope = 'row';
        if (index === 2) {
          cell.className = `verdict ${item.status}`;
          if (item.status !== 'no') cell.textContent = `${text} ${PATHS[item.path]}`;
          else cell.textContent = text;
        } else {
          cell.textContent = text;
        }
        row.append(cell);
      });
      tableBody.append(row);

      const line = document.createElement('div');
      line.className = 'chart-row';
      const name = document.createElement('span');
      name.textContent = item.label;
      const track = document.createElement('div');
      track.className = 'chart-track';
      const bar = document.createElement('div');
      bar.className = `chart-bar ${item.status}`;
      bar.style.width = `${(item.memoryBytes / scale) * 100}%`;
      track.append(bar);
      line.append(name, track);
      chart.append(line);
    }

    const limits = document.createElement('div');
    limits.className = 'chart-limits';
    for (const [kind, capacity, label] of [['ram', ram, 'RAM 85 %'], ['vram', vram, 'VRAM 85 %']]) {
      if (capacity <= 0) continue;
      const limit = document.createElement('div');
      limit.className = `chart-limit ${kind}`;
      limit.style.left = `${Math.min(100, ((capacity * GIB * COMFORTABLE_MARGIN) / scale) * 100)}%`;
      const text = document.createElement('span');
      text.textContent = label;
      limit.append(text);
      limits.append(limit);
    }
    chart.append(limits);

    const size = String(billions).replace('.', ',');
    if (result.best) {
      const speed = `${String(result.tpsLow).replace('.', ',')} à ${String(result.tpsHigh).replace('.', ',')} jetons/s`;
      summary.textContent = `Pour ${size} milliards de paramètres : la précision la plus fidèle qui tient est ${result.best} ${PATHS[result.path]}, avec une vitesse de l'ordre de ${speed} (repère générique, pas une mesure).`;
    } else {
      summary.textContent = `Pour ${size} milliards de paramètres : aucune précision ne tient dans la mémoire déclarée, même la plus compressée.`;
    }
  };

  preset.addEventListener('change', () => {
    paramsLabel.hidden = preset.value !== 'custom';
    render();
  });
  for (const input of [paramsInput, ramInput, vramInput]) input.addEventListener('input', render);
  form.addEventListener('submit', (event) => event.preventDefault());
  render();
}

// Service worker de la vitrine (indépendant de l'application HF Explorer)
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
  });
}
