# GATEWAY Frontend Separation - Quick Setup Guide

The frontend has been separated from the main project to enable independent deployment to Azure Cloud or other cloud providers.

## 📁 Project Structure

```
GATEWAY/
├── frontend/              # Original integrated frontend (legacy)
├── frontend-azure/        # NEW: Standalone frontend for cloud deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   ├── nginx.conf
│   ├── index.html
│   ├── gateway_auth.js
│   ├── script.js
│   ├── styles/
│   ├── .env.example
│   ├── README.md          # Frontend documentation
│   ├── AZURE_DEPLOYMENT.md # Azure deployment guide
│   └── .gitignore
├── backend_fastapi/       # Backend API
├── docker-compose.yml     # Main orchestration (backend only)
└── README.md
```

## 🚀 Quick Start

### Local Development

**Option A: Frontend & Backend Together (Docker)**
```bash
cd frontend-azure
docker-compose up -d
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

**Option B: Backend Only (from root)**
```bash
docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:8080 (using original frontend folder)
```

**Option C: Frontend with External Backend**
```bash
cd frontend-azure
cp .env.example .env
# Edit .env and set BACKEND_API_URL to your backend URL
docker-compose up -d
```

### Azure Deployment

The `frontend-azure` folder is specifically configured for Azure deployment:

```bash
cd frontend-azure
# See AZURE_DEPLOYMENT.md for detailed steps
```

**Quick Azure CLI Deploy:**
```bash
az container create \
  --resource-group my-group \
  --name gateway-frontend \
  --image gatewaycr.azurecr.io/gateway-frontend:latest \
  --ports 80 \
  --environment-variables BACKEND_API_URL=https://my-backend.azurewebsites.net
```

## 🔧 Key Features

✅ **Independent Deployment** - Deploy frontend and backend separately  
✅ **Environment Configuration** - Backend URL configurable via environment variables  
✅ **Azure Ready** - Docker image optimized for Azure Container Instances, App Service, and AKS  
✅ **Nginx Proxy** - Reverse proxy configured for seamless API communication  
✅ **SSL/TLS Support** - Ready for HTTPS deployment  
✅ **Multi-cloud** - Works with any cloud provider supporting Docker  

## 📝 Configuration

### Backend API URL

The frontend communicates with the backend through environment variable `BACKEND_API_URL`:

**Local Development:**
```env
BACKEND_API_URL=http://localhost:8000
```

**Azure Container Instances:**
```bash
--environment-variables BACKEND_API_URL=https://my-backend-service.azurewebsites.net
```

**Azure App Service:**
```bash
az webapp config appsettings set \
  --name my-app \
  --resource-group my-group \
  --settings BACKEND_API_URL=https://my-backend.azurewebsites.net
```

## 📚 Documentation

- **Frontend Setup**: See [frontend-azure/README.md](frontend-azure/README.md)
- **Azure Deployment**: See [frontend-azure/AZURE_DEPLOYMENT.md](frontend-azure/AZURE_DEPLOYMENT.md)
- **Backend Setup**: See [backend_fastapi/README.md](backend_fastapi/README.md)
- **Main Project**: See [README.md](README.md)

## 🔄 Migration Guide

If you're moving from the integrated frontend to the separate one:

1. **Backup your current setup**
   ```bash
   git checkout -b backup-integrated-frontend
   ```

2. **Use the new frontend-azure folder**
   ```bash
   cd frontend-azure
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your backend URL
   ```

4. **Deploy to Azure**
   ```bash
   # Follow AZURE_DEPLOYMENT.md
   ```

## ❓ FAQ

**Q: Can I still use the old integrated frontend?**  
A: Yes! The `frontend` folder remains unchanged and works with the old docker-compose setup.

**Q: Do I need to change the backend?**  
A: No changes needed to the backend. The frontend uses the same API endpoints.

**Q: How do I connect frontend and backend in Azure?**  
A: Set the `BACKEND_API_URL` environment variable to your backend service URL (e.g., `https://my-backend.azurewebsites.net`).

**Q: Can I deploy just the frontend?**  
A: Yes! That's the main purpose of `frontend-azure`. It can be deployed independently.

**Q: What if the backend URL changes?**  
A: Update the `BACKEND_API_URL` environment variable in your deployment:
   - Azure Portal: Settings → Configuration → Application settings
   - Azure CLI: `az webapp config appsettings set`
   - Docker: `-e BACKEND_API_URL=new-url`

## 🆘 Troubleshooting

**Frontend shows "Cannot connect to server"**
- Check `BACKEND_API_URL` is set correctly
- Ensure backend service is running and accessible
- Verify CORS is configured on the backend

**Nginx proxy errors (502 Bad Gateway)**
- Check environment variable is properly substituted: `docker logs container-id`
- Verify backend URL format includes protocol (http:// or https://)
- Test backend connectivity: `curl -I YOUR_BACKEND_URL/health`

**Images not loading**
- Ensure `styles/pictures/` folder was copied
- Check Dockerfile includes all necessary files
- Verify static file paths in index.html

## 📞 Support

For issues or questions:
1. Check the README files in each folder
2. See AZURE_DEPLOYMENT.md for deployment issues
3. Review backend_fastapi/README.md for API issues
4. Check main README.md for general project info
