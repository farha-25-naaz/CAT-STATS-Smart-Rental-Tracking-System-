# CATstats login setup

This login uses Supabase Auth. It does not require a new Azure resource or a backend container deployment.

## 1. Create the database security objects

In Supabase, open **SQL Editor**, paste all of `SUPABASE_AUTH_SETUP.sql`, and select **Run**.

## 2. Create the two users

Open **Authentication > Users > Add user > Create new user**. Create:

- one Apex customer user;
- one Caterpillar administrator user.

Use real email addresses and secure passwords. Do not put either password in source control.

## 3. Assign the roles

Return to **SQL Editor** and run the following after replacing the emails:

```sql
update public.profiles
set role = 'cat_admin',
    organization_id = (select id from public.organizations where slug = 'caterpillar')
where email = 'YOUR-CATERPILLAR-ADMIN-EMAIL';

update public.profiles
set role = 'customer',
    organization_id = (select id from public.organizations where slug = 'apex')
where email = 'YOUR-APEX-CUSTOMER-EMAIL';
```

Verify the assignments:

```sql
select email, full_name, role, organization_id from public.profiles order by email;
```

## 4. Add GitHub deployment settings

In the GitHub repository open **Settings > Secrets and variables > Actions**.

Under **Variables**, add:

- `VITE_SUPABASE_URL`: the project URL from Supabase **Settings > API**.

Under **Secrets**, add:

- `VITE_SUPABASE_ANON_KEY`: the Supabase publishable/anon key.

The anon key is designed for browser applications. Never use the `service_role` or Supabase secret key here.

## 5. Deploy

Commit and push these files to `main`. The existing `azure-frontend.yml` workflow will rebuild the same Azure Static Web App. The Azure Container App, Container Registry and backend environment variables do not need to be recreated.

After the workflow completes, open the current frontend URL and test both portal choices.
