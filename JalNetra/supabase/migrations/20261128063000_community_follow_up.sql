begin;

alter table public.pilot_reports add column is_follow_up boolean not null default false;
grant insert (is_follow_up) on public.pilot_reports to authenticated;
update public.pilot_reports r set is_follow_up = true
where exists (select 1 from private.community_evidence e where e.report_id = r.id);

alter table private.community_volunteers add column check_in_code text not null
  default upper(left(replace(gen_random_uuid()::text,'-',''),10)),
  add unique (campaign_id,check_in_code);

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
      and not r.is_follow_up
      and not exists (select 1 from private.community_evidence v where v.report_id = r.id)
      and not exists (select 1 from private.community_actions a where a.report_id = r.id and a.status = 'verified')
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

create or replace function public.pilot_community_board(p_lake uuid) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare
  actor uuid := auth.uid();
  operator boolean := exists (select 1 from public.pilot_memberships
    where lake_id = p_lake and user_id = actor and role in ('operator','admin'));
begin
  if not exists (select 1 from public.pilot_lakes where id = p_lake and slug is not null) then
    raise no_data_found using message = 'Lake is unavailable';
  end if;
  return jsonb_build_object(
    'operator', operator,
    'subscribed', exists (select 1 from private.community_subscriptions where user_id = actor and lake_id = p_lake),
    'campaigns', coalesce((select jsonb_agg(to_jsonb(c) || jsonb_build_object(
      'joined', exists (select 1 from private.community_volunteers v where v.campaign_id = c.id and v.user_id = actor),
      'registrations', (select count(*) from private.community_volunteers v where v.campaign_id = c.id),
      'roster', case when operator then (select jsonb_agg(jsonb_build_object('id', v.user_id, 'attended', v.attended, 'check_in_code', v.check_in_code))
        from private.community_volunteers v where v.campaign_id = c.id) end) order by c.starts_at)
      from private.community_campaigns c where c.lake_id = p_lake), '[]'::jsonb),
    'adoptions', coalesce((select jsonb_agg(to_jsonb(g) - 'user_id' order by g.group_name)
      from private.community_adoptions g where g.lake_id = p_lake
        and (g.status in ('active','ended') or operator or g.user_id = actor)), '[]'::jsonb),
    'actions', coalesce((select jsonb_agg((to_jsonb(a) - 'report_id') || jsonb_build_object(
      'zone_id', r.zone_id, 'evidence_pending', exists (select 1 from private.community_evidence e
        where e.action_id = a.id and e.status = 'pending'),
      'pending_evidence', (select e.report_id from private.community_evidence e
        where operator and e.action_id = a.id and e.status = 'pending')) order by a.id)
      from private.community_actions a join public.pilot_reports r on r.id = a.report_id where a.lake_id = p_lake), '[]'::jsonb),
    'reports', coalesce((select jsonb_agg(to_jsonb(candidate) order by candidate.observed_at desc) from (
      select r.id, r.observed_at, r.created_at, r.zone_id from public.pilot_reports r
      where r.lake_id = p_lake and (operator or r.reporter_id = actor)
        and case when operator then
          not r.is_follow_up and not exists (select 1 from private.community_actions a where a.report_id = r.id)
          and (select e.action from public.pilot_review_events e where e.report_id = r.id and e.action <> 'model'
            order by e.created_at desc,e.id desc limit 1) in ('confirm','correct')
        else r.is_follow_up and not exists (select 1 from private.community_evidence e where e.report_id = r.id) end
      order by r.observed_at desc limit 100
    ) candidate), '[]'::jsonb),
    'impact', jsonb_build_object(
      'completed_cleanups', (select count(*) from private.community_campaigns where lake_id = p_lake and status = 'completed'),
      'volunteers', (select count(distinct v.user_id) from private.community_volunteers v
        join private.community_campaigns c on c.id = v.campaign_id
        where c.lake_id = p_lake and c.status = 'completed' and v.attended),
      'active_adoptions', (select count(*) from private.community_adoptions where lake_id = p_lake and status = 'active'),
      'verified_restorations', (select count(*) from private.community_actions where lake_id = p_lake and status = 'verified')),
    'alerts', coalesce((select jsonb_agg(to_jsonb(alert) order by alert.created_at desc) from (
      select e.id, l.name as lake, e.category, e.created_at,
        exists (select 1 from private.community_alert_reads r where r.user_id = actor and r.alert_id = e.id) as read
      from private.community_subscriptions s join private.community_alert_events e
        on e.lake_id = s.lake_id and e.created_at >= s.subscribed_at
      join public.pilot_lakes l on l.id = e.lake_id
      where s.user_id = actor order by e.created_at desc,e.id desc limit 30
    ) alert), '[]'::jsonb)
  );
end;
$$;

create or replace function public.pilot_drive_schedule(p_today boolean default false) returns jsonb
language sql stable security definer set search_path = '' as $$
  with bounds as (
    select date_trunc('day', now() at time zone 'Asia/Kolkata') as midnight
  ), drives as (
    select c.id,c.lake_id,l.name as lake,c.title,c.details,c.organization,c.starts_at,
      exists (select 1 from private.community_volunteers v
        where v.campaign_id = c.id and v.user_id = (select auth.uid())) as joined,
      (select v.check_in_code from private.community_volunteers v
        where v.campaign_id = c.id and v.user_id = (select auth.uid())) as check_in_code
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

create or replace function public.pilot_drive_proposals() returns jsonb
language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(to_jsonb(p) order by p.starts_at,p.id), '[]'::jsonb)
  from (
    select d.id,d.lake_id,l.name as lake,d.organization,d.title,d.details,d.starts_at,
      case when c.status in ('completed','cancelled') then c.status else d.status end as status,
      d.owner_id = auth.uid() as own,
      d.owner_id <> auth.uid() and d.status = 'pending' and d.starts_at > now() as can_review
    from private.community_drive_proposals d join public.pilot_lakes l on l.id = d.lake_id
    left join private.community_campaigns c on c.id = d.id
    where d.owner_id = auth.uid() or (d.status = 'pending' and exists (
      select 1 from public.pilot_memberships m where m.lake_id = d.lake_id
        and m.user_id = auth.uid() and m.role in ('operator','admin')
    ))
    order by d.starts_at desc,d.id desc limit 200
  ) p;
$$;

commit;
