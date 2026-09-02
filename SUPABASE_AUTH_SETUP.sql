-- CATstats authentication and role-based asset access.
-- Run this once in Supabase Dashboard > SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  created_at timestamptz not null default now()
);

insert into public.organizations (slug, name)
values ('apex', 'Apex Infra Logistics Corp'), ('caterpillar', 'Caterpillar')
on conflict (slug) do update set name = excluded.name;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  role text not null check (role in ('customer', 'cat_admin')) default 'customer',
  organization_id uuid references public.organizations(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.assets
  add column if not exists customer_organization_id uuid references public.organizations(id);

-- Assign existing demo assets to Apex. Change this per asset later if needed.
update public.assets
set customer_organization_id = (select id from public.organizations where slug = 'apex')
where customer_organization_id is null;

create or replace function public.is_cat_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'cat_admin'
  );
$$;

revoke all on function public.is_cat_admin() from public;
grant execute on function public.is_cat_admin() to authenticated;

alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.assets enable row level security;

drop policy if exists "users read own profile" on public.profiles;
create policy "users read own profile" on public.profiles
for select to authenticated using (id = auth.uid());

drop policy if exists "users read own organization" on public.organizations;
create policy "users read own organization" on public.organizations
for select to authenticated using (
  id = (select organization_id from public.profiles where profiles.id = auth.uid())
  or public.is_cat_admin()
);

drop policy if exists "customers read assigned assets" on public.assets;
create policy "customers read assigned assets" on public.assets
for select to authenticated using (
  public.is_cat_admin()
  or customer_organization_id = (
    select organization_id from public.profiles where profiles.id = auth.uid()
  )
);

drop policy if exists "admins update assets" on public.assets;
create policy "admins update assets" on public.assets
for update to authenticated
using (public.is_cat_admin())
with check (public.is_cat_admin());

-- Automatically create a restricted customer profile for new Auth users.
-- Promote Caterpillar staff explicitly with the statements below.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name, role, organization_id)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    'customer',
    (select id from public.organizations where slug = 'apex')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- AFTER creating users in Authentication > Users, assign their roles here.
-- Replace the example email addresses before running these two statements.
--
-- update public.profiles
-- set role = 'cat_admin', organization_id = (select id from public.organizations where slug='caterpillar')
-- where email = 'admin@caterpillar.com';
--
-- update public.profiles
-- set role = 'customer', organization_id = (select id from public.organizations where slug='apex')
-- where email = 'operations@apex.com';
