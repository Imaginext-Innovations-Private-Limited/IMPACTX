#!/bin/bash

echo "======================================"
echo "   UNIVERSAL AI HONEYPOT ENGINE"
echo "          SSH ONLY MODE"
echo "======================================"

PROJECT_DIR="$HOME/universal-ai-honeypot"
COWRIE_DIR="$HOME/cowrie"

# Step 1: Start Cowrie
echo "[1/4] Starting Cowrie SSH..."

cd "$COWRIE_DIR" || exit 1
source cowrie-env/bin/activate

if ss -lnt | grep -q ':2222'; then
    echo "[RUNNING] Cowrie SSH already listening on port 2222."
else
    cowrie start || {
        echo "[ERROR] Cowrie startup failed."
        exit 1
    }
fi

# Step 2: Wait for SSH listener
for i in {1..15}; do
    if ss -lnt | grep -q ':2222'; then
        break
    fi
    sleep 1
done

if ! ss -lnt | grep -q ':2222'; then
    echo "[ERROR] Cowrie SSH is not listening on port 2222."
    exit 1
fi

# Step 3: Start SSH processing services
echo "[2/4] Starting SSH processing services..."

cd "$PROJECT_DIR" || exit 1
source venv/bin/activate

python run_honeypot.py start-ssh || exit 1

echo "[3/4] Verifying SSH services..."
python run_honeypot.py status

echo "[4/4] Startup completed."

echo "======================================"
echo "SSH Honeypot: 192.168.47.130:2222"
echo "Dashboard: http://192.168.47.130:5000/dashboard"
echo "======================================"
