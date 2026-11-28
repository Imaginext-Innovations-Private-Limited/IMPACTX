import { readdir, readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

const database = new PGlite();
try {
  // Minimal Supabase platform tables for exercising repository migrations locally.
  await database.exec(`
    create role anon;
    create role authenticated;
    create schema auth;
    create schema storage;
    create schema extensions;
    create table auth.users (id uuid primary key, email text, email_confirmed_at timestamptz);
    create table storage.buckets (id text primary key, name text, public bool, file_size_limit bigint, allowed_mime_types text[]);
    create table storage.objects (bucket_id text, name text);
    alter table storage.objects enable row level security;
    create function auth.uid() returns uuid language sql stable as $$
      select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
    $$;
    create function auth.jwt() returns jsonb language sql stable as $$ select '{}'::jsonb $$;
    grant usage on schema auth to anon, authenticated;
  `);
  for (const directory of ['supabase/migrations', 'supabase/tests']) {
    for (const file of (await readdir(directory)).filter(name => name.endsWith('.sql')).sort()) {
      try {
        await database.exec(await readFile(directory + '/' + file, 'utf8'));
      } catch (error) {
        throw new Error(directory + '/' + file + ' failed: ' + error.message, { cause: error });
      }
      console.log('Passed ' + file);
    }
  }
} finally {
  await database.close();
}
