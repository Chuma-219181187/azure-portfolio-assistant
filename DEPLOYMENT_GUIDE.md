# Azure Portfolio Assistant - Complete Deployment Guide

## Executive Summary

This document provides a step-by-step guide for deploying the **Azure Portfolio Assistant** application to Microsoft Azure using GitHub Actions CI/CD pipeline. The application is containerized with Docker and deployed to Azure Container Instances (ACI) in the `centralindia` region.

**Current Deployment Status**: ✅ **LIVE**
- **Application URL**: http://20.219.177.35:5000
- **Region**: Central India (`centralindia`)
- **Status**: Running & Operational
- **Updated**: November 21, 2025

---

## Table of Contents

1. [Prerequisites & Requirements](#prerequisites--requirements)
2. [Architecture Overview](#architecture-overview)
3. [Step 1: Identify Deployment Constraints](#step-1-identify-deployment-constraints)
4. [Step 2: Set Up Azure Resources](#step-2-set-up-azure-resources)
5. [Step 3: Create Service Principal for CI/CD](#step-3-create-service-principal-for-cicd)
6. [Step 4: Configure GitHub Secrets](#step-4-configure-github-secrets)
7. [Step 5: GitHub Actions Workflow](#step-5-github-actions-workflow)
8. [Step 6: Register Required Azure Providers](#step-6-register-required-azure-providers)
9. [Step 7: Trigger Deployment](#step-7-trigger-deployment)
10. [Verification & Monitoring](#verification--monitoring)
11. [Troubleshooting](#troubleshooting)
12. [Demo Talking Points](#demo-talking-points)
13. [Quick Reference Commands](#quick-reference-commands)

---

## Prerequisites & Requirements

### Required Tools
- **Azure CLI** (`az`) - Command-line tool for Azure management
- **Git** - Version control for GitHub operations
- **GitHub Account** - Repository hosting and Actions for CI/CD
- **Azure Subscription** - Active subscription with available quota

### Optional Tools
- **Docker Desktop** - For local testing before deployment
- **GitHub CLI** (`gh`) - For GitHub operations from terminal

### Azure Subscription Constraints
⚠️ **Important**: The Azure subscription has **region restrictions** due to organizational policy.

**Allowed Regions**:
- `brazilsouth` (Brazil South)
- `uaenorth` (UAE North)
- `centralindia` (Central India) ← **Selected for this deployment**
- `spaincentral` (Spain Central)
- `southafricanorth` (South Africa North)

**Deployment Region Selected**: `centralindia`

---

## Architecture Overview

### High-Level Deployment Flow

```
Local Code Repository (GitHub)
           ↓
    GitHub Actions Workflow (on push to main)
           ↓
    ┌─────────────────────────────┐
    │   Build & Push to ACR       │
    │  - Build Docker image       │
    │  - Tag with commit SHA      │
    │  - Push to Container Registry
    └─────────────────────────────┘
           ↓
    Azure Container Registry (ACR)
           ↓
    ┌─────────────────────────────┐
    │  Deploy to ACI              │
    │  - Pull image from ACR      │
    │  - Create container instance│
    │  - Allocate public IP       │
    │  - Expose port 5000         │
    └─────────────────────────────┘
           ↓
    Azure Container Instances (ACI)
           ↓
    Public Endpoint Available
```

### Azure Resources Created

| Resource | Type | Status |
|---|---|---|
| Resource Group | `rg-portfolio-assistant` | ✅ Created |
| Container Registry | `acrportfolio7988` | ✅ Created |
| Container Instance | `portfolio-assistant` | ✅ Running |
| Service Principal | `github-actions-deployer` | ✅ Created |

---

## Step 1: Identify Deployment Constraints

### Problems Encountered
1. **Docker not installed locally** - Cannot build images on local machine
2. **Azure region policy restriction** - Subscription limited to 5 specific regions
3. **Default workflow region** - Original workflow was configured for `eastus` (not allowed)

### Solution Applied
→ Use **GitHub Actions CI/CD** to build in cloud, deploy to **allowed region** (`centralindia`)

### Commands to Check Constraints

**Check Docker availability:**
```bash
docker --version
```

**Check allowed regions policy:**
```bash
az policy assignment list --query "[?displayName=='Allowed resource deployment regions']" -o json
```

**Query allowed regions parameter:**
```bash
az rest --method get \
  --uri "/subscriptions/<YOUR_SUBSCRIPTION_ID>/providers/Microsoft.Authorization/policyAssignments/sys.regionrestriction?api-version=2021-06-01" \
  --query "properties.parameters.listOfAllowedLocations.value" \
  -o json
```

---

## Step 2: Set Up Azure Resources

### 2.1 Install & Authenticate Azure CLI

**Install Azure CLI:**
```bash
# Windows (PowerShell as Admin)
winget install -e --id Microsoft.AzureCLI

# Or download MSI from: https://aka.ms/installazurecliwindows
```

**Login to Azure:**
```bash
az login
# Opens browser for interactive authentication
```

### 2.2 Create Resource Group

```bash
az group create \
  --name rg-portfolio-assistant \
  --location centralindia
```

### 2.3 Register Required Providers

**Register Container Registry Provider:**
```bash
az provider register --namespace Microsoft.ContainerRegistry --wait
```

**Register Container Instances Provider:**
```bash
az provider register --namespace Microsoft.ContainerInstance --wait
```

**Verify registration:**
```bash
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState" -o tsv
az provider show --namespace Microsoft.ContainerInstance --query "registrationState" -o tsv
# Both should output: Registered
```

### 2.4 Create Azure Container Registry (ACR)

```bash
az acr create \
  --resource-group rg-portfolio-assistant \
  --name acrportfolio<RANDOM_NUMBER> \
  --sku Basic \
  --admin-enabled true \
  --location centralindia
```

**Note the following from output:**
- Registry name: `acrportfolio<RANDOM_NUMBER>`
- Login server: `acrportfolio<RANDOM_NUMBER>.azurecr.io`

**Get ACR Credentials:**
```bash
az acr credential show \
  --resource-group rg-portfolio-assistant \
  --name acrportfolio<RANDOM_NUMBER> \
  -o json
```

**Save these for later use:**
- `username`: Registry login username
- `passwords[0].value`: Registry admin password

---

## Step 3: Create Service Principal for CI/CD

### What is a Service Principal?
A **service principal** is an identity for automated processes (like GitHub Actions) to authenticate with Azure without using personal credentials.

### Create the Service Principal

```bash
az ad sp create-for-rbac \
  --name "github-actions-deployer" \
  --role contributor \
  --scopes "/subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-portfolio-assistant" \
  --sdk-auth
```

### Save the Output
The command outputs a JSON object. **Save this securely** - you'll need it for GitHub secrets:

```json
{
  "clientId": "<YOUR_CLIENT_ID>",
  "clientSecret": "<YOUR_CLIENT_SECRET>",
  "subscriptionId": "<YOUR_SUBSCRIPTION_ID>",
  "tenantId": "<YOUR_TENANT_ID>",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### Key Fields (write these down):
- **`clientId`**: Service Principal application ID
- **`clientSecret`**: Password for the service principal
- **`subscriptionId`**: Azure subscription ID
- **`tenantId`**: Azure AD tenant ID

---

## Step 4: Configure GitHub Secrets

### Why GitHub Secrets?
GitHub Secrets securely store credentials used by GitHub Actions workflows without exposing them in code or logs.

### Steps to Add Secrets

1. **Navigate to GitHub Repository**
   - Go to: https://github.com/Chuma-219181187/azure-portfolio-assistant
   - Click **Settings** (top-right)

2. **Open Secrets Management**
   - Left sidebar → **Secrets and variables** → **Actions**
   - Click **New repository secret** (green button)

3. **Add Each Secret** (6 total)

| # | Secret Name | Secret Value | Source |
|---|---|---|---|
| 1 | `AZURE_CREDENTIALS` | Entire JSON from Step 3 | Service Principal output |
| 2 | `AZURE_CONTAINER_REGISTRY_NAME` | `acrportfolio<RANDOM_NUMBER>` | ACR name from Step 2.4 |
| 3 | `AZURE_CLIENT_ID` | clientId from Step 3 | Service Principal |
| 4 | `AZURE_CLIENT_SECRET` | clientSecret from Step 3 | Service Principal |
| 5 | `RESOURCE_GROUP` | `rg-portfolio-assistant` | Fixed value |
| 6 | `AZURE_KEY_VAULT_NAME` | `portfolio-kv` | Fixed value |

### Verification
After adding all secrets, you should see 6 secrets listed:
- ✅ AZURE_CREDENTIALS
- ✅ AZURE_CONTAINER_REGISTRY_NAME
- ✅ AZURE_CLIENT_ID
- ✅ AZURE_CLIENT_SECRET
- ✅ RESOURCE_GROUP
- ✅ AZURE_KEY_VAULT_NAME

---

## Step 5: GitHub Actions Workflow

### Workflow File Location
`.github/workflows/deploy.yml`

### Workflow Configuration

**Key Elements:**

```yaml
name: Build and Deploy to Azure

on:
  push:
    branches: [ "main" ]  # Trigger on push to main
  workflow_dispatch:       # Manual trigger option

env:
  ACR_NAME: ${{ secrets.AZURE_CONTAINER_REGISTRY_NAME }}
  RESOURCE_GROUP: ${{ secrets.RESOURCE_GROUP }}
  CONTAINER_NAME: 'portfolio-assistant'
  KEY_VAULT_NAME: ${{ secrets.AZURE_KEY_VAULT_NAME }}
  LOCATION: 'centralindia'  # ← Allowed region

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest  # Build environment
    
    steps:
    - Checkout code
    - Azure Login (using service principal)
    - Log in to ACR (using credentials)
    - Build Docker image
    - Push image to ACR
    - Deploy to Azure Container Instances
```

### Workflow Steps Explained

1. **Checkout code** - Pulls latest code from GitHub
2. **Azure Login** - Authenticates with Azure using AZURE_CREDENTIALS secret
3. **Docker Registry Login** - Logs into ACR using AZURE_CLIENT_ID and AZURE_CLIENT_SECRET
4. **Build & Push** - Builds Docker image and pushes to ACR with:
   - Unique tag: Commit SHA (for traceability)
   - Latest tag: Always points to newest version
5. **Deploy to ACI** - Creates/updates container instance:
   - Pulls image from ACR
   - Exposes port 5000
   - Allocates 1 CPU, 1.5 GB memory
   - Sets restart policy to Always (high availability)

### Key Configuration Values

| Parameter | Value | Purpose |
|---|---|---|
| `LOCATION` | `centralindia` | Deployment region (must be allowed by policy) |
| `ports` | `5000` | Container port exposed to public |
| `cpu` | `1` | 1 CPU core allocated |
| `memory` | `1.5` | 1.5 GB RAM allocated |
| `restart-policy` | `Always` | Auto-restart on crash or node failure |

---

## Step 6: Register Required Azure Providers

### Why Register Providers?
Azure resource providers are backend services that enable specific resource types. They must be registered with your subscription before use.

### Register Providers

**Microsoft.ContainerRegistry (for ACR):**
```bash
az provider register --namespace Microsoft.ContainerRegistry --wait
```

**Microsoft.ContainerInstance (for ACI):**
```bash
az provider register --namespace Microsoft.ContainerInstance --wait
```

### Verify Registration
```bash
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState" -o tsv
az provider show --namespace Microsoft.ContainerInstance --query "registrationState" -o tsv
# Both should output: Registered
```

---

## Step 7: Trigger Deployment

### Method 1: Automatic (Push to Main)
Any push to the `main` branch automatically triggers the workflow:

```bash
git add .
git commit -m "trigger deployment"
git push origin main
```

### Method 2: Manual (Workflow Dispatch)
1. Go to **Actions** tab in GitHub repository
2. Click **Build and Deploy to Azure** workflow
3. Click **Run workflow** (green button)
4. Select **main** branch and confirm

### Method 3: GitHub CLI
```bash
gh workflow run deploy.yml --repo Chuma-219181187/azure-portfolio-assistant
```

### Monitor in Real-Time

**Via GitHub:**
1. Go to **Actions** tab
2. Click the latest workflow run
3. Click **build-and-deploy** job
4. Watch logs as workflow executes

**Via Azure CLI:**
```bash
# Check container instance status
az container list --resource-group rg-portfolio-assistant -o table

# Expected status when complete: Succeeded
```

---

## Verification & Monitoring

### Step 1: Verify Deployment Success

```bash
az container show \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant \
  -o json
```

**Key fields to check:**
- `instanceView.state` = `Running`
- `provisioningState` = `Succeeded`

### Step 2: Get Public IP Address

```bash
az container show \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant \
  --query "ipAddress.ip" -o tsv
```

### Step 3: Access Application

```
http://<PUBLIC_IP>:5000
```

Example: `http://20.219.177.35:5000`

### Step 4: View Application Logs

```bash
az container logs \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant
```

**Check for errors or startup messages**

### Step 5: Monitor Resource Usage

```bash
az container show \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant \
  --query "{CPU: containers[0].resources.requests.cpu, Memory: containers[0].resources.requests.memoryInGb, Status: instanceView.state}" \
  -o json
```

---

## Troubleshooting

### Problem 1: Workflow Fails - "username was required but not supplied"
**Cause**: GitHub secret not set or empty  
**Solution**: Verify all 6 secrets in GitHub Settings → Secrets

### Problem 2: Workflow Fails - "RequestDisallowedByAzure - region not allowed"
**Cause**: Deployment region not in allowed list  
**Solution**: Verify `LOCATION: 'centralindia'` in workflow file

**Check allowed regions:**
```bash
az rest --method get \
  --uri "/subscriptions/<SUBSCRIPTION_ID>/providers/Microsoft.Authorization/policyAssignments/sys.regionrestriction?api-version=2021-06-01" \
  --query "properties.parameters.listOfAllowedLocations.value" \
  -o json
```

### Problem 3: Workflow Fails - "Subscription is not registered to use namespace"
**Cause**: Azure provider not registered  
**Solution**: Register the required provider

```bash
az provider register --namespace Microsoft.ContainerInstance --wait
```

### Problem 4: Cannot Access Application
**Cause**: Container still starting, port mismatch, or firewall  
**Solution**: 

```bash
# Check container status
az container show \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant \
  --query "instanceView.state" -o tsv

# View logs for errors
az container logs \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant
```

### Problem 5: Application Crashes After Deployment
**Cause**: Missing environment variables, port mismatch, or dependency issue  
**Solution**: Check logs and verify Dockerfile

```bash
# Detailed logs with following
az container logs \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant \
  --follow
```

---

## Demo Talking Points

### 1. Problem Statement
- "We needed to deploy a containerized AI portfolio assistant to Azure"
- "Organization has regional restrictions on Azure subscriptions"
- "Local Docker installation was not available"

### 2. Solution Architecture
- **GitHub Actions**: CI/CD pipeline for automated build and deployment
- **Docker**: Containerized application (Python + Gunicorn)
- **Azure Container Registry**: Private image registry in centralindia
- **Azure Container Instances**: Serverless containers (pay per second)

### 3. Deployment Process
```
Code Push → GitHub Actions Builds Docker Image → 
Push to ACR → Deploy to ACI → Public Endpoint Live
```

### 4. Security Highlights
- Service principal with minimal permissions (resource group scope only)
- Secrets stored securely in GitHub (never in code/logs)
- ACR with admin authentication for image pulls

### 5. Cost Efficiency
- **Azure Container Instances**: Pay only for running seconds
- **Basic ACR**: Low cost for image storage
- **1 CPU / 1.5 GB RAM**: Sufficient for portfolio workloads
- **Auto-restart policy**: High availability without extra cost

### 6. Scalability Path
- Upgrade to Web App for automatic scaling
- Add Application Insights for monitoring
- Implement load balancing for multiple instances
- Add custom domain with Azure CDN

### 7. Live Demo (if applicable)
1. Show running application at public IP
2. Show GitHub Actions workflow execution
3. Show Azure resources in Portal
4. Make code change and push to trigger automatic deployment
5. Show updated application live

### 8. Monitoring & Reliability
```bash
# Show container status
az container show \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant

# Show recent logs
az container logs \
  --resource-group rg-portfolio-assistant \
  --name portfolio-assistant \
  --tail 20
```

---

## Quick Reference Commands

### Authentication
```bash
az login
az account show
az account list-subscriptions
```

### Resource Management
```bash
# List resources
az resource list --resource-group rg-portfolio-assistant -o table

# Delete resource group (caution: deletes all resources)
az group delete --name rg-portfolio-assistant --yes
```

### Container Management
```bash
# List containers
az container list --resource-group rg-portfolio-assistant -o table

# Start container
az container start --resource-group rg-portfolio-assistant --name portfolio-assistant

# Stop container
az container stop --resource-group rg-portfolio-assistant --name portfolio-assistant

# Restart container
az container restart --resource-group rg-portfolio-assistant --name portfolio-assistant

# Delete container
az container delete --resource-group rg-portfolio-assistant --name portfolio-assistant --yes
```

### ACR Management
```bash
# List repositories
az acr repository list --name acrportfolio<RANDOM_NUMBER>

# List image tags
az acr repository show-tags --name acrportfolio<RANDOM_NUMBER> --repository portfolio-assistant

# Get image details
az acr repository show --name acrportfolio<RANDOM_NUMBER> --image portfolio-assistant:latest
```

### Logs & Monitoring
```bash
# View container logs (real-time)
az container logs --resource-group rg-portfolio-assistant --name portfolio-assistant --follow

# Get container details
az container show --resource-group rg-portfolio-assistant --name portfolio-assistant

# Get public IP
az container show --resource-group rg-portfolio-assistant --name portfolio-assistant --query "ipAddress.ip" -o tsv

# Get FQDN
az container show --resource-group rg-portfolio-assistant --name portfolio-assistant --query "ipAddress.fqdn" -o tsv
```

---

## Application Details

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
ENV FLASK_APP=app.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

**Key Points:**
- Base: Python 3.11 slim (optimized)
- Port: 5000
- Server: Gunicorn (production WSGI)
- Framework: Flask

### Environment
- **Language**: Python 3.11
- **Framework**: Flask
- **Server**: Gunicorn
- **Port**: 5000
- **OS**: Linux (Debian-based)
- **CPU**: 1 vCPU
- **Memory**: 1.5 GB

---

## Success Metrics

✅ **Deployment Successful**
- Application URL: http://20.219.177.35:5000
- Status: Succeeded
- Region: centralindia
- Container: Running
- Uptime: 100% (with auto-restart)
- Auto-scaling: Available via Web App upgrade

---

## Support & Troubleshooting Resources

1. **Azure Portal**: Resource Group → Logs
2. **GitHub Actions**: Actions tab → Workflow runs
3. **Azure CLI**: Container logs and show commands
4. **Microsoft Docs**: aka.ms/azure-container-instances
5. **GitHub Actions Docs**: docs.github.com/actions

---

**Documentation Created**: November 21, 2025  
**Last Updated**: November 21, 2025  
**Status**: ✅ LIVE & OPERATIONAL
