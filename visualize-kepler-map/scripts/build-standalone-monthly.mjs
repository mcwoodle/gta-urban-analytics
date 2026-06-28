// ========================================================================
// build-standalone-monthly.mjs — embed the monthly dataset + monthly bundle
// into one HTML file (dist/standalone-monthly.html)
// ========================================================================
// Prereq: `yarn build` (or esbuild --build) has populated dist/ with
// index-monthly.html and bundle-monthly.js. This script reads:
//
//   data/02_transformed/standalone/gta_municipalities_monthly.geojson
//
// gzips + base64-encodes it under the key `municipalities_monthly`, injects a
// <script> defining window.__STANDALONE_MODE__ = true and
// window.__STANDALONE_DATA__ = { municipalities_monthly: "<b64>" }, inlines
// dist/bundle-monthly.js, and writes dist/standalone-monthly.html.
//
// Mirrors scripts/build-standalone.mjs but for the single-dataset monthly map.
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

const DATASET_KEY = 'municipalities_monthly';
const DATASET_FILE = 'gta_municipalities_monthly.geojson';

function fail(msg) {
  console.error(`[build-standalone-monthly] ${msg}`);
  process.exit(1);
}

function mb(bytes) {
  return (bytes / (1024 * 1024)).toFixed(2);
}

/** Escape `</script>` sequences so text is safe to embed inside a <script> tag. */
function escapeForScript(text) {
  return text.replace(/<\/script>/gi, '<\\/script>');
}

async function main() {
  const htmlTemplatePath = path.join(vizRoot, 'public', 'index-monthly.html');
  const bundlePath = path.join(distDir, 'bundle-monthly.js');
  if (!fs.existsSync(bundlePath)) {
    fail('dist/bundle-monthly.js missing. Run `yarn build` before this script.');
  }
  if (!fs.existsSync(htmlTemplatePath)) {
    fail(`${htmlTemplatePath} missing — cannot build the monthly page.`);
  }

  const srcPath = path.join(standaloneDataDir, DATASET_FILE);
  if (!fs.existsSync(srcPath)) {
    fail(
      `${srcPath} does not exist. Run \`uv run transform\` (or at least the ` +
        `build_municipality_monthly step) from the repo root first.`
    );
  }

  // Read + gzip + base64 the monthly dataset.
  const raw = fs.readFileSync(srcPath);
  const gz = zlib.gzipSync(raw, { level: 9 });
  const b64 = gz.toString('base64');
  console.info(
    `[build-standalone-monthly] ${DATASET_FILE.padEnd(36)}  ` +
      `orig=${mb(raw.length).padStart(6)} MB  ` +
      `gz=${mb(gz.length).padStart(6)} MB  ` +
      `b64=${mb(b64.length).padStart(6)} MB`
  );

  // Build the embedded data + bundle <script> blocks (data first — the bundle
  // reads window.__STANDALONE_DATA__ on startup).
  const dataScript =
    `window.__STANDALONE_MODE__ = true;\n` +
    `window.__STANDALONE_DATA__ = {\n  ${JSON.stringify(DATASET_KEY)}: ${JSON.stringify(b64)}\n};`;

  const safeBundle = escapeForScript(fs.readFileSync(bundlePath, 'utf8'));
  const inlinedScripts =
    `<script>${dataScript}</script>\n` + `<script>${safeBundle}</script>`;

  const htmlTemplate = fs.readFileSync(htmlTemplatePath, 'utf8');
  const html = htmlTemplate.replace(
    /<script src=['"]\.?\/?bundle-monthly\.js['"]><\/script>/,
    () => inlinedScripts
  );

  if (!html.includes('__STANDALONE_DATA__')) {
    fail(
      'Failed to inject standalone data into HTML — did the template change? ' +
        'Expected a <script src="./bundle-monthly.js"></script> tag.'
    );
  }

  const outPath = path.join(distDir, 'standalone-monthly.html');
  fs.writeFileSync(outPath, html);
  const outSize = fs.statSync(outPath).size;

  console.info('');
  console.info(`[build-standalone-monthly] wrote ${outPath}`);
  console.info(`[build-standalone-monthly] final-html=${mb(outSize)} MB`);
  console.info(
    `[build-standalone-monthly] to verify: open ${path.relative(
      process.cwd(),
      outPath
    )} directly in a browser (file://)`
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
