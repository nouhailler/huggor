// Reprend à l'identique la méthode de src/resource_calculator.py (précisions, marge d'exécution,
// seuil de confort, repères de bande passante). Illustration pédagogique : l'application, elle,
// part des métadonnées réelles du modèle et estime aussi le contexte via le cache KV.

export const GIB = 1024 ** 3;
export const RUNTIME_OVERHEAD = 1.1;
export const COMFORTABLE_MARGIN = 0.85;
export const GPU_BANDWIDTH_GBPS = 300;
export const CPU_BANDWIDTH_GBPS = 40;

export const PRECISIONS = [
  { label: 'FP32', bytesPerParameter: 4.0 },
  { label: 'FP16', bytesPerParameter: 2.0 },
  { label: 'INT8', bytesPerParameter: 1.0 },
  { label: 'Q8', bytesPerParameter: 1.0625 },
  { label: 'Q6', bytesPerParameter: 0.8203 },
  { label: 'Q4_K_M', bytesPerParameter: 0.6094 },
];

function fitPrecision(label, bytesPerParameter, parameters, ramBytes, vramBytes) {
  const memoryBytes = Math.trunc(parameters * bytesPerParameter * RUNTIME_OVERHEAD);
  if (vramBytes > 0 && memoryBytes <= vramBytes * COMFORTABLE_MARGIN) return { label, status: 'ok', memoryBytes, path: 'gpu' };
  if (ramBytes > 0 && memoryBytes <= ramBytes * COMFORTABLE_MARGIN) return { label, status: 'ok', memoryBytes, path: 'cpu' };
  if (vramBytes > 0 && memoryBytes <= vramBytes) return { label, status: 'warning', memoryBytes, path: 'gpu' };
  if (ramBytes > 0 && memoryBytes <= ramBytes) return { label, status: 'warning', memoryBytes, path: 'cpu' };
  return { label, status: 'no', memoryBytes, path: 'none' };
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

export function estimate(parametersBillions, ramGib, vramGib) {
  const parameters = Math.round(parametersBillions * 1e9);
  if (!(parameters > 0) || ramGib < 0 || vramGib < 0) {
    return { parameters, precisions: [], best: null, path: 'none', tpsLow: null, tpsHigh: null };
  }
  const ramBytes = ramGib * GIB;
  const vramBytes = vramGib * GIB;
  const precisions = PRECISIONS.map(({ label, bytesPerParameter }) => fitPrecision(label, bytesPerParameter, parameters, ramBytes, vramBytes));
  const best = ['ok', 'warning'].map((status) => precisions.find((item) => item.status === status)).find(Boolean) ?? null;
  if (!best || best.path === 'none') {
    return { parameters, precisions, best: null, path: 'none', tpsLow: null, tpsHigh: null };
  }
  const bandwidth = best.path === 'gpu' ? GPU_BANDWIDTH_GBPS : CPU_BANDWIDTH_GBPS;
  const tokensPerSecond = (bandwidth * 1e9) / best.memoryBytes;
  return {
    parameters,
    precisions,
    best: best.label,
    path: best.path,
    tpsLow: round1(tokensPerSecond * 0.6),
    tpsHigh: round1(tokensPerSecond * 1.4),
  };
}
