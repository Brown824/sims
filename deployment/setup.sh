#!/bin/bash
# SIMS Server Setup Script (Ubuntu 22.04)
# Run as root.

set -e

echo "======================================"
echo " SIMS Backend Deployment Setup"
echo "======================================"

# 1. Update and install prerequisites
echo "[+] Updating system packages..."
apt-get update && apt-get upgrade -y
apt-get install -y apt-transport-https ca-certificates curl software-properties-common ufw

# 2. Install Docker
echo "[+] Installing Docker..."
if ! command -v docker &> /dev/null
then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
else
    echo "Docker already installed."
fi

# 3. Setup firewall (UFW)
echo "[+] Configuring Firewall (UFW)..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw --force enable

# 4. Create App Directory and .env
echo "[+] Setting up app directory..."
mkdir -p /root/sims
cd /root/sims

if [ ! -f .env ]; then
    echo "Creating template .env file..."
    cat <<EOF > .env
VIRUSTOTAL_API_KEY=YOUR_KEY_HERE
MODEL_PATH=./sims_model.h5
API_PORT=8000
EOF
    echo "WARNING: Edit /root/sims/.env with your real API keys!"
fi

# 5. Pull and run image
# Wait for github actions to push the image, or you can run this manually:
# docker pull yourusername/sims-api:latest
# docker run -d --name sims-api -p 8000:8000 --restart always --env-file /root/sims/.env yourusername/sims-api:latest

echo "======================================"
echo " Setup complete!"
echo " Next steps:"
echo " 1. nano /root/sims/.env to set your API keys."
echo " 2. Let GitHub Actions deploy the image, or run docker pull manually."
echo " 3. Verify at http://<YOUR_SERVER_IP>:8000/docs"
echo "======================================"
