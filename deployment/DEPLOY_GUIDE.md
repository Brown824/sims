# SIMS Deployment Guide

This guide covers deploying the backend API to Oracle Cloud Free Tier and building the Android APK for production.

## 1. Oracle Cloud Setup

1. Sign up for Oracle Cloud Free Tier (https://www.oracle.com/cloud/free/).
2. Go to **Compute Instances** -> **Create Instance**.
3. Choose **Canonical Ubuntu 22.04** image.
4. Select the "Always Free" Ampere A1 (ARM) or VM.Standard.E2.1.Micro (AMD/Intel) shape.
5. Save the generated SSH Private Key (`.key` file) to your computer.
6. Create the instance. Note the **Public IP Address**.
7. In the instance settings, go to **Subnet** -> **Default Security List**. Add an Ingress Rule allowing TCP port `8000` from `0.0.0.0/0`.

## 2. Server Configuration

1. SSH into the server:
   ```bash
   ssh -i your_private_key.key ubuntu@YOUR_PUBLIC_IP
   ```
2. Switch to root and run the setup script:
   ```bash
   sudo su
   curl -O https://raw.githubusercontent.com/YOUR_GITHUB/sims/main/deployment/setup.sh
   chmod +x setup.sh
   ./setup.sh
   ```
3. Edit the `.env` file with your real keys:
   ```bash
   nano /root/sims/.env
   # Add your VirusTotal API key.
   ```

## 3. GitHub Actions CI/CD

To enable automated deployment on `git push`:
1. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Add the following repository secrets:
   - `DOCKERHUB_USERNAME`: your Docker Hub username
   - `DOCKERHUB_TOKEN`: your Docker Hub access token
   - `SERVER_HOST`: your Oracle Cloud Public IP
   - `SERVER_USER`: `root` or `ubuntu`
   - `SERVER_SSH_KEY`: the raw content of your `.key` file

## 4. Mobile App Configuration & Build

1. Open `mobile-app/src/services/api.js`.
2. Change `BASE_URL` to your Oracle Cloud IP:
   ```javascript
   const BASE_URL = 'http://YOUR_PUBLIC_IP:8000';
   ```
3. Build the Android APK using Expo Application Services (EAS):
   ```bash
   cd mobile-app
   npm install -g eas-cli
   eas login
   eas build --platform android --profile preview
   ```
4. Download the generated `.apk` and install it on your Android device.

## 5. Defense Day Verification

To verify everything is working during your academic defense:
1. Show the API Docs: `http://YOUR_PUBLIC_IP:8000/docs`
2. Show the Health Endpoint: `http://YOUR_PUBLIC_IP:8000/health`
3. Send a test SMS to the Android device and show the real-time classification on the app dashboard.
