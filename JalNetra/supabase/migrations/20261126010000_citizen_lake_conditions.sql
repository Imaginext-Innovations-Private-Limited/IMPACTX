begin;

alter table public.pilot_review_events drop constraint pilot_review_events_action_check;
alter table public.pilot_review_events add constraint pilot_review_events_action_check
  check (action in ('model','confirm','correct','dismiss','duplicate','clear'));

alter table public.pilot_concerns add column report_id uuid references public.pilot_reports(id);
grant insert (report_id) on public.pilot_concerns to authenticated;
alter policy pilot_concerns_write on public.pilot_concerns with check (
  reporter_id = (select auth.uid()) and exists (
    select 1 from public.pilot_memberships m where m.lake_id = pilot_concerns.lake_id
    and m.user_id = (select auth.uid()) and m.role = 'citizen'
  ) and (report_id is null or exists (
    select 1 from public.pilot_reports r where r.id = pilot_concerns.report_id
    and r.lake_id = pilot_concerns.lake_id and r.zone_id = pilot_concerns.zone_id
    and r.reporter_id = (select auth.uid())
  ))
);

create table private.pilot_analysis_config (
  singleton boolean primary key default true check (singleton),
  token_digest bytea not null
);
revoke all on private.pilot_analysis_config from public, anon, authenticated;

create function public.pilot_save_preliminary(p_report uuid, p_token text, p_output jsonb)
returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare
  saved public.pilot_review_events;
begin
  if auth.uid() is null or not exists (
    select 1 from private.pilot_analysis_config c
    where c.token_digest = extensions.digest(p_token, 'sha256')
  ) then
    raise insufficient_privilege using message = 'Preliminary write is not authorized';
  end if;
  insert into public.pilot_review_events (lake_id, report_id, actor_id, action, model_output)
  select r.lake_id, r.id, auth.uid(), 'model', p_output
  from public.pilot_reports r
  join public.pilot_memberships m on m.lake_id = r.lake_id and m.user_id = auth.uid() and m.role = 'citizen'
  where r.id = p_report and r.reporter_id = auth.uid()
  on conflict (report_id) where action = 'model' do nothing
  returning * into saved;
  if not found then
    select e.* into saved from public.pilot_review_events e
    join public.pilot_reports r on r.id = e.report_id
    join public.pilot_memberships m on m.lake_id = r.lake_id and m.user_id = auth.uid() and m.role = 'citizen'
    where e.report_id = p_report and e.action = 'model' and r.reporter_id = auth.uid();
    if not found then raise insufficient_privilege using message = 'Report is not available'; end if;
  end if;
  return to_jsonb(saved);
end;
$$;
revoke all on function public.pilot_save_preliminary(uuid, text, jsonb) from public, anon, authenticated;
grant execute on function public.pilot_save_preliminary(uuid, text, jsonb) to authenticated;

create function public.pilot_lake_conditions()
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
  from signals s
  where auth.uid() is not null and not coalesce((auth.jwt()->>'is_anonymous')::boolean, false)
  group by s.lake_id, s.zone_id, s.state, s.category;
$$;
revoke all on function public.pilot_lake_conditions() from public, anon, authenticated;
grant execute on function public.pilot_lake_conditions() to authenticated;

commit;

