# Update and install necessary software packages
apt-get update
apt-get install -yq git python3-pip python3-venv nginx
pip3 install --upgrade pip

# Set the directory paths for the repository and HW-4
REPO_DIR="/opt/app"
HW4_DIR="$REPO_DIR/HW-4"

# Clone the source code repository if it doesn't exist
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/vanisinghal0201/cloud_ds-561.git $REPO_DIR
fi

# Create a Python virtual environment 
if [ ! -d "$HW4_DIR/env" ]; then
    python3 -m venv $HW4_DIR/env
    $HW4_DIR/env/bin/pip install --upgrade pip
    $HW4_DIR/env/bin/pip install -r $HW4_DIR/requirements.txt
fi

# Change the working directory to HW-4
cd $HW4_DIR

# Configure Nginx for the Flask app
NGINX_CONF="/etc/nginx/sites-available/flask_app"
if [ ! -f "$NGINX_CONF" ]; then
    cat > $NGINX_CONF <<EOL
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOL

    # Enable the Nginx configuration by creating a symlink
    ln -s $NGINX_CONF /etc/nginx/sites-enabled/
fi

# Remove the default Nginx configuration if it exists
if [ -e /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

# Restart Nginx to apply the configuration
systemctl restart nginx

# Check if Gunicorn is running for hw-4, and if not, start it as a daemon
if ! pgrep -f "gunicorn -b 0.0.0.0:8080 main:app"; then
    $HW4_DIR/env/bin/gunicorn -b 0.0.0.0:8080 main:app --daemon
fi
