# GitHub Actions Deployment Guide

This guide explains how to deploy EduComic using GitHub Actions with your environment secrets.

## ✅ Step 1: Add Secrets to GitHub

Go to your repository: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets (you've already done this! ✓):

### Required Secrets:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/service key
- `OPENAI_API_KEY` - Your OpenAI API key
- `BFL_API_KEY` - Your Black Forest Labs API key

### Optional Secrets (depending on deployment method):
- `VITE_API_URL` - Your production backend URL (e.g., `https://api.educomic.com`)

## 🚀 Step 2: Choose Your Deployment Method

The workflow is ready to build your app. Now uncomment the deployment section that matches your hosting provider:

### Option A: Vercel (Frontend) + Railway (Backend)
**Best for:** Quick deployment with minimal config

1. **Deploy Frontend to Vercel:**
   ```bash
   # Install Vercel CLI
   npm i -g vercel
   
   # Login and link project
   cd frontend
   vercel link
   ```
   
   Add these secrets to GitHub:
   - `VERCEL_TOKEN` - Get from https://vercel.com/account/tokens
   - `VERCEL_ORG_ID` - Found in `.vercel/project.json` after linking
   - `VERCEL_PROJECT_ID` - Found in `.vercel/project.json` after linking

2. **Deploy Backend to Railway:**
   - Go to https://railway.app
   - Create new project from GitHub repo
   - Add environment variables in Railway dashboard
   - Get `RAILWAY_TOKEN` from Railway settings
   - Add `RAILWAY_TOKEN` to GitHub secrets

3. **Uncomment in `.github/workflows/deploy.yml`:**
   ```yaml
   # Lines 75-81 (Vercel)
   # Lines 83-87 (Railway)
   ```

### Option B: Single Platform (Render, Fly.io, etc.)
**Best for:** Unified deployment

1. **Render.com:**
   - Create Web Service for backend
   - Create Static Site for frontend
   - Add environment variables in Render dashboard
   - Deploy via Render's GitHub integration (no workflow changes needed)

2. **Fly.io:**
   - Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
   - Create apps: `fly launch` in backend and frontend dirs
   - Add secrets: `fly secrets set KEY=value`
   - Deploy automatically via GitHub integration

### Option C: VPS/Cloud Server (AWS, DigitalOcean, etc.)
**Best for:** Full control

1. **Set up SSH access:**
   - Generate SSH key: `ssh-keygen -t ed25519 -C "github-actions"`
   - Add public key to server: `~/.ssh/authorized_keys`
   - Add private key to GitHub secrets as `SSH_PRIVATE_KEY`

2. **Add server secrets:**
   - `SERVER_HOST` - Your server IP/domain
   - `SERVER_USER` - SSH username (e.g., `ubuntu`)

3. **Uncomment in `.github/workflows/deploy.yml`:**
   ```yaml
   # Lines 89-98 (SSH deployment)
   ```

4. **Customize deployment script:**
   ```yaml
   script: |
     cd /var/www/educomic
     git pull origin main
     
     # Backend
     cd backend
     uv sync
     sudo systemctl restart educomic-backend
     
     # Frontend
     cd ../frontend
     npm ci
     npm run build
     sudo cp -r dist/* /var/www/html/
   ```

### Option D: Docker + Container Registry
**Best for:** Containerized deployments (Kubernetes, ECS, etc.)

1. **Add registry secrets:**
   - `DOCKER_USERNAME` - Docker Hub username
   - `DOCKER_PASSWORD` - Docker Hub token

2. **Create Dockerfiles:**
   ```dockerfile
   # backend/Dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY . .
   RUN pip install uv && uv sync
   CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

   ```dockerfile
   # frontend/Dockerfile
   FROM node:20-alpine AS build
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   RUN npm run build

   FROM nginx:alpine
   COPY --from=build /app/dist /usr/share/nginx/html
   ```

3. **Uncomment in `.github/workflows/deploy.yml`:**
   ```yaml
   # Lines 100-105 (Docker build/push)
   ```

## 🔄 Step 3: Trigger Deployment

### Automatic (on push to main):
```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

### Manual (via GitHub UI):
1. Go to **Actions** tab
2. Select **Deploy EduComic** workflow
3. Click **Run workflow**
4. Select branch and click **Run workflow**

## 📊 Step 4: Monitor Deployment

1. Go to **Actions** tab in your repository
2. Click on the running workflow
3. Watch the build logs in real-time
4. Check for ✅ success or ❌ errors

## 🐛 Troubleshooting

### Build fails with "Secret not found"
- Verify secrets are added in **Settings → Secrets and variables → Actions**
- Secret names must match exactly (case-sensitive)

### Frontend build fails
- Check `VITE_API_URL` points to your production backend
- Ensure all frontend dependencies are in `package.json`

### Backend tests fail
- Tests are set to `continue-on-error: true` by default
- Remove this if you want strict test enforcement

### Deployment step skipped
- Make sure you uncommented the deployment section
- Verify all required secrets for that platform are added

## 🔐 Security Best Practices

✅ **DO:**
- Use GitHub Secrets for all sensitive data
- Rotate API keys regularly
- Use different keys for production vs development
- Enable branch protection on `main`
- Review deployment logs for exposed secrets

❌ **DON'T:**
- Commit `.env` files
- Echo secrets in workflow logs
- Use development keys in production
- Share secrets in pull request comments

## 📝 Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SUPABASE_URL` | ✅ | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | ✅ | Supabase anon key | `eyJhbGc...` |
| `OPENAI_API_KEY` | ✅ | OpenAI API key | `sk-proj-...` |
| `BFL_API_KEY` | ✅ | FLUX API key | `bfl_...` |
| `VITE_API_URL` | ⚠️ | Production backend URL | `https://api.educomic.com` |
| `ENVIRONMENT` | ✅ | Environment name | `production` |

## 🎯 Next Steps

1. ✅ Secrets added to GitHub
2. ⬜ Choose deployment platform
3. ⬜ Uncomment deployment section in workflow
4. ⬜ Add platform-specific secrets
5. ⬜ Push to `main` branch
6. ⬜ Monitor deployment in Actions tab
7. ⬜ Test production deployment
8. ⬜ Set up custom domain (optional)

## 💡 Tips

- **Test locally first:** Run `npm run build` and test the production build
- **Use staging:** Create a `staging` branch for pre-production testing
- **Monitor costs:** Set up billing alerts for API usage
- **Enable caching:** GitHub Actions can cache dependencies to speed up builds
- **Add notifications:** Integrate Slack/Discord for deployment alerts

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Vercel Deployment](https://vercel.com/docs)
- [Railway Deployment](https://docs.railway.app/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

Need help? Open an issue or check the deployment logs in the Actions tab!
