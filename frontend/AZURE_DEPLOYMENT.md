# Deployment Guide for Separate Frontend on Azure

This guide explains how to deploy the **frontend-azure** folder as a standalone service to Azure Cloud while keeping the backend separate.

## 📋 Prerequisites

- Azure account (free tier or paid)
- Docker installed locally
- Azure CLI installed
- A backend service already deployed (or URL to connect to)

---

## 🚀 Deployment Options

### Option 1: Azure Container Instances (ACI) - Simplest & Fastest

**Step 1: Login to Azure**
```bash
az login
```

**Step 2: Create a Resource Group** (if you don't have one)
```bash
az group create \
  --name gateway-resources \
  --location westeurope
```

**Step 3: Create Azure Container Registry** (ACR)
```bash
az acr create \
  --resource-group gateway-resources \
  --name gatewaycr \
  --sku Basic
```

**Step 4: Build and Push Docker Image**
```bash
# Login to ACR
az acr login --name gatewaycr

# Build the image
az acr build \
  --registry gatewaycr \
  --image gateway-frontend:latest \
  ./frontend-azure/

# Or build locally and push
docker build -t gatewaycr.azurecr.io/gateway-frontend:latest ./frontend-azure/
docker push gatewaycr.azurecr.io/gateway-frontend:latest
```

**Step 5: Deploy Container Instance**
```bash
az container create \
  --resource-group gateway-resources \
  --name gateway-frontend \
  --image gatewaycr.azurecr.io/gateway-frontend:latest \
  --registry-login-server gatewaycr.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --ports 80 \
  --environment-variables BACKEND_API_URL=https://your-backend-url.azurewebsites.net \
  --restart-policy OnFailure \
  --cpu 1 --memory 1
```

**Step 6: Get the IP Address**
```bash
az container show \
  --resource-group gateway-resources \
  --name gateway-frontend \
  --query ipAddress.fqdn \
  --output table
```

---

### Option 2: Azure App Service - Recommended for Production

**Step 1: Create App Service Plan**
```bash
az appservice plan create \
  --name gatewayPlan \
  --resource-group gateway-resources \
  --sku B1 \
  --is-linux
```

**Step 2: Create Web App with Docker**
```bash
az webapp create \
  --resource-group gateway-resources \
  --plan gatewayPlan \
  --name gateway-frontend-app \
  --deployment-container-image-name gatewaycr.azurecr.io/gateway-frontend:latest
```

**Step 3: Configure Container Settings**
```bash
az webapp config container set \
  --name gateway-frontend-app \
  --resource-group gateway-resources \
  --docker-custom-image-name gatewaycr.azurecr.io/gateway-frontend:latest \
  --docker-registry-server-url https://gatewaycr.azurecr.io \
  --docker-registry-server-user <username> \
  --docker-registry-server-password <password>
```

**Step 4: Set Environment Variables**
```bash
az webapp config appsettings set \
  --name gateway-frontend-app \
  --resource-group gateway-resources \
  --settings BACKEND_API_URL=https://your-backend-url.azurewebsites.net
```

**Step 5: Access Your App**
Your frontend will be available at: `https://gateway-frontend-app.azurewebsites.net`

---

### Option 3: Azure Kubernetes Service (AKS) - For Scalability

**Step 1: Create AKS Cluster**
```bash
az aks create \
  --resource-group gateway-resources \
  --name gatewayCluster \
  --node-count 1 \
  --attach-acr gatewaycr
```

**Step 2: Get Credentials**
```bash
az aks get-credentials \
  --resource-group gateway-resources \
  --name gatewayCluster
```

**Step 3: Create Kubernetes Deployment (k8s-deployment.yaml)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway-frontend
  template:
    metadata:
      labels:
        app: gateway-frontend
    spec:
      containers:
      - name: frontend
        image: gatewaycr.azurecr.io/gateway-frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_API_URL
          value: https://your-backend-url.azurewebsites.net
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"

---
apiVersion: v1
kind: Service
metadata:
  name: gateway-frontend-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: gateway-frontend
```

**Step 4: Deploy to Kubernetes**
```bash
kubectl apply -f k8s-deployment.yaml
```

**Step 5: Check Deployment Status**
```bash
kubectl get svc gateway-frontend-service
```

---

## 🔧 Managing Environment Variables

### Local Development
```bash
cd frontend-azure
docker run -d \
  -p 3000:80 \
  -e BACKEND_API_URL=http://localhost:8000 \
  --name gateway-frontend \
  gateway-frontend:latest
```

### Azure App Service (Portal)
1. Go to Settings → Configuration
2. Under "Application settings", add:
   - Name: `BACKEND_API_URL`
   - Value: `https://your-backend-url.azurewebsites.net`
3. Save and restart

### Azure CLI
```bash
az webapp config appsettings set \
  --name gateway-frontend-app \
  --resource-group gateway-resources \
  --settings BACKEND_API_URL=https://your-backend.azurewebsites.net
```

---

## 🔐 Security Considerations

### 1. Enable HTTPS Only
```bash
az webapp update \
  --name gateway-frontend-app \
  --resource-group gateway-resources \
  --set httpsOnly=true
```

### 2. Add Custom Domain
```bash
az webapp config hostname add \
  --name gateway-frontend-app \
  --resource-group gateway-resources \
  --hostname yourdomain.com
```

### 3. Configure CORS on Backend
Your backend should allow requests from your frontend URL:

**FastAPI Example (backend_fastapi/app/main.py)**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gateway-frontend-app.azurewebsites.net",
        "https://yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Monitoring & Debugging

### View Container Logs (ACI)
```bash
az container logs \
  --resource-group gateway-resources \
  --name gateway-frontend
```

### View App Service Logs
```bash
az webapp log download \
  --name gateway-frontend-app \
  --resource-group gateway-resources
```

### Check Backend Connectivity
```bash
# In App Service → Log stream
# Or SSH into container and test:
curl -I https://your-backend-url/health
```

---

## 🚨 Troubleshooting

### "502 Bad Gateway"
- Check `BACKEND_API_URL` environment variable
- Ensure backend service is running and accessible
- Check firewall rules in Azure

### "Cannot connect to the server"
- Verify backend URL format (must include protocol: `https://`)
- Test backend connectivity: `curl -I YOUR_BACKEND_URL/health`
- Check Azure Application Insights for errors

### Nginx Configuration Issues
- Container logs will show: `docker logs gateway-frontend`
- Check that environment variables were properly substituted in nginx.conf

---

## 🔄 CI/CD Pipeline Example (GitHub Actions)

**File: .github/workflows/deploy.yml**
```yaml
name: Deploy Frontend to Azure

on:
  push:
    branches: [main]
    paths: ['frontend-azure/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t gatewaycr.azurecr.io/gateway-frontend:${{ github.sha }} ./frontend-azure/
      
      - name: Login to ACR
        uses: docker/login-action@v1
        with:
          registry: gatewaycr.azurecr.io
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      
      - name: Push image
        run: docker push gatewaycr.azurecr.io/gateway-frontend:${{ github.sha }}
      
      - name: Update App Service
        run: |
          az appservice web config container set \
            --name gateway-frontend-app \
            --resource-group gateway-resources \
            --docker-custom-image-name gatewaycr.azurecr.io/gateway-frontend:${{ github.sha }}
```

---

## 📞 Support & Further Help

- [Azure Container Instances Documentation](https://docs.microsoft.com/azure/container-instances/)
- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- Gateway Project Documentation: See main [README.md](../README.md)
