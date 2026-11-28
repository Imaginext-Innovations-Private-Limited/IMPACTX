begin;

create table public.pilot_lakes (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(btrim(name)) between 1 and 120)
);

create table public.pilot_zones (
  id uuid primary key default gen_random_uuid(),
  lake_id uuid not null references public.pilot_lakes(id),
  name text not null check (length(btrim(name)) between 1 and 120),
  unique (lake_id, id),
  unique (lake_id, name)
);

create table public.pilot_memberships (
  lake_id uuid not null references public.pilot_lakes(id),
  user_id uuid not null references auth.users(id),
  role text not null check (role in ('citizen', 'operator')),
  primary key (lake_id, user_id)
);
create index pilot_memberships_by_user on public.pilot_memberships(user_id, lake_id);

create table public.pilot_reports (
  id uuid primary key default gen_random_uuid(),
  lake_id uuid not null,
  zone_id uuid not null,
  reporter_id uuid not null default auth.uid() references auth.users(id),
  observed_at timestamptz not null,
  created_at timestamptz not null default now(),
  note text check (length(note) <= 500),
  ph numeric check (ph between 0 and 14),
  temperature_c numeric check (temperature_c between -20 and 100),
  photo_path text not null unique check (photo_path ~ '^[0-9a-f-]{36}/[0-9a-f-]{36}[.]png$'),
  foreign key (lake_id, zone_id) references public.pilot_zones(lake_id, id)
);
create index pilot_reports_by_lake_time on public.pilot_reports(lake_id, created_at desc);
create index pilot_reports_by_reporter on public.pilot_reports(reporter_id);
create index pilot_reports_by_zone_time on public.pilot_reports(zone_id, created_at desc);
create index pilot_reports_recent on public.pilot_reports(created_at desc);

alter table public.pilot_lakes enable row level security;
alter table public.pilot_zones enable row level security;
alter table public.pilot_memberships enable row level security;
alter table public.pilot_reports enable row level security;

revoke all on public.pilot_lakes, public.pilot_zones, public.pilot_memberships, public.pilot_reports
  from public, anon, authenticated;
grant select on public.pilot_lakes, public.pilot_zones, public.pilot_memberships, public.pilot_reports to authenticated;
grant insert (lake_id, zone_id, observed_at, note, ph, temperature_c, photo_path)
  on public.pilot_reports to authenticated;

create policy pilot_memberships_read_own on public.pilot_memberships for select to authenticated
  using (user_id = (select auth.uid()));

create policy pilot_lakes_read_member on public.pilot_lakes for select to authenticated
  using (exists (
    select 1 from public.pilot_memberships m where m.lake_id = pilot_lakes.id and m.user_id = (select auth.uid())
  ));

create policy pilot_zones_read_member on public.pilot_zones for select to authenticated
  using (exists (
    select 1 from public.pilot_memberships m where m.lake_id = pilot_zones.lake_id and m.user_id = (select auth.uid())
  ));

create policy pilot_reports_read_member on public.pilot_reports for select to authenticated
  using (exists (
    select 1 from public.pilot_memberships m
    where m.lake_id = pilot_reports.lake_id and m.user_id = (select auth.uid())
      and (m.role = 'operator' or pilot_reports.reporter_id = (select auth.uid()))
  ));

create policy pilot_reports_create_citizen on public.pilot_reports for insert to authenticated
  with check (
    reporter_id = (select auth.uid())
    and observed_at <= now() + interval '5 minutes'
    and split_part(photo_path, '/', 1) = (select auth.uid())::text
    and exists (
      select 1 from public.pilot_memberships m
      where m.lake_id = pilot_reports.lake_id and m.user_id = (select auth.uid()) and m.role = 'citizen'
    )
  );

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('jalnetra-pilot-evidence', 'jalnetra-pilot-evidence', false, 5242880, array['image/png']);

create policy pilot_evidence_upload_citizen on storage.objects for insert to authenticated
  with check (
    bucket_id = 'jalnetra-pilot-evidence'
    and name ~ '^[0-9a-f-]{36}/[0-9a-f-]{36}[.]png$'
    and split_part(name, '/', 1) = (select auth.uid())::text
    and exists (
      select 1 from public.pilot_memberships m where m.user_id = (select auth.uid()) and m.role = 'citizen'
    )
  );

create policy pilot_evidence_read_authorized on storage.objects for select to authenticated
  using (
    bucket_id = 'jalnetra-pilot-evidence'
    and (
      (split_part(name, '/', 1) = (select auth.uid())::text and exists (
        select 1 from public.pilot_memberships m where m.user_id = (select auth.uid())
      ))
      or exists (select 1 from public.pilot_reports r where r.photo_path = storage.objects.name)
    )
  );

create function public.jalnetra_pilot_status() returns jsonb
  language sql stable security invoker set search_path = ''
  as $$ select jsonb_build_object('ready', true, 'schemaVersion', 1) $$;
revoke all on function public.jalnetra_pilot_status() from public;
grant execute on function public.jalnetra_pilot_status() to anon, authenticated;

commit;
