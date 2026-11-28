begin;

create table private.community_campaigns (
  id uuid primary key,
  lake_id uuid not null references public.pilot_lakes(id),
  title text not null check (length(btrim(title)) between 1 and 120),
  details text not null check (length(btrim(details)) between 1 and 500),
  starts_at timestamptz not null,
  status text not null default 'open' check (status in ('open','completed','cancelled'))
);
create index community_campaigns_lake on private.community_campaigns(lake_id, starts_at);
create table private.community_volunteers (
  campaign_id uuid not null references private.community_campaigns(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  attended boolean not null default false,
  primary key (campaign_id, user_id)
);
create table private.community_adoptions (
  id uuid primary key,
  lake_id uuid not null references public.pilot_lakes(id),
  user_id uuid references auth.users(id) on delete set null,
  group_name text not null check (length(btrim(group_name)) between 1 and 120),
  plan text not null check (length(btrim(plan)) between 1 and 500),
  status text not null default 'pending' check (status in ('pending','active','declined','ended'))
);
create index community_adoptions_lake on private.community_adoptions(lake_id);
create table private.community_actions (
  id uuid primary key,
  lake_id uuid not null references public.pilot_lakes(id),
  report_id uuid not null unique,
  assignee text not null check (length(btrim(assignee)) between 1 and 120),
  plan text not null check (length(btrim(plan)) between 1 and 500),
  progress text check (length(btrim(progress)) between 1 and 500),
  status text not null default 'assigned' check (status in ('assigned','in_progress','awaiting_verification','verified')),
  started_at timestamptz,
  ready_at timestamptz,
  verified_at timestamptz,
  foreign key (lake_id, report_id) references public.pilot_reports(lake_id,id)
);
create index community_actions_lake on private.community_actions(lake_id);
create table private.community_evidence (
  action_id uuid not null references private.community_actions(id),
  report_id uuid not null unique references public.pilot_reports(id),
  status text not null default 'pending' check (status in ('pending','accepted','rejected')),
  primary key (action_id, report_id)
);
create unique index community_one_pending_evidence on private.community_evidence(action_id) where status = 'pending';
create table private.community_subscriptions (
  user_id uuid not null references auth.users(id) on delete cascade,
  lake_id uuid not null references public.pilot_lakes(id),
  subscribed_at timestamptz not null default clock_timestamp(),
  primary key (user_id,lake_id)
);
create table private.community_alert_events (
  id uuid primary key,
  lake_id uuid not null references public.pilot_lakes(id),
  category text not null,
  created_at timestamptz not null default clock_timestamp()
);
create index community_alert_events_lake on private.community_alert_events(lake_id, created_at desc);
create table private.community_alert_reads (
  user_id uuid not null references auth.users(id) on delete cascade,
  alert_id uuid not null references private.community_alert_events(id) on delete cascade,
  primary key (user_id,alert_id)
);

alter table private.community_campaigns enable row level security;
alter table private.community_volunteers enable row level security;
alter table private.community_adoptions enable row level security;
alter table private.community_actions enable row level security;
alter table private.community_evidence enable row level security;
alter table private.community_subscriptions enable row level security;
alter table private.community_alert_events enable row level security;
alter table private.community_alert_reads enable row level security;
revoke all on private.community_campaigns, private.community_volunteers, private.community_adoptions,
  private.community_actions, private.community_evidence, private.community_subscriptions,
  private.community_alert_events, private.community_alert_reads from public, anon, authenticated;

create function private.community_publish_alert() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into private.community_alert_events (id, lake_id, category)
  values (new.id, new.lake_id, new.category) on conflict do nothing;
  return new;
end;
$$;
revoke all on function private.community_publish_alert() from public, anon, authenticated;
create trigger community_concern_alert after insert on public.pilot_concerns
for each row when (new.report_id is null) execute function private.community_publish_alert();
create trigger community_verified_alert after insert on public.pilot_review_events
for each row when (new.action in ('confirm','correct')) execute function private.community_publish_alert();

create function public.pilot_community_board(p_lake uuid) returns jsonb
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
      'roster', case when operator then (select jsonb_agg(jsonb_build_object('id', v.user_id, 'attended', v.attended))
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
          not exists (select 1 from private.community_actions a where a.report_id = r.id)
          and (select e.action from public.pilot_review_events e where e.report_id = r.id and e.action <> 'model'
            order by e.created_at desc,e.id desc limit 1) in ('confirm','correct')
        else not exists (select 1 from private.community_evidence e where e.report_id = r.id) end
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

create function public.pilot_community_change(p_lake uuid, p_action text, p_data jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  actor uuid := auth.uid();
  member_role text;
  target uuid := (p_data->>'id')::uuid;
  report uuid := (p_data->>'reportId')::uuid;
  campaign private.community_campaigns;
  restoration private.community_actions;
begin
  if actor is null or coalesce(auth.jwt()->>'is_anonymous','false') = 'true' then
    raise insufficient_privilege using message = 'A JalNetra session is required';
  end if;
  select role into member_role from public.pilot_memberships where lake_id = p_lake and user_id = actor;
  if p_action in ('campaign_create','campaign_finish','campaign_cancel','attendance',
    'adoption_approve','adoption_decline','adoption_end','restoration_create','restoration_start',
    'restoration_ready','evidence_accept','evidence_reject') then
    if coalesce(member_role,'') not in ('operator','admin') then
      raise insufficient_privilege using message = 'An assigned operator is required';
    end if;
  elsif p_action <> 'alert_read' and coalesce(member_role,'') <> 'citizen' then
    raise insufficient_privilege using message = 'A citizen lake membership is required';
  end if;

  if p_action = 'campaign_create' then
    if (p_data->>'startsAt')::timestamptz <= now() then
      raise invalid_parameter_value using message = 'Schedule the cleanup in the future';
    end if;
    insert into private.community_campaigns (id,lake_id,title,details,starts_at)
    values (target,p_lake,btrim(p_data->>'title'),btrim(p_data->>'details'),(p_data->>'startsAt')::timestamptz)
    on conflict (id) do nothing;
  elsif p_action in ('join','leave','attendance','campaign_finish','campaign_cancel') then
    select * into strict campaign from private.community_campaigns where id = target and lake_id = p_lake for update;
    if campaign.status <> 'open' then
      if (p_action = 'campaign_finish' and campaign.status = 'completed')
        or (p_action = 'campaign_cancel' and campaign.status = 'cancelled') then return '{}'::jsonb; end if;
      raise invalid_parameter_value using message = 'This cleanup is closed';
    end if;
    if p_action in ('join','leave') and campaign.starts_at <= now() then
      raise invalid_parameter_value using message = 'Registration has closed';
    elsif p_action in ('attendance','campaign_finish') and campaign.starts_at > now() then
      raise invalid_parameter_value using message = 'The cleanup has not started';
    end if;
    case p_action
      when 'join' then insert into private.community_volunteers (campaign_id,user_id) values (target,actor) on conflict do nothing;
      when 'leave' then delete from private.community_volunteers where campaign_id = target and user_id = actor;
      when 'attendance' then update private.community_volunteers set attended = (p_data->>'attended')::boolean
        where campaign_id = target and user_id = (p_data->>'volunteerId')::uuid;
      else update private.community_campaigns set status = case when p_action = 'campaign_finish' then 'completed' else 'cancelled' end
        where id = target;
    end case;
  elsif p_action = 'adoption_request' then
    insert into private.community_adoptions (id,lake_id,user_id,group_name,plan)
    values (target,p_lake,actor,btrim(p_data->>'group'),btrim(p_data->>'plan')) on conflict (id) do nothing;
  elsif p_action in ('adoption_approve','adoption_decline','adoption_end') then
    update private.community_adoptions
    set status = case p_action when 'adoption_approve' then 'active' when 'adoption_decline' then 'declined' else 'ended' end
    where id = target and lake_id = p_lake and status = case when p_action = 'adoption_end' then 'active' else 'pending' end;
  elsif p_action = 'restoration_create' then
    if not exists (select 1 from public.pilot_reports r where r.id = report and r.lake_id = p_lake
      and (select e.action from public.pilot_review_events e where e.report_id = r.id and e.action <> 'model'
        order by e.created_at desc,e.id desc limit 1) in ('confirm','correct')) then
      raise invalid_parameter_value using message = 'Choose a verified pollution report from this lake';
    end if;
    insert into private.community_actions (id,lake_id,report_id,assignee,plan)
    values (target,p_lake,report,btrim(p_data->>'assignee'),btrim(p_data->>'plan')) on conflict do nothing;
  elsif p_action in ('restoration_start','restoration_ready','evidence_submit','evidence_accept','evidence_reject') then
    select * into strict restoration from private.community_actions where id = target and lake_id = p_lake for update;
    if p_action = 'restoration_start' and restoration.status = 'assigned' then
      update private.community_actions set status = 'in_progress', started_at = clock_timestamp() where id = target;
    elsif p_action = 'restoration_ready' and restoration.status = 'in_progress' then
      update private.community_actions set status = 'awaiting_verification', ready_at = clock_timestamp(),
        progress = btrim(p_data->>'progress') where id = target;
    elsif p_action = 'evidence_submit' and restoration.status = 'awaiting_verification' then
      if not exists (select 1 from public.pilot_reports r join public.pilot_reports original
        on original.id = restoration.report_id and original.zone_id = r.zone_id
        where r.id = report and r.lake_id = p_lake and r.reporter_id = actor
          and r.observed_at >= date_trunc('minute', restoration.ready_at)
          and r.created_at >= restoration.ready_at and r.id <> original.id
          and exists (select 1 from storage.objects o where o.bucket_id = 'jalnetra-pilot-evidence' and o.name = r.photo_path)) then
        raise invalid_parameter_value using message = 'Use your own photo taken in the same sector after the corrective work was recorded';
      end if;
      insert into private.community_evidence (action_id,report_id) values (target,report)
      on conflict (action_id,report_id) do nothing;
    elsif p_action in ('evidence_accept','evidence_reject') and restoration.status = 'awaiting_verification' then
      update private.community_evidence set status = case when p_action = 'evidence_accept' then 'accepted' else 'rejected' end
      where action_id = target and report_id = report and status = 'pending';
      if not found then raise invalid_parameter_value using message = 'The evidence is no longer awaiting review'; end if;
      if p_action = 'evidence_accept' then
        update private.community_actions set status = 'verified', verified_at = clock_timestamp() where id = target;
      end if;
    else
      raise invalid_parameter_value using message = 'This restoration action is no longer available';
    end if;
  elsif p_action = 'subscribe' then
    insert into private.community_subscriptions (user_id,lake_id) values (actor,p_lake) on conflict do nothing;
  elsif p_action = 'unsubscribe' then
    delete from private.community_subscriptions where user_id = actor and lake_id = p_lake;
  elsif p_action = 'alert_read' then
    insert into private.community_alert_reads (user_id,alert_id)
    select actor,e.id from private.community_alert_events e join private.community_subscriptions s
      on s.lake_id = e.lake_id and e.created_at >= s.subscribed_at
    where e.id = target and s.user_id = actor on conflict do nothing;
  else
    raise invalid_parameter_value using message = 'Unknown community action';
  end if;
  return '{}'::jsonb;
end;
$$;

revoke all on function public.pilot_community_board(uuid) from public, anon, authenticated;
grant execute on function public.pilot_community_board(uuid) to anon, authenticated;
revoke all on function public.pilot_community_change(uuid,text,jsonb) from public, anon, authenticated;
grant execute on function public.pilot_community_change(uuid,text,jsonb) to authenticated;

commit;
