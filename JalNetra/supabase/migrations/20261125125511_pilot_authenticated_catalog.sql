begin;
create policy pilot_lake_catalog on public.pilot_lakes for select to authenticated using (slug is not null);
create policy pilot_zone_catalog on public.pilot_zones for select to authenticated using (slug is not null);
commit;
