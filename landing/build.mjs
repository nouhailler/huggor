// Construit le site statique : copie src/ vers dist/, injecte les URLs centralisées de
// site.config.json et, si possible, les informations de la dernière release publiée.
// Aucune dépendance : Node.js 18 ou supérieur suffit.

import { createHash } from 'node:crypto';
import { cp, mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const sourceDirectory = path.join(root, 'src');
const outputDirectory = path.join(root, 'dist');
const TEXT_EXTENSIONS = new Set(['.html', '.js', '.css', '.webmanifest', '.json', '.txt', '.xml', '.svg']);

const config = JSON.parse(await readFile(path.join(root, 'site.config.json'), 'utf8'));
const siteUrl = (process.env.SITE_URL ?? config.siteUrl ?? '').trim().replace(/\/+$/, '');
if (siteUrl && !/^https:\/\/[^\s/]+$/.test(siteUrl)) {
  throw new Error(`SITE_URL doit être une origine https sans chemin (reçu : ${siteUrl}).`);
}

async function lookupLatestRelease() {
  if (process.env.SKIP_RELEASE_LOOKUP === '1') {
    return null;
  }
  try {
    const response = await fetch(`https://api.github.com/repos/${config.downloadsRepository}/releases/latest`, {
      headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'huggor-landing-build' },
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const release = await response.json();
    const deb = release.assets?.find((asset) => /^hf-explorer_\d+\.\d+\.\d+_all\.deb$/.test(asset.name));
    if (!deb || !/^v\d+\.\d+\.\d+$/.test(release.tag_name)) {
      throw new Error('release sans paquet .deb reconnu');
    }
    const checksum = release.assets.find((asset) => asset.name === `${deb.name}.sha256`);
    return {
      version: release.tag_name.slice(1),
      tag: release.tag_name,
      debAsset: deb.name,
      checksumAsset: checksum?.name ?? '',
      publishedAt: release.published_at ?? '',
      debSize: deb.size ?? 0,
    };
  } catch (error) {
    console.warn(`[build] Release GitHub non lue (${error.message}) : valeurs de secours de site.config.json.`);
    return null;
  }
}

const looked = await lookupLatestRelease();
const release = looked ?? { ...config.fallbackRelease, publishedAt: '', debSize: 0 };
console.log(`[build] Release utilisée : ${release.tag} (${looked ? 'API GitHub' : 'secours'})`);

const releasesUrl = `${config.downloadsUrl}/releases`;
const downloadBase = `${releasesUrl}/download/${release.tag}`;
const frenchDate = release.publishedAt
  ? new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long', timeZone: 'UTC' }).format(new Date(release.publishedAt))
  : '';
const debSizeLabel = release.debSize ? `${Math.round(release.debSize / 1024)} Ko` : '';

const values = {
  APP_URL: config.appUrl,
  GITHUB_URL: config.githubUrl,
  DOWNLOADS_URL: config.downloadsUrl,
  HUB_URL: config.hubUrl,
  DOCS_URL: config.docsUrl,
  LEGAL_URL: config.legalUrl,
  ISSUES_URL: config.issuesUrl,
  CONTRIBUTING_URL: config.contributingUrl,
  RELEASES_URL: releasesUrl,
  RELEASE_VERSION: release.version,
  RELEASE_TAG: release.tag,
  RELEASE_DATE: frenchDate,
  DEB_SIZE: debSizeLabel,
  DEB_NAME: release.debAsset,
  DEB_URL: `${downloadBase}/${release.debAsset}`,
  CHECKSUM_URL: release.checksumAsset ? `${downloadBase}/${release.checksumAsset}` : releasesUrl,
  INSTALL_PAGE: '/installer/',
  INSTALL_URL: `https://raw.githubusercontent.com/${config.downloadsRepository}/main/install.sh`,
  INSTALL_COMMAND: `curl -fsSL https://raw.githubusercontent.com/${config.downloadsRepository}/main/install.sh | bash`,
};

const siteMetaFor = (pagePath) =>
  siteUrl
    ? [
        `<link rel="canonical" href="${siteUrl}${pagePath}">`,
        `<meta property="og:url" content="${siteUrl}${pagePath}">`,
        `<meta property="og:image" content="${siteUrl}/og-image.png">`,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        `<meta name="twitter:image" content="${siteUrl}/og-image.png">`,
      ].join('\n    ')
    : '<!-- SITE_URL non défini : canonical, og:url et og:image absolus omis. -->';

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((entry) => {
      const full = path.join(directory, entry.name);
      return entry.isDirectory() ? walk(full) : [full];
    }),
  );
  return files.flat();
}

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await cp(sourceDirectory, outputDirectory, { recursive: true });

for (const file of await walk(outputDirectory)) {
  if (!TEXT_EXTENSIONS.has(path.extname(file))) {
    continue;
  }
  let content = await readFile(file, 'utf8');
  content = content.replace(/<!--SITE_META:([^ ]*)-->/g, (match, pagePath) => siteMetaFor(pagePath));
  content = content.replace(/\{\{([A-Z_]+)\}\}/g, (match, key) => {
    if (key === 'BUILD_ID') {
      return match;
    }
    if (!(key in values)) {
      throw new Error(`Variable inconnue ${match} dans ${path.relative(outputDirectory, file)}`);
    }
    return values[key];
  });
  await writeFile(file, content);
}

const robots = ['User-agent: *', 'Allow: /'];
if (siteUrl) {
  robots.push('', `Sitemap: ${siteUrl}/sitemap.xml`);
  const lastModified = new Date().toISOString().slice(0, 10);
  await writeFile(
    path.join(outputDirectory, 'sitemap.xml'),
    `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>${siteUrl}/</loc><lastmod>${lastModified}</lastmod></url>\n  <url><loc>${siteUrl}/installer/</loc><lastmod>${lastModified}</lastmod></url>\n</urlset>\n`,
  );
}
await writeFile(path.join(outputDirectory, 'robots.txt'), `${robots.join('\n')}\n`);

// Identifiant de cache du service worker : change dès qu'un fichier publié change.
const hash = createHash('sha256');
for (const file of (await walk(outputDirectory)).sort()) {
  if (path.basename(file) !== 'sw.js') {
    hash.update(path.relative(outputDirectory, file));
    hash.update(await readFile(file));
  }
}
const serviceWorkerPath = path.join(outputDirectory, 'sw.js');
await writeFile(serviceWorkerPath, (await readFile(serviceWorkerPath, 'utf8')).replace('{{BUILD_ID}}', hash.digest('hex').slice(0, 12)));

// Garde-fou : aucun marqueur ne doit survivre dans le résultat publié.
for (const file of await walk(outputDirectory)) {
  if (TEXT_EXTENSIONS.has(path.extname(file)) && /\{\{[A-Z_]+\}\}/.test(await readFile(file, 'utf8'))) {
    throw new Error(`Marqueur non remplacé dans ${path.relative(outputDirectory, file)}`);
  }
}

const total = (await Promise.all((await walk(outputDirectory)).map(async (file) => (await stat(file)).size))).reduce((a, b) => a + b, 0);
console.log(`[build] dist/ prêt : ${Math.round(total / 1024)} Ko${siteUrl ? `, SITE_URL=${siteUrl}` : ', SITE_URL non défini'}.`);
