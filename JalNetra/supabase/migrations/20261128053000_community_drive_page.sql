begin;

create table private.community_drive_proposals (
  id uuid primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  lake_id uuid not null references public.pilot_lakes(id),
  organization text not null check (length(btrim(organization)) between 1 and 120),
  title text not null check (length(btrim(title)) between 1 and 120),
  details text not null check (length(btrim(details)) between 1 and 500),
  starts_at timestamptz not null,
  status text not null default 'pending' check (status in ('pending','published','declined','withdrawn'))
);
create index community_drive_proposals_owner on private.community_drive_proposals(owner_id, starts_at);
create index community_drive_proposals_review on private.community_drive_proposals(lake_id, starts_at) where status = 'pending';
alter table private.community_drive_proposals enable row level security;
revoke all on private.community_drive_proposals from public, anon, authenticated;
alter table private.community_campaigns add column organization text;

create function public.pilot_drive_schedule(p_today boolean default false) returns jsonb
language sql stable security definer set search_path = '' as $$
  with bounds as (
    select date_trunc('day', now() at time zone 'Asia/Kolkata') as midnight
  ), drives as (
    select c.id,c.lake_id,l.name as lake,c.title,c.details,c.organization,c.starts_at,
      exists (select 1 from private.community_volunteers v
        where v.campaign_id = c.id and v.user_id = (select auth.uid())) as joined
    from private.community_campaigns c
    join public.pilot_lakes l on l.id = c.lake_id and l.slug is not null
    cross join bounds b
    where c.status = 'open' and c.starts_at >= b.midnight at time zone 'Asia/Kolkata'
      and (not p_today or c.starts_at < (b.midnight + interval '1 day') at time zone 'Asia/Kolkata')
    order by c.starts_at,c.id limit 200
  )
  select jsonb_build_object('date', to_char(b.midnight, 'YYYY-MM-DD'),
    'drives', coalesce((select jsonb_agg(to_jsonb(d) order by d.starts_at,d.id) from drives d), '[]'::jsonb))
  from bounds b;
$$;

create function public.pilot_drive_proposals() returns jsonb
language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(to_jsonb(p) order by p.starts_at,p.id), '[]'::jsonb)
  from (
    select d.id,d.lake_id,l.name as lake,d.organization,d.title,d.details,d.starts_at,d.status,
      d.owner_id = auth.uid() as own,
      d.owner_id <> auth.uid() and d.status = 'pending' and d.starts_at > now() as can_review
    from private.community_drive_proposals d join public.pilot_lakes l on l.id = d.lake_id
    where d.owner_id = auth.uid() or (d.status = 'pending' and exists (
      select 1 from public.pilot_memberships m where m.lake_id = d.lake_id
        and m.user_id = auth.uid() and m.role in ('operator','admin')
    ))
    order by d.starts_at desc,d.id desc limit 200
  ) p;
$$;

create function public.pilot_drive_change(p_action text, p_data jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  actor uuid := auth.uid();
  target uuid := (p_data->>'id')::uuid;
  proposal private.community_drive_proposals;
  selected uuid := (p_data->>'lakeId')::uuid;
  event_time timestamptz := (p_data->>'startsAt')::timestamptz;
begin
  if not exists (select 1 from auth.users u where u.id = actor and u.email_confirmed_at is not null
      and u.email is not null and lower(u.email) not like '%@jalnetra.invalid')
      or coalesce(auth.jwt()->>'is_anonymous','false') = 'true' then
    raise insufficient_privilege using message = 'Sign in with a confirmed email to manage community drives';
  end if;
  if p_action = 'submit' then
    if event_time is null or event_time <= now() or not exists (
      select 1 from public.pilot_lakes where id = selected and slug is not null
    ) then raise invalid_parameter_value using message = 'Choose a mapped lake and a future start time'; end if;
    insert into private.community_drive_proposals (id,owner_id,lake_id,organization,title,details,starts_at)
    values (target,actor,selected,btrim(p_data->>'organization'),btrim(p_data->>'title'),
      btrim(p_data->>'details'),event_time)
    on conflict (id) do nothing;
    return '{}'::jsonb;
  end if;
  select * into strict proposal from private.community_drive_proposals where id = target for update;
  if p_action = 'withdraw' then
    if proposal.owner_id <> actor then raise insufficient_privilege; end if;
    update private.community_drive_proposals set status='withdrawn' where id=target and status='pending';
  elsif p_action in ('publish','decline') then
    if proposal.owner_id = actor or not exists (
      select 1 from public.pilot_memberships where lake_id = proposal.lake_id and user_id = actor and role in ('operator','admin')
    ) then raise insufficient_privilege using message = 'A separate operator assigned to this lake must review the drive'; end if;
    if proposal.status <> 'pending' or (p_action = 'publish' and proposal.starts_at <= now()) then
      raise invalid_parameter_value using message = 'This drive can no longer be published or reviewed';
    end if;
    if p_action = 'publish' then
      insert into private.community_campaigns(id,lake_id,organization,title,details,starts_at)
      values (proposal.id,proposal.lake_id,proposal.organization,proposal.title,proposal.details,proposal.starts_at);
    end if;
    update private.community_drive_proposals set status=case when p_action='publish' then 'published' else 'declined' end
      where id=target;
  else
    raise invalid_parameter_value using message = 'Unknown drive action';
  end if;
  return '{}'::jsonb;
end;
$$;

revoke all on function public.pilot_drive_schedule(boolean) from public, anon, authenticated;
grant execute on function public.pilot_drive_schedule(boolean) to anon, authenticated;
revoke all on function public.pilot_drive_proposals(), public.pilot_drive_change(text,jsonb) from public, anon, authenticated;
grant execute on function public.pilot_drive_proposals(), public.pilot_drive_change(text,jsonb) to authenticated;

commit;
