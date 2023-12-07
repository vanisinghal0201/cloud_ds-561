# Update and install necessary software packages
apt-get update
apt-get install -yq git python3-pip python3-venv

# Set the directory paths for the repository and HW-4
REPO_DIR="/opt/app2"
HW5_DIR="$REPO_DIR/HW-5"

# Clone the source code repository if it doesn't exist
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/vanisinghal0201/cloud_ds-561.git $REPO_DIR
fi

# Create a Python virtual environment for hw-4
if [ ! -d "$HW5_DIR/env" ]; then
    python3 -m venv $HW5_DIR/env
    $HW5_DIR/env/bin/pip install --upgrade pip
    $HW5_DIR/env/bin/pip install -r $HW5_DIR/requirements.txt
fi

# Activate the Python environment for HW-4
if [ -d "$HW5_DIR/env" ]; then
    source $HW5_DIR/env/bin/activate
fi

# Start the country logger app in the background
$HW5_DIR/env/bin/python3 $HW5_DIR/logger-app-2.py &
