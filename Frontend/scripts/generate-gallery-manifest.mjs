import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { events } from '../src/data/events.js';

// Generated asset fingerprints only; all event information stays in events.js.
const paths = [...new Set(events.flatMap(event => event.gallery.length ? event.gallery : [event.coverImage].filter(Boolean)))].sort();
const manifest = {};
for (const path of paths) {
    if (!/^\/events\/[\w/-]+\.webp$/.test(path)) throw new Error(`Invalid gallery path: ${path}`);
    const bytes = await readFile(new URL(`../public${path}`, import.meta.url));
    if (bytes.toString('ascii', 0, 4) !== 'RIFF' || bytes.toString('ascii', 8, 12) !== 'WEBP') throw new Error(`Invalid WebP: ${path}`);
    manifest[path] = createHash('sha256').update(bytes).digest('hex');
}
await writeFile(new URL('../src/data/galleryManifest.json', import.meta.url), JSON.stringify(manifest, null, 2) + '\n');
