#!/bin/bash
# WARNING: VPN startup script - Can cause container to fail!

echo "Starting VPN connection..."

# Check if VPN config exists
if [ ! -f /app/vpn/config.ovpn ]; then
    echo "ERROR: VPN config not found at /app/vpn/config.ovpn"
    echo "Falling back to running without VPN..."
    exec uvicorn main:app --host 0.0.0.0 --port 3000
fi

# Start OpenVPN in background
openvpn --config /app/vpn/config.ovpn --daemon

# Wait for VPN connection
echo "Waiting for VPN to connect..."
sleep 10

# Check if VPN is connected
if ip addr show tun0 &> /dev/null; then
    echo "VPN connected successfully!"
    ip addr show tun0
else
    echo "WARNING: VPN not connected, continuing anyway..."
fi

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 3000
