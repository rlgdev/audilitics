// Runs the dataviz palette validator on the categorical slots declared in src/styles/tokens.css,
// once for light and once for dark (spec 8.3, ci.yml). Exits non-zero when a check FAILs.
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, '..', 'src', 'styles', 'tokens.css'), 'utf8');

function slots(block) {
  const out = [];
  for (let i = 1; i <= 8; i++) {
    const m = block.match(new RegExp(`--cat-${i}:\\s*(#[0-9a-fA-F]{6})`));
    if (!m) throw new Error(`--cat-${i} missing`);
    out.push(m[1]);
  }
  return out;
}

const light = slots(css.slice(0, css.indexOf('@media')));
const darkStart = css.indexOf(":root[data-theme='dark']");
const dark = slots(css.slice(darkStart));
let failed = false;
for (const [mode, list, surface] of [['light', light, '#fcfcfb'], ['dark', dark, '#1a1a19']]) {
  const out = execFileSync(process.execPath, [join(here, 'validate_palette.js'), list.join(','), '--mode', mode, '--surface', surface], { encoding: 'utf8' });
  process.stdout.write(out);
  if (/\[FAIL\]/.test(out)) failed = true;
}
process.exit(failed ? 1 : 0);
