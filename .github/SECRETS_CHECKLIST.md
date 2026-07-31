# Future Deployment Secrets Checklist

The repository's CI workflow does not use application or deployment secrets. No secret is assumed to be configured.

Configure these only after the founder chooses and approves a deployment target:

- [ ] `SUPABASE_KEY` - backend database credential
- [ ] `OPENAI_API_KEY` - backend narrative-generation credential
- [ ] `BFL_API_KEY` - backend image-generation credential
- [ ] The chosen hosting provider's deployment credential, scoped only to this project

The deployed services also need non-secret configuration such as `SUPABASE_URL`, `VITE_API_URL`, and `ALLOWED_ORIGINS`. Keep runtime secrets in the hosting provider's secret store; do not add them to repository files or frontend variables.

See [DEPLOYMENT.md](DEPLOYMENT.md) after a hosting and access model has been selected. The current repository contains CI verification only and does not deploy the application.
