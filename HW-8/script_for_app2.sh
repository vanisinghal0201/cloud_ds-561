# Update and install necessary software packages
apt-get update
apt-get install -yq git python3-pip python3-venv

# Set the directory paths for the repository and HW-4
REPO_DIR="/opt/app"
HW4_DIR="$REPO_DIR/HW-4"

# Clone the source code repository if it doesn't exist
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/vanisinghal0201/cloud_ds-561.git $REPO_DIR
fi

# Create a Python virtual environment for hw-4
if [ ! -d "$HW4_DIR/env" ]; then
    python3 -m venv $HW4_DIR/env
    $HW4_DIR/env/bin/pip install --upgrade pip
    $HW4_DIR/env/bin/pip install -r $HW4_DIR/requirements.txt
fi

# Activate the Python environment for HW-4
if [ -d "$HW4_DIR/env" ]; then
    source $HW4_DIR/env/bin/activate
fi

# Start the country logger app in the background
$HW4_DIR/env/bin/python3 $HW4_DIR/logger-app-2.py &
