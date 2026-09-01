# Azure deployment

This application uses Azure Container Apps for FastAPI, WebSockets, the
scheduler, and ML engine, plus Azure Static Web Apps (Free) for React. Supabase
remains the database and Groq remains the optional summary provider.

## 1. Create the backend

Install Azure CLI, sign in, and select the subscription containing your
credits. Change the sample names where necessary.

```powershell
az login
az account set --subscription "YOUR SUBSCRIPTION NAME OR ID"
az extension add --name containerapp --upgrade

az group create --name cat-stats-rg --location centralindia
az acr create --resource-group cat-stats-rg --name YOUR_UNIQUE_ACR_NAME --sku Basic
az containerapp env create --resource-group cat-stats-rg --name cat-stats-env --location centralindia

az acr build --registry YOUR_UNIQUE_ACR_NAME --image cat-stats-backend:v1 .

az containerapp create `
  --resource-group cat-stats-rg `
  --environment cat-stats-env `
  --name cat-stats-api `
  --image YOUR_UNIQUE_ACR_NAME.azurecr.io/cat-stats-backend:v1 `
  --registry-server YOUR_UNIQUE_ACR_NAME.azurecr.io `
  --target-port 8000 `
  --ingress external `
  --cpu 0.5 `
  --memory 1.0Gi `
  --min-replicas 1 `
  --max-replicas 1 `
  --secrets supabase-url="YOUR_URL" supabase-key="YOUR_KEY" groq-api-key="YOUR_KEY" `
  --env-vars SUPABASE_URL=secretref:supabase-url SUPABASE_KEY=secretref:supabase-key GROQ_API_KEY=secretref:groq-api-key CORS_ALLOW_ORIGINS="https://YOUR_FRONTEND.azurestaticapps.net"
```

Keep both replica settings at 1. More replicas execute the in-process scheduler
more than once; zero replicas stop scheduled work and disconnect WebSockets.

If first-boot model training needs more memory, use:

```powershell
az containerapp update --resource-group cat-stats-rg --name cat-stats-api --cpu 1.0 --memory 2.0Gi
```

The backend root URL should return `{"status":"ok"}`.

## 2. Create the frontend

Create an Azure **Static Web App** on the Free plan and connect this GitHub
repository. Set app location to `frontend`, leave API location empty, and set
output location to `dist`.

Under GitHub **Settings > Secrets and variables > Actions > Variables**, add:

- `VITE_API_BASE_URL`: Container App HTTPS URL without a trailing slash.
- `VITE_WS_URL`: the same host as `wss://.../ws/live`.
- `AZURE_RESOURCE_GROUP`: `cat-stats-rg`.
- `AZURE_CONTAINER_APP_NAME`: `cat-stats-api`.
- `AZURE_ACR_NAME`: registry name without `.azurecr.io`.

The Static Web Apps wizard normally creates the
`AZURE_STATIC_WEB_APPS_API_TOKEN` repository secret. The backend workflow needs
an `AZURE_CREDENTIALS` secret for a service principal allowed to update the
resource group.

After the frontend gets its final hostname, update backend CORS if needed:

```powershell
az containerapp update `
  --resource-group cat-stats-rg `
  --name cat-stats-api `
  --set-env-vars CORS_ALLOW_ORIGINS="https://YOUR_FRONTEND.azurestaticapps.net"
```

## 3. Protect the credits

Create an Azure Cost Management budget before leaving the resources running.
Suggested alerts are 50%, 75%, and 90% of your monthly limit.

## Operational notes

- Startup-generated models use ephemeral container storage and regenerate
  after a fresh revision; persistent application data remains in Supabase.
- Never commit `backend/.env`; production values belong in Azure secrets.
- Keep one Uvicorn worker because WebSocket clients and the scheduler are held
  in process memory.
- During redeployment, the frontend reconnects its WebSocket automatically.
