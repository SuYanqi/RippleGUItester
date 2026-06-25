#!/bin/bash
set -euxo pipefail

echo "=========================================="
echo "Setting up RippleGUItester environment..."
echo "=========================================="

python -m pip --version
python --version

echo ""
echo "📦 Installing Python dependencies..."
python -m pip install --user -r requirements.txt

echo ""
echo "📦 Installing RippleGUItester in editable mode..."
python -m pip install --user -e .

echo ""
echo "✅ Setup complete!"

# Start virtual display for GUI testing
echo ""
echo "🖥️  Setting up virtual display (Xvfb)..."
touch ~/.Xauthority
export DISPLAY=:99

# Function to start Xvfb if not running
start_xvfb_if_needed() {
    if ! pgrep -x "Xvfb" > /dev/null; then
        Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
        sleep 1
        echo "   ✅ Xvfb started on DISPLAY :99"
    else
        echo "   ✅ Xvfb already running"
    fi
}

# Start Xvfb now
start_xvfb_if_needed

# Add auto-start to shell profiles for persistence across restarts
if ! grep -q "# Auto-start Xvfb for RippleGUItester" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'

# Auto-start Xvfb for RippleGUItester
export DISPLAY=:99
if ! pgrep -x "Xvfb" > /dev/null 2>&1; then
    Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
fi
EOF
    echo "   ✅ Added Xvfb auto-start to ~/.bashrc"
fi

