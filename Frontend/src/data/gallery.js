import { events } from './events';
import fingerprints from './galleryManifest.json';
import { newestFirst } from '../components/events/eventUtils';

const sortedEvents = [...events].sort(newestFirst);
const imageLists = sortedEvents.map(event => event.gallery.length ? event.gallery : [event.coverImage].filter(Boolean));
const uniqueImages = new Map();

// Round-robin selection gives each event a turn before its next image.
for (let index = 0; index < Math.max(0, ...imageLists.map(images => images.length)); index += 1) {
    sortedEvents.forEach((event, eventIndex) => {
        const src = imageLists[eventIndex][index];
        const id = fingerprints[src];
        if (!id) return;
        if (uniqueImages.has(id)) {
            const item = uniqueImages.get(id);
            if (!item.sourceEvents.some(source => source.id === event.id)) item.sourceEvents.push(event);
        } else {
            uniqueImages.set(id, { id, src, sourceEvents: [event] });
        }
    });
}

export const galleryImages = [...uniqueImages.values()];
export const galleryEvents = sortedEvents.filter(event => galleryImages.some(image => image.sourceEvents.includes(event)));
export const galleryYears = [...new Set(galleryEvents.map(event => event.year))].sort((a, b) => b - a);
export const galleryCategories = [...new Set(galleryEvents.map(event => event.category))].sort();
