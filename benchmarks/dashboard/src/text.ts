// Chart labels are typeset on the page rather than in a worker: HoloChart's text worker
// evaluates code, which this site's Content Security Policy forbids, so the labels would never
// appear. Imported first by main.ts; the renderer applies it when its text engine loads.
// (vite.config.ts points '@mk7s/holochart-render' at the renderer HoloChart itself uses.)
// @ts-expect-error not a direct dependency, so TypeScript cannot see its types
import { configureText } from '@mk7s/holochart-render';

(configureText as (config: { useWorker?: boolean }) => void)({ useWorker: false });
