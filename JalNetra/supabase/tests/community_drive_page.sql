begin;
insert into auth.users (id,email,email_confirmed_at) values
  ('d1000000-0000-4000-8000-000000000001','drive-organizer@example.invalid',now()),
  ('d1000000-0000-4000-8000-000000000002','drive-operator@example.invalid',now());
insert into public.pilot_lakes (id,name,slug) values
  ('d2000000-0000-4000-8000-000000000001','Drive QA Lake','drive-qa-lake');
insert into public.pilot_memberships (lake_id,user_id,role) values
  ('d2000000-0000-4000-8000-000000000001','d1000000-0000-4000-8000-000000000002','operator'),
  ('d2000000-0000-4000-8000-000000000001','d1000000-0000-4000-8000-000000000001','citizen');

set local role authenticated;
select set_config('request.jwt.claim.sub','d1000000-0000-4000-8000-000000000001',true);
do $$
declare id uuid := 'd3000000-0000-4000-8000-000000000001';
begin
  perform public.pilot_drive_change('submit',jsonb_build_object(
    'id',id,'lakeId','d2000000-0000-4000-8000-000000000001','organization','Lake Friends',
    'title','Cleanup','details','Meet at the gate','startsAt',now()+interval '1 day'));
  if not exists (select 1 from jsonb_array_elements(public.pilot_drive_proposals()) d where d->>'id' = id::text)
    or exists (select 1 from jsonb_array_elements(public.pilot_drive_schedule(false)->'drives') d where d->>'id' = id::text) then
    raise exception 'Proposal visibility is incorrect';
  end if;
  begin
    perform public.pilot_drive_change('publish',jsonb_build_object('id',id));
    raise exception 'Organizer self-published';
  exception when insufficient_privilege then null;
  end;
end;
$$;

select set_config('request.jwt.claim.sub','d1000000-0000-4000-8000-000000000002',true);
select public.pilot_drive_change('publish','{"id":"d3000000-0000-4000-8000-000000000001"}');
select set_config('request.jwt.claim.sub','d1000000-0000-4000-8000-000000000001',true);
select public.pilot_community_change('d2000000-0000-4000-8000-000000000001','join',
  '{"id":"d3000000-0000-4000-8000-000000000001"}');
do $$
declare code text;
begin
  select d->>'check_in_code' into code from jsonb_array_elements(public.pilot_drive_schedule(false)->'drives') d
  where d->>'id' = 'd3000000-0000-4000-8000-000000000001';
  if code is null or code !~ '^[A-F0-9]{10}$' then raise exception 'Volunteer check-in code missing'; end if;
  perform set_config('request.jwt.claim.sub','d1000000-0000-4000-8000-000000000002',true);
  if public.pilot_community_board('d2000000-0000-4000-8000-000000000001')#>>'{campaigns,0,roster,0,check_in_code}' is distinct from code
    then raise exception 'Operator sees a different check-in code'; end if;
  if exists (select 1 from jsonb_array_elements(public.pilot_drive_schedule(false)->'drives') d
    where d->>'id' = 'd3000000-0000-4000-8000-000000000001' and d->>'check_in_code' is not null)
    then raise exception 'Another account can read a volunteer check-in code'; end if;
end $$;
reset role;
insert into private.community_campaigns (id,lake_id,title,details,starts_at,status)
select id::uuid,'d2000000-0000-4000-8000-000000000001','Boundary drive','Meet at the gate',
  (date_trunc('day',now() at time zone 'Asia/Kolkata') + shift) at time zone 'Asia/Kolkata',status
from (values
  ('d3000000-0000-4000-8000-000000000002',interval '0', 'open'),
  ('d3000000-0000-4000-8000-000000000003',interval '-1 minute','open'),
  ('d3000000-0000-4000-8000-000000000004',interval '1 day','open'),
  ('d3000000-0000-4000-8000-000000000005',interval '1 minute','cancelled')
) entries(id,shift,status);
select set_config('request.jwt.claim.sub','',true);
set local role anon;
do $$
declare agenda jsonb := public.pilot_drive_schedule(true);
begin
  if agenda->>'date' is distinct from (now() at time zone 'Asia/Kolkata')::date::text
    or (select count(*) from jsonb_array_elements(agenda->'drives') d where d->>'id' like 'd3000000-%') <> 1
    or not exists (select 1 from jsonb_array_elements(agenda->'drives') d where d->>'id' = 'd3000000-0000-4000-8000-000000000002')
    or not exists (select 1 from jsonb_array_elements(public.pilot_drive_schedule(false)->'drives') d
      where d->>'id' = 'd3000000-0000-4000-8000-000000000001' and d->>'organization' = 'Lake Friends') then
    raise exception 'Public drive schedule is incorrect';
  end if;
end;
$$;
set local role authenticated;
select set_config('request.jwt.claim.sub','d1000000-0000-4000-8000-000000000002',true);
select public.pilot_community_change('d2000000-0000-4000-8000-000000000001','campaign_cancel',
  '{"id":"d3000000-0000-4000-8000-000000000001"}');
select set_config('request.jwt.claim.sub','d1000000-0000-4000-8000-000000000001',true);
do $$ begin
  if public.pilot_drive_proposals()#>>'{0,status}' is distinct from 'cancelled' then
    raise exception 'Organizer sees stale publication status';
  end if;
end $$;
rollback;
