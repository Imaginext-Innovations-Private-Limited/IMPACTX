begin;

create table private.pilot_demo_runs (
  id uuid primary key default gen_random_uuid(),
  scenario text not null check (scenario in ('foam-inlet','algae','dumping')),
  created_at timestamptz not null default now(),
  confirmed_at timestamptz
);
revoke all on private.pilot_demo_runs from public, anon, authenticated;

create function public.pilot_start_demo(p_token text, p_scenario text)
returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare item private.pilot_demo_runs;
begin
  if not exists (select 1 from private.pilot_guest_config
    where token_digest = extensions.digest(p_token, 'sha256')) then
    raise insufficient_privilege using message = 'Demo creation is unavailable';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(27433, 672);
  delete from private.pilot_demo_runs where created_at < now() - interval '24 hours';
  if (select count(*) from private.pilot_demo_runs) >= 300 then
    return jsonb_build_object('limited', true);
  end if;
  insert into private.pilot_demo_runs(scenario) values (p_scenario) returning * into item;
  return to_jsonb(item);
end;
$$;
revoke all on function public.pilot_start_demo(text, text) from public, anon, authenticated;
grant execute on function public.pilot_start_demo(text, text) to anon;

create function public.pilot_demo_run(p_id uuid, p_confirm boolean default false)
returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare item private.pilot_demo_runs;
begin
  if auth.uid() is null or not exists (
    select 1 from public.pilot_memberships where user_id = auth.uid() and role in ('operator','admin')
  ) then raise insufficient_privilege using message = 'Operator access is required'; end if;
  if p_confirm then
    update private.pilot_demo_runs set confirmed_at = coalesce(confirmed_at, now())
    where id = p_id and created_at >= now() - interval '24 hours' returning * into item;
  else
    select * into item from private.pilot_demo_runs where id = p_id and created_at >= now() - interval '24 hours';
  end if;
  if item.id is null then return null; end if;
  return to_jsonb(item);
end;
$$;
revoke all on function public.pilot_demo_run(uuid, boolean) from public, anon, authenticated;
grant execute on function public.pilot_demo_run(uuid, boolean) to authenticated;

commit;
