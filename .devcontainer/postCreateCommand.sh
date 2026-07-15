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
echo "📥 Downloading datasets..."

# Remove stale zip files and directories if they exist
[ -f "data.zip" ] && rm -f data.zip && echo "   🗑️  Removed stale data.zip"
[ -f "output.zip" ] && rm -f output.zip && echo "   🗑️  Removed stale output.zip"
[ -d "data" ] && rm -rf data && echo "   🗑️  Removed stale data/"
[ -d "output" ] && rm -rf output && echo "   🗑️  Removed stale output/"

wget -q https://github.com/SuYanqi/RippleGUItester/releases/download/data/data.zip
unzip -qo data.zip
rm -f data.zip
echo "   ✅ data/ downloaded and extracted"

wget -q https://github.com/SuYanqi/RippleGUItester/releases/download/data/output.zip
unzip -qo output.zip
rm -f output.zip
echo "   ✅ output/ downloaded and extracted"

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

