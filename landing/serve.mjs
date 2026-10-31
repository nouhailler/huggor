// Serveur statique minimal pour contrôler dist/ en local : node serve.mjs [port]
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), 'dist');
const port = Number(process.argv[2] ?? 8788);

// Applique les règles de dist/_headers (format Cloudflare Pages) pour tester aussi la CSP en local.
const headerRules = [];
try {
  let current = null;
  for (const line of (await readFile(path.join(root, '_headers'), 'utf8')).split('\n')) {
    if (!line.trim()) continue;
    if (!/^\s/.test(line)) {
      current = { pattern: line.trim(), headers: {} };
      headerRules.push(current);
    } else if (current) {
      const index = line.indexOf(':');
      current.headers[line.slice(0, index).trim()] = line.slice(index + 1).trim();
    }
  }
} catch {
  // Pas de fichier _headers : aucun en-tête supplémentaire.
}
const matches = (pattern, pathname) => (pattern.endsWith('/*') ? pathname.startsWith(pattern.slice(0, -1)) || pattern === '/*' : pattern === pathname);
const extraHeaders = (pathname) => Object.assign({}, ...headerRules.filter((rule) => matches(rule.pattern, pathname)).map((rule) => rule.headers));
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.webmanifest': 'application/manifest+json',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml',
};

createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  const relative = pathname.endsWith('/') ? `${pathname}index.html` : pathname;
  const file = path.normalize(path.join(root, relative));
  if (!file.startsWith(root)) {
    response.writeHead(403).end();
    return;
  }
  try {
    const body = await readFile(file);
    response.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] ?? 'application/octet-stream', ...extraHeaders(pathname === '/' ? '/index.html' : pathname) });
    response.end(body);
  } catch {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('Introuvable');
  }
}).listen(port, '127.0.0.1', () => console.log(`http://127.0.0.1:${port}/`));
