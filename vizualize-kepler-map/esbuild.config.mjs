// ========================================================================
// esbuild config — dev server + production bundler
// ========================================================================
// Invocations:
//   node esbuild.config.mjs --start    → dev server on :8080 with live reload
//   node esbuild.config.mjs --build    → production bundle in dist/ + data copy
//
// Production mode emits a single non-split IIFE bundle (required so
// scripts/build-standalone.mjs can inline it into a one-file HTML).
// ========================================================================

import esbuild from 'esbuild';
import copyPlugin from 'esbuild-plugin-copy';
import process from 'node:process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv;
const port = 8080;

// Load .env if present, so the dev server and local production builds
// pick up MapboxAccessToken without requiring an external dotenv tool.
loadDotEnv(path.join(__dirname, '.env'));

// ------------------------------------------------------------------------
// Shared config
// ------------------------------------------------------------------------

const sharedConfig = {
  platform: 'browser',
  format: 'iife',
  logLevel: 'info',
  loader: {
    '.js': 'jsx',
    '.css': 'css',
    '.png': 'file',
    '.jpg': 'file',
    '.svg': 'file',
    '.woff': 'file',
    '.woff2': 'file'
  },
  entryPoints: [path.join(__dirname, 'src/app.tsx')],
  outfile: path.join(__dirname, 'dist/bundle.js'),
  bundle: true,
  splitting: false, // CRITICAL: scripts/build-standalone.mjs expects one bundle.
  target: 'es2020',
  define: {
    NODE_ENV: JSON.stringify(process.env.NODE_ENV || 'production'),
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    'process.env.MapboxAccessToken': JSON.stringify(process.env.MapboxAccessToken || ''),
    'process.env.DropboxClientId': JSON.stringify(''),
    'process.env.MapboxExportToken': JSON.stringify(''),
    'process.env.CartoClientId': JSON.stringify(''),
    'process.env.FoursquareClientId': JSON.stringify(''),
    'process.env.FoursquareDomain': JSON.stringify(''),
    'process.env.FoursquareAPIURL': JSON.stringify(''),
    'process.env.FoursquareUserMapsURL': JSON.stringify(''),
    'process.env.OpenAIToken': JSON.stringify(''),
    'process.env.NODE_DEBUG': JSON.stringify(false)
  },
  plugins: [
    copyPlugin({
      resolveFrom: 'cwd',
      assets: [
        {
          from: [path.join(__dirname, 'public/index.html')],
          to: [path.join(__dirname, 'dist')]
        }
      ]
    })
  ]
};

// ------------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------------

function loadDotEnv(envPath) {
  if (!fs.existsSync(envPath)) return;
  const content = fs.readFileSync(envPath, 'utf8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

function openURL(url) {
  const cmd = {
    darwin: ['open'],
    linux: ['xdg-open'],
    win32: ['cmd', '/c', 'start']
  };
  const command = cmd[process.platform];
  if (command) {
    const child = spawn(command[0], [...command.slice(1), url], { stdio: 'ignore', detached: true });
    child.on('error', (err) => {
      if (err.code === 'ENOENT' && command[0] === 'xdg-open') {
        console.warn('\n[esbuild] Failed to open browser automatically: "xdg-open" command not found.');
        console.warn('[esbuild] If you are using WSL, you can fix this by running:');
        console.warn('[esbuild]   sudo apt-get install xdg-utils\n');
      } else {
        console.error('[esbuild] Failed to open browser:', err);
      }
    });
  }
}

/** Copy the full data files from ../data/02_transformed into dist/data for
 * the multi-file static site. Uses the public/data symlink as its source,
 * so dev and prod both read from the same canonical location.
 */
function copyDataToDist() {
  const src = path.join(__dirname, 'public', 'data');
  const dst = path.join(__dirname, 'dist', 'data');

  if (!fs.existsSync(src)) {
    console.warn(
      `[esbuild] public/data does not exist — did you run \`ln -s ../../data/02_transformed public/data\`?`
    );
    return;
  }

  fs.mkdirSync(dst, { recursive: true });

  // Copy the three files the viz actually loads (plus shooting_arcs.csv for
  // the arc layer). Deliberately NOT copying the `standalone/` subdirectory —
  // the standalone build reads it from outside dist/.
  const files = ['unified_data.csv', 'gta_census_da.geojson', 'shooting_arcs.csv'];
  for (const f of files) {
    const from = path.join(src, f);
    const to = path.join(dst, f);
    if (!fs.existsSync(from)) {
      console.warn(`[esbuild] skipping missing data file: ${from}`);
      continue;
    }
    fs.copyFileSync(from, to);
    const mb = (fs.statSync(to).size / (1024 * 1024)).toFixed(1);
    console.info(`[esbuild] copied ${f} (${mb} MB) → dist/data/`);
  }
}

// ------------------------------------------------------------------------
// Entrypoint
// ------------------------------------------------------------------------

(async () => {
  if (args.includes('--build')) {
    try {
      const result = await esbuild.build({
        ...sharedConfig,
        minify: true,
        sourcemap: false,
        metafile: true
      });
      fs.writeFileSync(
        path.join(__dirname, 'dist/esbuild-metadata.json'),
        JSON.stringify(result.metafile)
      );
      copyDataToDist();
      const size = (fs.statSync(path.join(__dirname, 'dist/bundle.js')).size / (1024 * 1024)).toFixed(1);
      console.info(`[esbuild] production build complete — bundle.js ${size} MB`);
    } catch (e) {
      console.error(e);
      process.exit(1);
    }
  }

  if (args.includes('--start')) {
    try {
      const ctx = await esbuild.context({
        ...sharedConfig,
        minify: false,
        sourcemap: true,
        banner: {
          js: "new EventSource('/esbuild').addEventListener('change', () => location.reload());"
        }
      });
      await ctx.watch();
      await ctx.serve({
        servedir: path.join(__dirname, 'dist'),
        port,
        fallback: path.join(__dirname, 'dist/index.html'),
        onRequest: ({ remoteAddress, method, path: reqPath, status, timeInMS }) => {
          console.info(remoteAddress, status, `"${method} ${reqPath}" [${timeInMS}ms]`);
        }
      });

      // Also serve raw data files directly from public/data via a simple
      // symlink under dist/data so the dev server can fetch them without
      // needing a full copy.
      ensureDevDataLink();

      console.info(`[esbuild] dev server running at http://localhost:${port}`);
      openURL(`http://localhost:${port}`);
    } catch (e) {
      console.error(e);
      process.exit(1);
    }
  }
})();

function ensureDevDataLink() {
  const distDataLink = path.join(__dirname, 'dist', 'data');
  const target = path.join('..', 'public', 'data');
  try {
    fs.mkdirSync(path.join(__dirname, 'dist'), { recursive: true });
    if (fs.existsSync(distDataLink)) {
      const stat = fs.lstatSync(distDataLink);
      if (stat.isSymbolicLink() || stat.isFile()) {
        // Ok — leave existing link/file alone.
        return;
      }
      // It's a directory (from a prior --build run). Clean it up so the
      // symlink can take its place during dev.
      fs.rmSync(distDataLink, { recursive: true, force: true });
    }
    fs.symlinkSync(target, distDataLink, 'dir');
    console.info('[esbuild] symlinked dist/data → public/data for dev server');
  } catch (e) {
    console.warn('[esbuild] could not create dist/data symlink:', e.message);
  }
}
