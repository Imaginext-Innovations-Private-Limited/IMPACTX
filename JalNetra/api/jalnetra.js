import { BlobNotFoundError, BlobPreconditionFailedError, get, head, put } from '@vercel/blob';
import { getVercelOidcToken } from '@vercel/oidc';
import { createHostedHandler, SnapshotConflict } from '../src/hosted.js';
import { createPilotHandler } from '../src/pilot.js';

const store = {
  async read(path, { forWrite }) {
    let revision;
    if (forWrite) {
      try {
        revision = (await head(path)).etag;
        if (!revision) throw new Error('Missing private snapshot revision.');
      } catch (error) {
        if (error instanceof BlobNotFoundError) return null;
        throw error;
      }
    }
    const result = await get(path, { access: 'private', useCache: false });
    if (!result) return null;
    if (result.statusCode !== 200 || !result.stream) throw new Error('Invalid private snapshot.');
    return { bytes: Buffer.from(await new Response(result.stream).arrayBuffer()), etag: revision };
  },
  async write(path, bytes, etag) {
    try {
      await put(path, bytes, {
        access: 'private',
        addRandomSuffix: false,
        contentType: 'application/octet-stream',
        ttlDays: 7,
        ...(etag ? { allowOverwrite: true, ifMatch: etag } : {}),
      });
    } catch (error) {
      if (error instanceof BlobPreconditionFailedError || (!etag && /already exists/i.test(error.message))) {
        throw new SnapshotConflict();
      }
      throw error;
    }
  },
};

const hosted = createHostedHandler(store);
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const route = url.pathname === '/api/jalnetra' ? url.searchParams.get('jalroute') : url.pathname.slice(5);
    if (!route?.startsWith('pilot/')) return hosted(request);
    const geminiKey = process.env.GEMINI_API_KEY;
    const openAiKey = process.env.OPENAI_API_KEY || process.env.openai_key;
    let apiKey = openAiKey || process.env.AI_GATEWAY_API_KEY;
    if (!geminiKey && !apiKey && ['pilot/status', 'pilot/analyze', 'pilot/preliminary'].includes(route)) {
      apiKey = await getVercelOidcToken().catch(() => undefined);
    }
    const pilot = createPilotHandler({
      url: process.env.SUPABASE_URL,
      publishableKey: process.env.SUPABASE_PUBLISHABLE_KEY,
      analysisWriteToken: process.env.PILOT_ANALYSIS_WRITE_TOKEN,
      guestWriteToken: process.env.PILOT_GUEST_WRITE_TOKEN,
      visionDiagnostics: process.env.PILOT_VISION_DIAGNOSTICS === '1',
      apiKey,
      geminiKey,
      model: process.env.JALNETRA_VISION_MODEL || (openAiKey ? 'gpt-4.1-mini' : 'openai/gpt-4.1-mini'),
      gateway: !openAiKey,
    });
    return (await pilot(request)) ?? hosted(request);
  },
};
