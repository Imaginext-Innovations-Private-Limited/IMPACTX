begin;

grant select (id, name, slug) on public.pilot_lakes to anon;
grant select (id, lake_id, name, slug) on public.pilot_zones to anon;
create policy pilot_public_lake_catalog on public.pilot_lakes for select to anon using (slug is not null);
create policy pilot_public_zone_catalog on public.pilot_zones for select to anon using (slug is not null);

create or replace function public.pilot_lake_conditions()
returns table (lake_id uuid, zone_id uuid, state text, category text, observed_at timestamptz)
language sql stable security definer set search_path = ''
as $$
  with recent as (
    select r.lake_id, r.zone_id, r.observed_at, e.action, e.category
    from public.pilot_reports r
    join public.pilot_lakes l on l.id = r.lake_id and l.slug is not null
    left join lateral (
      select action, category from public.pilot_review_events
      where report_id = r.id and action <> 'model'
      order by created_at desc, id desc limit 1
    ) e on true
    where r.observed_at between now() - interval '7 days' and now()
  ), signals as (
    select r.lake_id, r.zone_id,
      case when r.action in ('confirm','correct') then 'verified'
           when r.action = 'clear' then 'clear' else 'pending' end as state,
      r.category, r.observed_at
    from recent r
    where r.action is null or r.action in ('confirm','correct','clear')
    union all
    select c.lake_id, c.zone_id, 'pending', null, c.created_at
    from public.pilot_concerns c
    join public.pilot_lakes l on l.id = c.lake_id and l.slug is not null
    where c.report_id is null and c.created_at between now() - interval '7 days' and now()
  )
  select s.lake_id, s.zone_id, s.state, s.category, max(s.observed_at)
  from signals s group by s.lake_id, s.zone_id, s.state, s.category;
$$;
grant execute on function public.pilot_lake_conditions() to anon;

create table private.pilot_guest_config (
  singleton boolean primary key default true check (singleton),
  token_digest bytea not null
);
create table private.pilot_guest_requests (
  network_key text not null,
  created_at timestamptz not null default now()
);
create index pilot_guest_requests_time on private.pilot_guest_requests(created_at);
revoke all on private.pilot_guest_config, private.pilot_guest_requests from public, anon, authenticated;

create function public.pilot_create_guest(p_token text, p_network text)
returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare
  guest_id uuid := gen_random_uuid();
  guest_email text := 'guest-' || guest_id::text || '@jalnetra.invalid';
  guest_password text := encode(extensions.gen_random_bytes(32), 'hex');
begin
  if not exists (
    select 1 from private.pilot_guest_config
    where token_digest = extensions.digest(p_token, 'sha256')
  ) or p_network is null or p_network !~ '^[a-f0-9]{64}$' then
    raise insufficient_privilege using message = 'Guest access is unavailable';
  end if;

  perform pg_catalog.pg_advisory_xact_lock(27433, 671);
  delete from private.pilot_guest_requests where created_at < now() - interval '1 hour';
  if (select count(*) from private.pilot_guest_requests where network_key = p_network) >= 10
    or (select count(*) from private.pilot_guest_requests) >= 150 then
    return jsonb_build_object('limited', true);
  end if;
  insert into private.pilot_guest_requests(network_key) values (p_network);

  insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
    raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new, email_change,
    email_change_token_current, reauthentication_token, phone_change, phone_change_token
  ) values (
    '00000000-0000-0000-0000-000000000000', guest_id, 'authenticated', 'authenticated', guest_email,
    extensions.crypt(guest_password, extensions.gen_salt('bf', 10)), now(),
    '{"provider":"email","providers":["email"],"jalnetra_guest":true}', '{}', now(), now(),
    '', '', '', '', '', '', '', ''
  );
  insert into auth.identities (provider_id, user_id, identity_data, provider, created_at, updated_at)
  values (guest_id::text, guest_id, jsonb_build_object('sub', guest_id::text, 'email', guest_email,
    'email_verified', true, 'phone_verified', false), 'email', now(), now());
  return jsonb_build_object('email', guest_email, 'password', guest_password);
end;
$$;
revoke all on function public.pilot_create_guest(text, text) from public, anon, authenticated;
grant execute on function public.pilot_create_guest(text, text) to anon;

commit;
