begin;

alter table public.pilot_memberships drop constraint pilot_memberships_role_check;
alter table public.pilot_memberships add constraint pilot_memberships_role_check check (role in ('citizen','operator','admin'));
alter table public.pilot_lakes add column slug text unique;
alter table public.pilot_zones add column slug text;
alter table public.pilot_zones add unique (lake_id, slug);
alter table public.pilot_reports add column photo_hash text check (photo_hash ~ '^[a-f0-9]{16}$');
grant insert (lake_id, user_id, role) on public.pilot_memberships to authenticated;
grant insert (photo_hash) on public.pilot_reports to authenticated;
create policy pilot_memberships_self_enroll on public.pilot_memberships for insert to authenticated
with check (user_id = (select auth.uid()) and role = 'citizen'
  and not coalesce((select auth.jwt()->>'is_anonymous') = 'true', false));

alter policy pilot_reports_read_member on public.pilot_reports using (exists (
  select 1 from public.pilot_memberships m where m.lake_id=pilot_reports.lake_id
    and m.user_id=(select auth.uid()) and (m.role in ('operator','admin') or reporter_id=(select auth.uid()))
));

create table public.pilot_concerns (
  id uuid primary key default gen_random_uuid(), lake_id uuid not null, zone_id uuid not null,
  reporter_id uuid not null default auth.uid() references auth.users(id),
  category text not null check (category in ('dumping','suspected-discharge','sewage','other')),
  description text not null check (length(btrim(description)) between 1 and 500),
  created_at timestamptz not null default now(),
  foreign key (lake_id, zone_id) references public.pilot_zones(lake_id,id)
);
create index pilot_concerns_lake_recent on public.pilot_concerns(lake_id,created_at desc);
alter table public.pilot_concerns enable row level security;
revoke all on public.pilot_concerns from public, anon, authenticated;
grant select on public.pilot_concerns to authenticated;
grant insert (id, lake_id, zone_id, category, description) on public.pilot_concerns to authenticated;
create policy pilot_concerns_read on public.pilot_concerns for select to authenticated using (exists (
  select 1 from public.pilot_memberships m where m.lake_id=pilot_concerns.lake_id and m.user_id=(select auth.uid())
    and (m.role in ('operator','admin') or reporter_id=(select auth.uid()))
));
create policy pilot_concerns_write on public.pilot_concerns for insert to authenticated with check (
  reporter_id=(select auth.uid()) and exists (select 1 from public.pilot_memberships m
  where m.lake_id=pilot_concerns.lake_id and m.user_id=(select auth.uid()) and m.role='citizen')
);

alter table public.pilot_reports add unique (lake_id,id);
create table public.pilot_review_events (
  id uuid primary key default gen_random_uuid(), lake_id uuid not null, report_id uuid not null,
  actor_id uuid not null default auth.uid() references auth.users(id),
  action text not null check (action in ('model','confirm','correct','dismiss','duplicate')),
  category text check (category in ('foam','algae_like_growth','dumping')),
  note text check (length(note) <= 500),
  model_output jsonb check (pg_column_size(model_output) <= 4096),
  duplicate_of uuid,
  created_at timestamptz not null default now(),
  foreign key (lake_id,report_id) references public.pilot_reports(lake_id,id),
  foreign key (lake_id,duplicate_of) references public.pilot_reports(lake_id,id),
  check ((action='duplicate') = (duplicate_of is not null)),
  check (duplicate_of is null or duplicate_of <> report_id),
  check ((action='model') = (model_output is not null)),
  check ((action in ('confirm','correct')) = (category is not null))
);
create index pilot_events_report_recent on public.pilot_review_events(report_id,created_at desc);
create unique index pilot_one_model_result on public.pilot_review_events(report_id) where action='model';
alter table public.pilot_review_events enable row level security;
revoke all on public.pilot_review_events from public, anon, authenticated;
grant select on public.pilot_review_events to authenticated;
grant insert (lake_id, report_id, action, category, note, model_output, duplicate_of) on public.pilot_review_events to authenticated;
create policy pilot_events_read on public.pilot_review_events for select to authenticated using (exists (
  select 1 from public.pilot_reports r where r.id=pilot_review_events.report_id
));
create policy pilot_events_write on public.pilot_review_events for insert to authenticated with check (
  actor_id=(select auth.uid()) and exists (select 1 from public.pilot_memberships m
  where m.lake_id=pilot_review_events.lake_id and m.user_id=(select auth.uid()) and m.role in ('operator','admin'))
);

create or replace function public.jalnetra_pilot_status() returns jsonb
  language sql stable security invoker set search_path = ''
  as $$ select jsonb_build_object('ready', true, 'schemaVersion', 2) $$;

commit;

begin;
insert into public.pilot_lakes (name,slug) values
('Ulsoor Lake', 'ulsoor-lake'),
('Sankey Tank', 'sankey-tank'),
('Agara Lake', 'agara-lake'),
('Madiwala Lake', 'madiwala-lake'),
('Bellandur Lake', 'bellandur-lake'),
('Devanahalli Lake', 'devanahalli-lake'),
('Doddajala Lake', 'doddajala-lake'),
('Hesaraghatta Lake', 'hesaraghatta-lake'),
('Yelahanka Lake', 'yelahanka-lake'),
('Jakkur Lake', 'jakkur-lake'),
('Rachenahalli Lake', 'rachenahalli-lake'),
('Hebbal Lake', 'hebbal-lake'),
('Chikkabanavara Lake', 'chikkabanavara-lake'),
('Kommaghatta Lake', 'kommaghatta-lake'),
('Kengeri Lake', 'kengeri-lake'),
('Varthur Lake', 'varthur-lake'),
('Doddanekundi Lake', 'doddanekundi-lake'),
('Kalkere Lake', 'kalkere-lake'),
('Hulimavu Lake', 'hulimavu-lake'),
('Begur Lake', 'begur-lake'),
('Veerasandra Lake', 'veerasandra-lake')
on conflict (slug) do nothing;
insert into public.pilot_zones (lake_id,name,slug) select l.id,z.zone_name,z.zone_slug
from (values
('ulsoor-lake', 'North sector', 'ulsoor-north'),
('ulsoor-lake', 'East sector', 'ulsoor-east'),
('ulsoor-lake', 'South sector', 'ulsoor-south'),
('ulsoor-lake', 'West sector', 'ulsoor-west'),
('sankey-tank', 'North sector', 'sankey-north'),
('sankey-tank', 'East sector', 'sankey-east'),
('sankey-tank', 'South sector', 'sankey-south'),
('sankey-tank', 'West sector', 'sankey-west'),
('agara-lake', 'North sector', 'agara-north'),
('agara-lake', 'East sector', 'agara-east'),
('agara-lake', 'South sector', 'agara-south'),
('agara-lake', 'West sector', 'agara-west'),
('madiwala-lake', 'North sector', 'madiwala-north'),
('madiwala-lake', 'East sector', 'madiwala-east'),
('madiwala-lake', 'South sector', 'madiwala-south'),
('madiwala-lake', 'West sector', 'madiwala-west'),
('bellandur-lake', 'North sector', 'bellandur-north'),
('bellandur-lake', 'East sector', 'bellandur-east'),
('bellandur-lake', 'South sector', 'bellandur-south'),
('bellandur-lake', 'West sector', 'bellandur-west'),
('devanahalli-lake', 'North sector', 'devanahalli-lake-north'),
('devanahalli-lake', 'East sector', 'devanahalli-lake-east'),
('devanahalli-lake', 'South sector', 'devanahalli-lake-south'),
('devanahalli-lake', 'West sector', 'devanahalli-lake-west'),
('doddajala-lake', 'North sector', 'doddajala-lake-north'),
('doddajala-lake', 'East sector', 'doddajala-lake-east'),
('doddajala-lake', 'South sector', 'doddajala-lake-south'),
('doddajala-lake', 'West sector', 'doddajala-lake-west'),
('hesaraghatta-lake', 'North sector', 'hesaraghatta-lake-north'),
('hesaraghatta-lake', 'East sector', 'hesaraghatta-lake-east'),
('hesaraghatta-lake', 'South sector', 'hesaraghatta-lake-south'),
('hesaraghatta-lake', 'West sector', 'hesaraghatta-lake-west'),
('yelahanka-lake', 'North sector', 'yelahanka-lake-north'),
('yelahanka-lake', 'East sector', 'yelahanka-lake-east'),
('yelahanka-lake', 'South sector', 'yelahanka-lake-south'),
('yelahanka-lake', 'West sector', 'yelahanka-lake-west'),
('jakkur-lake', 'North sector', 'jakkur-lake-north'),
('jakkur-lake', 'East sector', 'jakkur-lake-east'),
('jakkur-lake', 'South sector', 'jakkur-lake-south'),
('jakkur-lake', 'West sector', 'jakkur-lake-west'),
('rachenahalli-lake', 'North sector', 'rachenahalli-lake-north'),
('rachenahalli-lake', 'East sector', 'rachenahalli-lake-east'),
('rachenahalli-lake', 'South sector', 'rachenahalli-lake-south'),
('rachenahalli-lake', 'West sector', 'rachenahalli-lake-west'),
('hebbal-lake', 'North sector', 'hebbal-lake-north'),
('hebbal-lake', 'East sector', 'hebbal-lake-east'),
('hebbal-lake', 'South sector', 'hebbal-lake-south'),
('hebbal-lake', 'West sector', 'hebbal-lake-west'),
('chikkabanavara-lake', 'North sector', 'chikkabanavara-lake-north'),
('chikkabanavara-lake', 'East sector', 'chikkabanavara-lake-east'),
('chikkabanavara-lake', 'South sector', 'chikkabanavara-lake-south'),
('chikkabanavara-lake', 'West sector', 'chikkabanavara-lake-west'),
('kommaghatta-lake', 'North sector', 'kommaghatta-lake-north'),
('kommaghatta-lake', 'East sector', 'kommaghatta-lake-east'),
('kommaghatta-lake', 'South sector', 'kommaghatta-lake-south'),
('kommaghatta-lake', 'West sector', 'kommaghatta-lake-west'),
('kengeri-lake', 'North sector', 'kengeri-lake-north'),
('kengeri-lake', 'East sector', 'kengeri-lake-east'),
('kengeri-lake', 'South sector', 'kengeri-lake-south'),
('kengeri-lake', 'West sector', 'kengeri-lake-west'),
('varthur-lake', 'North sector', 'varthur-lake-north'),
('varthur-lake', 'East sector', 'varthur-lake-east'),
('varthur-lake', 'South sector', 'varthur-lake-south'),
('varthur-lake', 'West sector', 'varthur-lake-west'),
('doddanekundi-lake', 'North sector', 'doddanekundi-lake-north'),
('doddanekundi-lake', 'East sector', 'doddanekundi-lake-east'),
('doddanekundi-lake', 'South sector', 'doddanekundi-lake-south'),
('doddanekundi-lake', 'West sector', 'doddanekundi-lake-west'),
('kalkere-lake', 'North sector', 'kalkere-lake-north'),
('kalkere-lake', 'East sector', 'kalkere-lake-east'),
('kalkere-lake', 'South sector', 'kalkere-lake-south'),
('kalkere-lake', 'West sector', 'kalkere-lake-west'),
('hulimavu-lake', 'North sector', 'hulimavu-lake-north'),
('hulimavu-lake', 'East sector', 'hulimavu-lake-east'),
('hulimavu-lake', 'South sector', 'hulimavu-lake-south'),
('hulimavu-lake', 'West sector', 'hulimavu-lake-west'),
('begur-lake', 'North sector', 'begur-lake-north'),
('begur-lake', 'East sector', 'begur-lake-east'),
('begur-lake', 'South sector', 'begur-lake-south'),
('begur-lake', 'West sector', 'begur-lake-west'),
('veerasandra-lake', 'North sector', 'veerasandra-lake-north'),
('veerasandra-lake', 'East sector', 'veerasandra-lake-east'),
('veerasandra-lake', 'South sector', 'veerasandra-lake-south'),
('veerasandra-lake', 'West sector', 'veerasandra-lake-west')
) as z(lake_slug,zone_name,zone_slug) join public.pilot_lakes l on l.slug=z.lake_slug
on conflict (lake_id,name) do nothing;
commit;
