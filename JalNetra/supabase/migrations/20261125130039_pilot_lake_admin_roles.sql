begin;
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;
create function private.pilot_is_lake_admin(target uuid) returns boolean
  language sql stable security definer set search_path = ''
  as $$ select exists (
    select 1 from public.pilot_memberships m where m.lake_id=target
      and m.user_id=(select auth.uid()) and m.role='admin'
  ) $$;
revoke all on function private.pilot_is_lake_admin(uuid) from public;
grant execute on function private.pilot_is_lake_admin(uuid) to authenticated;
grant update (role) on public.pilot_memberships to authenticated;
create policy pilot_memberships_admin_read on public.pilot_memberships for select to authenticated
using (private.pilot_is_lake_admin(lake_id));
create policy pilot_memberships_admin_update on public.pilot_memberships for update to authenticated
using (private.pilot_is_lake_admin(lake_id) and user_id<>(select auth.uid()) and role in ('citizen','operator'))
with check (private.pilot_is_lake_admin(lake_id) and user_id<>(select auth.uid()) and role in ('citizen','operator'));
commit;
