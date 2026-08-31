-- Remove the duplicate order rows left behind by the pre-account key scheme.
--
-- Two builds wrote the same parcels under two different keys:
--
--   old   ss-<order id>                    (no acctId, no dateSource)
--   new   ss-<account id>-<order id>       (written by the scheduled sync)
--
-- Starshipit order ids are globally unique on this tenant, so both rows are the
-- same shipment and every figure counts it twice.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- RUN THIS ONLY AFTER THE NEW BUILD IS LIVE on the teamaccess link.
-- While the old build is still deployed, any browser with a tab open writes the
-- old-scheme rows straight back, so this would clear them for a minute and then
-- they would return. The app collapses them on the way in either way, so there
-- is no rush — this is tidying, not a fix.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Look before deleting. This changes nothing.
select count(*) filter (where id like 'ss-msq%')                       as account_keyed,
       count(*) filter (where id not like 'ss-msq%')                   as legacy,
       count(*) filter (where id not like 'ss-msq%' and exists (
         select 1 from public.ss_orders m
         where m.id like 'ss-msq%'
           and m.data->>'ssId' = public.ss_orders.data->>'ssId'))      as legacy_with_a_twin,
       count(*) filter (where id not like 'ss-msq%' and not exists (
         select 1 from public.ss_orders m
         where m.id like 'ss-msq%'
           and m.data->>'ssId' = public.ss_orders.data->>'ssId'))      as legacy_alone
from public.ss_orders;

-- 2. Delete only the ones that have an account-keyed twin carrying the same
--    Starshipit order id. A legacy row with no twin is the only copy of that
--    order and is left alone — it will be superseded naturally once the sync
--    reaches its account, and dropping it now would lose the order outright.
delete from public.ss_orders l
where l.id not like 'ss-msq%'
  and coalesce(l.data->>'ssId', '') <> ''
  and exists (
    select 1 from public.ss_orders m
    where m.id like 'ss-msq%'
      and m.data->>'ssId' = l.data->>'ssId'
  );

-- 3. Confirm.
select count(*) as rows_left,
       count(*) filter (where id not like 'ss-msq%') as legacy_left
from public.ss_orders;
