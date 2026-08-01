# Future hosted Supabase boundary

Supabase is not used by, required for, or supported as a setup step for EduComic's local private profile. The private application defaults to SQLite and local files as documented in [README.md](README.md).

A future hosted release may use Supabase PostgreSQL and private Storage only after it implements real authentication, ownership and membership enforcement, tenant isolation, retention, and operational controls. That hosted design must be deny-by-default:

- keep secret and service-role keys on trusted servers only;
- expose no table or bucket publicly by default;
- enable RLS on every exposed table and add ownership-aware policies;
- treat authentication and row ownership as separate checks;
- use private object storage with authorized, expiring delivery;
- test cross-tenant access denial before deployment.

Do not point the current unauthenticated localhost API at a hosted database or expose it to the Internet. Hosted provisioning instructions belong to a separate, founder-approved hosted specification.
