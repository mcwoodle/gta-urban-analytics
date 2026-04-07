// ========================================================================
// build-standalone.mjs — embed data + JS bundle into one HTML file
// ========================================================================
// Prereq: `yarn build` has already populated dist/ with index.html and
// bundle.js. This script reads:
//
//   data/02_transformed/standalone/unified_data_compact.csv
//   data/02_transformed/standalone/gta_census_da_compact.geojson
//   data/02_transformed/standalone/shooting_arcs.csv
//
// gzips and base64-encodes each payload, injects a <script> block defining
// window.__STANDALONE_MODE__ = true and window.__STANDALONE_DATA__ = {...},
// inlines dist/bundle.js into a second <script> block, and writes the
// combined document to dist/standalone.html.
//
// dist/index.html, dist/bundle.js, and dist/data/ are left untouched so
// the multi-file static site is still available.
// ========================================================================

import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const vizRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(vizRoot, '..');
const distDir = path.join(vizRoot, 'dist');
const standaloneDataDir = path.join(repoRoot, 'data', '02_transformed', 'standalone');

const DATASETS = [
  { key: 'crime_points',  file: 'unified_data_compact.csv' },
  { key: 'census_da',     file: 'gta_census_da_compact.geojson' },
  { key: 'shooting_arcs', file: 'shooting_arcs.csv' }
];

// -------------------------------------------------------------------------

function fail(msg) {
  console.error(`[build-standalone] ${msg}`);
  process.exit(1);
}

function mb(bytes) {
  return (bytes / (1024 * 1024)).toFixed(2);
}

/** Escape `</script>` sequences in arbitrary text so it's safe to embed
 *  inside a <script> tag. Base64 payloads don't contain this, but the
 *  minified JS bundle occasionally does. */
function escapeForScript(text) {
  return text.replace(/<\/script>/gi, '<\\/script>');
}

// -------------------------------------------------------------------------

async function main() {
  // Sanity-check prerequisites.
  const indexHtmlPath = path.join(distDir, 'index.html');
  const bundlePath = path.join(distDir, 'bundle.js');
  if (!fs.existsSync(indexHtmlPath) || !fs.existsSync(bundlePath)) {
    fail(
      `dist/index.html or dist/bundle.js missing. Run \`yarn build\` before ` +
        `running this script.`
    );
  }
  if (!fs.existsSync(standaloneDataDir)) {
    fail(
      `${standaloneDataDir} does not exist. Run \`uv run transform\` (or at ` +
        `least the build_standalone_compact step) from the repo root first.`
    );
  }

  // Read + gzip + base64 each compact dataset.
  const embedded = {};
  let totalOrig = 0;
  let totalGz = 0;
  let totalB64 = 0;

  for (const ds of DATASETS) {
    const srcPath = path.join(standaloneDataDir, ds.file);
    if (!fs.existsSync(srcPath)) {
      console.warn(`[build-standalone] skipping missing ${ds.file}`);
      continue;
    }
    const raw = fs.readFileSync(srcPath);
    const gz = zlib.gzipSync(raw, { level: 9 });
    const b64 = gz.toString('base64');
    embedded[ds.key] = b64;

    totalOrig += raw.length;
    totalGz += gz.length;
    totalB64 += b64.length;

    console.info(
      `[build-standalone] ${ds.file.padEnd(36)}  ` +
        `orig=${mb(raw.length).padStart(6)} MB  ` +
        `gz=${mb(gz.length).padStart(6)} MB  ` +
        `b64=${mb(b64.length).padStart(6)} MB`
    );
  }

  if (Object.keys(embedded).length === 0) {
    fail('No compact data files were found — aborting.');
  }

  // Read the built JS bundle and escape any </script> sequences.
  const bundleJs = fs.readFileSync(bundlePath, 'utf8');
  const safeBundle = escapeForScript(bundleJs);

  // Build the embedded data script block. Each base64 payload is a plain
  // string literal (no escaping needed — base64 uses only [A-Za-z0-9+/=]).
  const dataEntries = Object.entries(embedded)
    .map(([key, b64]) => `  ${JSON.stringify(key)}: ${JSON.stringify(b64)}`)
    .join(',\n');
  const dataScript =
    `window.__STANDALONE_MODE__ = true;\n` +
    `window.__STANDALONE_DATA__ = {\n${dataEntries}\n};`;

  // Read the canonical HTML shell from public/ (not dist/) so we can
  // rebuild from a clean template each time.
  const htmlTemplate = fs.readFileSync(path.join(vizRoot, 'public', 'index.html'), 'utf8');

  // Replace the external bundle reference with two inlined <script> tags:
  // the data block first, the bundle second (order matters — the bundle
  // reads window.__STANDALONE_DATA__ on startup).
  const inlinedScripts =
    `<script>${dataScript}</script>\n` +
    `<script>${safeBundle}</script>`;

  const html = htmlTemplate.replace(
    /<script src=['"]\.?\/?bundle\.js['"]><\/script>/,
    inlinedScripts
  );

  if (!html.includes('__STANDALONE_DATA__')) {
    fail(
      `Failed to inject standalone data into HTML — did the template change? ` +
        `Expected a <script src="./bundle.js"></script> tag.`
    );
  }

  const outPath = path.join(distDir, 'standalone.html');
  fs.writeFileSync(outPath, html);
  const outSize = fs.statSync(outPath).size;

  console.info('');
  console.info(`[build-standalone] wrote ${outPath}`);
  console.info(
    `[build-standalone] totals  orig=${mb(totalOrig)} MB  gz=${mb(totalGz)} MB  ` +
      `b64=${mb(totalB64)} MB  final-html=${mb(outSize)} MB`
  );
  console.info(
    `[build-standalone] to verify: open ${path.relative(
      process.cwd(),
      outPath
    )} directly in a browser (file://)`
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
