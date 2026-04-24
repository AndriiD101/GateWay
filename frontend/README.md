# Gateway Frontend - Azure Deployment

This is a standalone frontend application for the Gateway project, designed to be independently deployed to Azure Container Instances, Azure App Service, or any cloud platform.

## 📋 Overview

- **Frontend**: HTML, CSS, JavaScript (Vanilla JS with ES6 modules)
- **Server**: Nginx reverse proxy
- **Communication**: REST API calls to a separate backend service
- **Deployment**: Docker containerized for cloud deployment

## 🚀 Quick Start

### Local Development with Docker

1. **Copy the environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit .env** with your backend URL:
   ```env
   BACKEND_API_URL=http://localhost:8000
   ```

3. **Run with docker-compose**:
   ```bash
   docker-compose up -d
   ```

4. **Access the app**:
   Open http://localhost:3000 in your browser

### Manual Build & Run

1. **Build the Docker image**:
   ```bash
   docker build -t gateway-frontend:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     -p 3000:80 \
     -e BACKEND_API_URL=http://localhost:8000 \
     gateway-frontend:latest
   ```

## 🌐 Environment Configuration

### Environment Variables

The frontend uses the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKEND_API_URL` | URL to your backend service | `http://localhost:8000` or `https://your-api.azurewebsites.net` |

### Setting Environment Variables

**In Docker:**
```bash
docker run -e BACKEND_API_URL=https://your-backend.azurewebsites.net gateway-frontend
```

**In docker-compose.yml:**
```yaml
services:
  frontend:
    environment:
      - BACKEND_API_URL=https://your-backend.azurewebsites.net
```

**In Azure Container Instances:**
Set via Azure Portal or CLI:
```bash
az container create \
  --resource-group myResourceGroup \
  --name gateway-frontend \
  --image myregistry.azurecr.io/gateway-frontend:latest \
  --ports 80 \
  --environment-variables BACKEND_API_URL=https://your-backend.azurewebsites.net
```

## 🏗️ Architecture

### Communication Flow

```
Browser
   ↓
Frontend (Nginx)
   ↓
Proxy Rules (nginx.conf)
   ↓
Backend API
   ├─ /api/* → Authentication & Chat
   ├─ /ai/* → AI Services
   ├─ /trips/* → Trip Management
   ├─ /blob/* → Blob Storage
   └─ /health → Health Check
```

### Proxy Configuration

The `nginx.conf` includes the following proxy routes:

- **`/api/*`** → Authentication and chat endpoints
- **`/ai/*`** → AI trip planning
- **`/trips/*`** → Trip CRUD operations
- **`/blob/*`** → Blob storage operations
- **`/health`** → Backend health check

## 📦 File Structure

```
frontend-azure/
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Local development compose file
├── entrypoint.sh          # Script to substitute env vars
├── nginx.conf             # Nginx proxy configuration (template)
├── .env.example           # Example environment file
├── README.md              # This file
├── index.html             # Main HTML page
├── gateway_auth.js        # Authentication module (ES6)
├── gateway_auth_old.js    # Legacy auth (backup)
├── script.js              # Main application script
└── styles/                # CSS and static assets
    ├── style.css
    └── pictures/          # Images and logos
```

## 🔌 API Communication

The frontend communicates with the backend using relative URLs:

```javascript
// These URLs are automatically proxied by Nginx
fetch('/api/login', { method: 'POST', ... })
fetch('/ai/plan-trip', { method: 'POST', ... })
fetch('/trips', { method: 'GET', ... })
```

Nginx translates these to the backend URL specified in `BACKEND_API_URL`.

## 🔐 CORS & Security

The proxy is configured to:
- Forward real IP addresses (`X-Real-IP`, `X-Forwarded-For`)
- Forward protocol (`X-Forwarded-Proto`)
- Maintain host headers for backend validation
- Cache static assets (30 days)

## ☁️ Azure Deployment

### Option 1: Azure Container Instances (ACI)

1. **Build and push to Azure Container Registry**:
   ```bash
   az acr build --registry myregistry --image gateway-frontend:latest .
   ```

2. **Create container instance**:
   ```bash
   az container create \
     --resource-group myResourceGroup \
     --name gateway-frontend \
     --image myregistry.azurecr.io/gateway-frontend:latest \
     --ports 80 \
     --registry-login-server myregistry.azurecr.io \
     --registry-username <username> \
     --registry-password <password> \
     --environment-variables BACKEND_API_URL=https://your-backend.azurewebsites.net
   ```

### Option 2: Azure App Service

1. **Create App Service**:
   ```bash
   az appservice plan create \
     --name myServicePlan \
     --resource-group myResourceGroup \
     --sku B1 --is-linux
   
   az webapp create \
     --resource-group myResourceGroup \
     --plan myServicePlan \
     --name gateway-frontend \
     --deployment-container-image-name myregistry.azurecr.io/gateway-frontend:latest
   ```

2. **Configure environment variables**:
   ```bash
   az webapp config appsettings set \
     --name gateway-frontend \
     --resource-group myResourceGroup \
     --settings BACKEND_API_URL=https://your-backend.azurewebsites.net
   ```

### Option 3: Azure Kubernetes Service (AKS)

Create a Kubernetes deployment:
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
        image: myregistry.azurecr.io/gateway-frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_API_URL
          value: https://your-backend.azurewebsites.net
```

## 🧪 Testing

### Health Check

Test if the frontend is running:
```bash
curl http://localhost:3000
```

### Backend Connectivity

Test if the frontend can reach the backend:
```bash
curl http://localhost:3000/health
```

## 📝 Troubleshooting

### "Cannot connect to the server"

1. Check `BACKEND_API_URL` is correct
2. Ensure backend service is running and accessible
3. Check firewall rules in Azure
4. Verify DNS resolution for the backend URL

### Nginx proxy errors (502 Bad Gateway)

1. Verify `BACKEND_API_URL` environment variable is set
2. Check backend service is reachable from the container
3. View nginx logs: `docker logs gateway_frontend`

### Static assets not loading

1. Ensure `styles/` and `pictures/` folders are properly copied in Dockerfile
2. Check nginx cache headers are not causing issues
3. Clear browser cache (Ctrl+Shift+Delete)

## 📚 Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Azure Container Instances](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Azure App Service](https://docs.microsoft.com/en-us/azure/app-service/)

## 🔄 Integration with Backend

For the frontend to work correctly, your backend must:

1. **Accept requests from your frontend URL** (Configure CORS if needed)
2. **Provide the following endpoints**:
   - `POST /api/login` - User authentication
   - `POST /api/register` - User registration
   - `GET/POST /api/chat` - Chat functionality
   - `POST /ai/plan-trip` - AI trip planning
   - `GET /trips` - List trips
   - `POST /trips` - Create trip
   - `PUT /trips/:id` - Update trip
   - `DELETE /trips/:id` - Delete trip
   - `GET /blob/*` - Blob storage operations
   - `GET /health` - Health check

## 📞 Support

For issues or questions, please refer to the main Gateway project documentation or create an issue in the repository.
