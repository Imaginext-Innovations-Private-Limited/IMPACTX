begin;
insert into auth.users (id,email,email_confirmed_at) values
 ('a1010000-0000-4000-8000-000000000001','pilot-citizen-one@example.invalid',now()),
 ('a1010000-0000-4000-8000-000000000002','pilot-citizen-two@example.invalid',now()),
 ('a1010000-0000-4000-8000-000000000003','pilot-operator@example.invalid',now()),
 ('a1010000-0000-4000-8000-000000000004','pilot-admin@example.invalid',now());
insert into public.pilot_memberships (lake_id,user_id,role)
select l.id, u.id::uuid, u.role from public.pilot_lakes l cross join (values
 ('a1010000-0000-4000-8000-000000000001','citizen'),
 ('a1010000-0000-4000-8000-000000000002','citizen'),
 ('a1010000-0000-4000-8000-000000000003','operator'),
 ('a1010000-0000-4000-8000-000000000004','admin')) u(id,role)
where l.slug='bellandur-lake';
insert into public.pilot_reports(id,lake_id,zone_id,reporter_id,photo_path,observed_at)
select 'a1020000-0000-4000-8000-000000000001', z.lake_id,z.id,
 'a1010000-0000-4000-8000-000000000001', 'a1010000-0000-4000-8000-000000000001/a1020000-0000-4000-8000-000000000001.png', now()
from public.pilot_zones z where z.slug='bellandur-east';
insert into public.pilot_concerns(id,lake_id,zone_id,reporter_id,category,description)
select 'a1020000-0000-4000-8000-000000000002', z.lake_id,z.id,
 'a1010000-0000-4000-8000-000000000001', 'dumping','Isolated access-policy test'
from public.pilot_zones z where z.slug='bellandur-east';

set local role authenticated;
select set_config('request.jwt.claim.sub','a1010000-0000-4000-8000-000000000002',true);
do $$ begin
  if exists(select 1 from public.pilot_reports where id='a1020000-0000-4000-8000-000000000001')
    or exists(select 1 from public.pilot_concerns where id='a1020000-0000-4000-8000-000000000002') then
    raise exception 'Another citizen can read private evidence';
  end if;
  if (select count(*) from public.pilot_lakes where slug is not null) < 21 then
    raise exception 'Authenticated catalog missing';
  end if;
  begin
    insert into public.pilot_memberships(lake_id,user_id,role)
    select id,auth.uid(),'admin' from public.pilot_lakes where slug='ulsoor-lake';
    raise exception 'Citizen self-assigned administrator role';
  exception when insufficient_privilege then null;
  end;
  begin
    insert into public.pilot_review_events(lake_id,report_id,action,note)
    select id,'a1020000-0000-4000-8000-000000000001','dismiss','test'
    from public.pilot_lakes where slug='bellandur-lake';
    raise exception 'Citizen can review reports';
  exception when insufficient_privilege then null;
  end;
end $$;
select set_config('request.jwt.claim.sub','a1010000-0000-4000-8000-000000000003',true);
do $$ declare affected bigint; begin
  if not exists(select 1 from public.pilot_reports where id='a1020000-0000-4000-8000-000000000001')
    or not exists(select 1 from public.pilot_concerns where id='a1020000-0000-4000-8000-000000000002') then
    raise exception 'Assigned operator cannot see citizen evidence';
  end if;
  insert into public.pilot_review_events(lake_id,report_id,action,note)
  select id,'a1020000-0000-4000-8000-000000000001','dismiss','test'
  from public.pilot_lakes where slug='bellandur-lake';
  update public.pilot_memberships set role='operator'
  where user_id='a1010000-0000-4000-8000-000000000002';
  get diagnostics affected = row_count;
  if affected <> 0 then raise exception 'Operator can change account roles'; end if;
end $$;
select set_config('request.jwt.claim.sub','a1010000-0000-4000-8000-000000000004',true);
do $$ declare affected bigint; begin
  update public.pilot_memberships set role='operator'
  where user_id='a1010000-0000-4000-8000-000000000002'
    and lake_id=(select id from public.pilot_lakes where slug='bellandur-lake');
  get diagnostics affected = row_count;
  if affected <> 1 then raise exception 'Administrator cannot change role'; end if;
end $$;
reset role;
rollback;
select 'pilot access checks passed' as result;
