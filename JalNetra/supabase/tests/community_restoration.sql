begin;

insert into auth.users (id,email,email_confirmed_at) values
  ('c1000000-0000-4000-8000-000000000001','community-citizen@example.invalid',now()),
  ('c1000000-0000-4000-8000-000000000002','community-operator@example.invalid',now()),
  ('c1000000-0000-4000-8000-000000000003','community-other@example.invalid',now());
insert into public.pilot_lakes (id,name,slug) values
  ('c2000000-0000-4000-8000-000000000001','Community QA Lake','community-qa-lake'),
  ('c2000000-0000-4000-8000-000000000002','Community QA Other','community-qa-other');
insert into public.pilot_zones (id,lake_id,name,slug)
values ('c3000000-0000-4000-8000-000000000001','c2000000-0000-4000-8000-000000000001','Test Sector','test-sector');
insert into public.pilot_memberships (lake_id,user_id,role)
select 'c2000000-0000-4000-8000-000000000001',id,
  case when email like '%operator%' then 'operator' else 'citizen' end
from auth.users where email in ('community-citizen@example.invalid','community-operator@example.invalid','community-other@example.invalid');

set local role authenticated;
select set_config('request.jwt.claim.sub','c1000000-0000-4000-8000-000000000002',true);
do $$
declare lake uuid := 'c2000000-0000-4000-8000-000000000001';
begin
  perform public.pilot_community_change(lake,'campaign_create',jsonb_build_object(
    'id','c4000000-0000-4000-8000-000000000001','title','Shoreline cleanup',
    'details','Meet at the park entrance','startsAt',now() + interval '1 day'));
  begin
    perform public.pilot_community_change('c2000000-0000-4000-8000-000000000002','campaign_create','{}');
    raise exception 'Operator managed a different lake';
  exception when insufficient_privilege then null;
  end;
end $$;

select set_config('request.jwt.claim.sub','c1000000-0000-4000-8000-000000000001',true);
do $$
declare lake uuid := 'c2000000-0000-4000-8000-000000000001';
declare campaign jsonb := '{"id":"c4000000-0000-4000-8000-000000000001"}';
declare board jsonb;
begin
  perform public.pilot_community_change(lake,'subscribe','{}');
  perform public.pilot_community_change(lake,'join',campaign);
  perform public.pilot_community_change(lake,'join',campaign);
  perform public.pilot_community_change(lake,'adoption_request','{
    "id":"c4000000-0000-4000-8000-000000000002","group":"Lake Friends","plan":"Inspect paths monthly"}');
  board := public.pilot_community_board(lake);
  if (board#>>'{campaigns,0,registrations}')::int is distinct from 1
    or (board#>>'{campaigns,0,joined}')::bool is distinct from true
    or board#>>'{campaigns,0,roster}' is not null then
    raise exception 'Registration is duplicated or volunteer identities are public';
  end if;
  begin
    perform public.pilot_community_change(lake,'campaign_cancel',campaign);
    raise exception 'Citizen cancelled a cleanup';
  exception when insufficient_privilege then null;
  end;
end $$;

reset role;
update private.community_campaigns set starts_at = now() - interval '1 hour'
where id = 'c4000000-0000-4000-8000-000000000001';
insert into public.pilot_reports (id,lake_id,zone_id,reporter_id,photo_path,observed_at)
values ('c5000000-0000-4000-8000-000000000001','c2000000-0000-4000-8000-000000000001',
  'c3000000-0000-4000-8000-000000000001','c1000000-0000-4000-8000-000000000001',
  'c1000000-0000-4000-8000-000000000001/c5000000-0000-4000-8000-000000000001.png',now() - interval '1 day');
insert into public.pilot_review_events (lake_id,report_id,actor_id,action,category)
values ('c2000000-0000-4000-8000-000000000001','c5000000-0000-4000-8000-000000000001',
  'c1000000-0000-4000-8000-000000000002','confirm','dumping');

set local role authenticated;
select set_config('request.jwt.claim.sub','c1000000-0000-4000-8000-000000000002',true);
do $$
declare lake uuid := 'c2000000-0000-4000-8000-000000000001';
declare job jsonb := '{"id":"c4000000-0000-4000-8000-000000000003"}';
begin
  perform public.pilot_community_change(lake,'attendance','{
    "id":"c4000000-0000-4000-8000-000000000001","volunteerId":"c1000000-0000-4000-8000-000000000001","attended":true}');
  perform public.pilot_community_change(lake,'campaign_finish','{"id":"c4000000-0000-4000-8000-000000000001"}');
  perform public.pilot_community_change(lake,'adoption_approve','{"id":"c4000000-0000-4000-8000-000000000002"}');
  perform public.pilot_community_change(lake,'restoration_create',job || '{
    "reportId":"c5000000-0000-4000-8000-000000000001","assignee":"Shoreline crew","plan":"Remove dumped waste"}');
  perform public.pilot_community_change(lake,'restoration_start',job);
  perform public.pilot_community_change(lake,'restoration_ready',job || '{"progress":"Waste removed"}');
end $$;

reset role;
insert into public.pilot_reports (id,lake_id,zone_id,reporter_id,photo_path,observed_at)
values ('c5000000-0000-4000-8000-000000000002','c2000000-0000-4000-8000-000000000001',
  'c3000000-0000-4000-8000-000000000001','c1000000-0000-4000-8000-000000000001',
  'c1000000-0000-4000-8000-000000000001/c5000000-0000-4000-8000-000000000002.png',clock_timestamp());
insert into storage.objects (bucket_id,name) values
  ('jalnetra-pilot-evidence','c1000000-0000-4000-8000-000000000001/c5000000-0000-4000-8000-000000000002.png');
update public.pilot_reports set created_at = clock_timestamp(), is_follow_up = true
where id = 'c5000000-0000-4000-8000-000000000002';
do $$ begin
  if exists (select 1 from public.pilot_lake_conditions()
    where lake_id = 'c2000000-0000-4000-8000-000000000001' and state = 'pending') then
    raise exception 'Restoration upload appeared as a new concern';
  end if;
end $$;

set local role authenticated;
select set_config('request.jwt.claim.sub','c1000000-0000-4000-8000-000000000003',true);
do $$
declare lake uuid := 'c2000000-0000-4000-8000-000000000001';
declare board jsonb := public.pilot_community_board(lake);
begin
  if jsonb_array_length(board->'alerts') <> 0 or jsonb_array_length(board->'reports') <> 0 then
    raise exception 'An unrelated citizen can see private alerts or evidence';
  end if;
  begin
    perform public.pilot_community_change(lake,'evidence_submit','{
      "id":"c4000000-0000-4000-8000-000000000003","reportId":"c5000000-0000-4000-8000-000000000002"}');
    raise exception 'Citizen attached another account’s photo';
  exception when invalid_parameter_value then null;
  end;
end $$;

select set_config('request.jwt.claim.sub','c1000000-0000-4000-8000-000000000001',true);
do $$
declare lake uuid := 'c2000000-0000-4000-8000-000000000001';
declare board jsonb := public.pilot_community_board(lake);
begin
  if board#>>'{alerts,0,category}' is distinct from 'dumping' then
    raise exception 'Verified concern did not generate a subscriber alert';
  end if;
  perform public.pilot_community_change(lake,'alert_read',jsonb_build_object('id',board#>>'{alerts,0,id}'));
  if (public.pilot_community_board(lake)#>>'{alerts,0,read}')::bool is distinct from true then
    raise exception 'Alert did not persist as read';
  end if;
  perform public.pilot_community_change(lake,'evidence_submit','{
    "id":"c4000000-0000-4000-8000-000000000003","reportId":"c5000000-0000-4000-8000-000000000002"}');
end $$;
select set_config('request.jwt.claim.sub','c1000000-0000-4000-8000-000000000002',true);
select public.pilot_community_change('c2000000-0000-4000-8000-000000000001','evidence_accept',
  '{"id":"c4000000-0000-4000-8000-000000000003","reportId":"c5000000-0000-4000-8000-000000000002"}');

select set_config('request.jwt.claim.sub','',true);
set local role anon;
do $$
declare board jsonb := public.pilot_community_board('c2000000-0000-4000-8000-000000000001');
begin
  if board->'impact' is distinct from '{"active_adoptions":1,"completed_cleanups":1,"verified_restorations":1,"volunteers":1}'::jsonb
    or board#>>'{actions,0,pending_evidence}' is not null then
    raise exception 'Public impact is inaccurate or exposes evidence';
  end if;
  if exists (select 1 from public.pilot_lake_conditions()
    where lake_id = 'c2000000-0000-4000-8000-000000000001') then
    raise exception 'Verified restoration is still listed as an open public concern';
  end if;
end $$;
rollback;
