# ngrok Setup for Dental ASR Frontend Development

## Overview
ngrok creates a secure tunnel from the internet to your local Python backend, allowing Lovable's cloud-hosted frontend to connect to your local development server.

## 🎉 PAID Personal Account Active
- **Custom Domain**: `dental-asr.ngrok.app` (permanent)
- **Auth Token**: `31gBfDb1SMPpCuDCdlXkbXefU8N_4Ltj6JoieJioj1rr4cB29`
- **Benefits**: Higher bandwidth for audio files, no timeouts, permanent URL

## Installation

### macOS
```bash
# Using Homebrew (recommended)
brew install ngrok

# Or download from website
# https://ngrok.com/download
```

### Windows
```powershell
# Option 1: Download from https://ngrok.com/download
# Extract ngrok.exe to C:\ngrok\

# Option 2: Using Chocolatey
choco install ngrok

# Option 3: Using Scoop
scoop install ngrok
```

### Linux
```bash
# Download and extract
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

## Configuration

### Add Authentication Token
```bash
# Configure your auth token (required for full features)
ngrok config add-authtoken 31gBfDb1SMPpCuDCdlXkbXefU8N_4Ltj6JoieJioj1rr4cB29
```

This token is saved to `~/.ngrok2/ngrok.yml` (Mac/Linux) or `%USERPROFILE%\.ngrok2\ngrok.yml` (Windows)

## Usage

### Step 1: Start Your Python Backend
```bash
# Navigate to project directory
cd /Users/janwillemvaartjes/projects/pairing_server

# Start the NEW unified server
python3 -m app.main

# Server will run on http://localhost:8089
```

### Step 2: Start ngrok Tunnel
```bash
# With PAID Personal Account - use custom domain
ngrok http 8089 --domain=dental-asr.ngrok.app

# You'll see output like:
# Session Status                online
# Account                       your-email@example.com (Personal)
# Version                       3.5.0
# Region                        United States (us)
# Web Interface                 http://127.0.0.1:4040
# Forwarding                    https://dental-asr.ngrok.app -> http://localhost:8089
```

### Step 3: Update Lovable Frontend

With the PAID Personal Account, use the permanent custom domain:

```javascript
// PERMANENT URLs - never change!
const API_BASE_URL = 'https://dental-asr.ngrok.app';
const WS_URL = 'wss://dental-asr.ngrok.app/ws';

// Example API call:
fetch(`${API_BASE_URL}/api/lexicon/categories`)
  .then(res => res.json())
  .then(data => console.log('Categories:', data));

// WebSocket connection:
const ws = new WebSocket(WS_URL);
```

## Features with Auth Token

With the auth token configured, you get:
- Longer session times (tunnels don't timeout)
- Custom subdomains (with paid plan)
- Multiple simultaneous tunnels
- Reserved domains (with paid plan)
- IP whitelisting options

## Monitoring

### ngrok Web Interface
While ngrok is running, visit http://localhost:4040 to see:
- All HTTP requests/responses
- Request timing and latency
- Request/response headers and bodies
- Replay requests for debugging

### Check Connection
Test the tunnel from any browser:
```javascript
// Visit your ngrok URL in browser or run in console:
fetch('https://your-ngrok-url.ngrok-free.app/api/lexicon/categories')
  .then(res => res.json())
  .then(data => console.log('✅ Connected!', data))
  .catch(err => console.error('❌ Error:', err));
```

## Common Issues

### "Tunnel not found" Error
- Make sure ngrok is running (`ngrok http 3001`)
- Check the Python server is running on port 3001
- Verify the ngrok URL is correct (it changes each session unless you have a paid plan)

### CORS Errors
- Your Python backend already has CORS configured for all origins
- If issues persist, check you're using HTTPS URL from ngrok, not HTTP

### WebSocket Connection Failed
- Use `wss://` protocol for WebSocket, not `ws://`
- Example: `wss://abc123.ngrok-free.app/ws`

### "Too Many Connections" Error
- Free tier has connection limits
- Close unused browser tabs
- Restart ngrok if needed

## Security Notes

1. **Development Only** - ngrok tunnels are for development, not production
2. **URL is Public** - Anyone with the URL can access your local server
3. **Temporary URLs** - Free tier URLs change each session
4. **Auth Token** - Keep your auth token private (though this one is already in docs)

## Tips

1. **Persistent URL**: Sign up at ngrok.com for a free account to get more stable URLs
2. **Multiple Tunnels**: Can run multiple tunnels on different ports
3. **Custom Domains**: Paid plans allow custom domains
4. **Basic Auth**: Can add password protection: `ngrok http 3001 --basic-auth="user:password"`

## Alternative for Production

For production, consider:
- Deploy Python backend to cloud (AWS, Google Cloud, Azure)
- Use proper domain with SSL certificate
- Set up proper authentication and security

## Quick Reference

```bash
# Complete setup flow (PAID Personal Account):
brew install ngrok                                                    # Install
ngrok config add-authtoken 31gBfDb1SMPpCuDCdlXkbXefU8N_4Ltj6JoieJioj1rr4cB29  # Configure
cd /Users/janwillemvaartjes/projects/pairing_server                   # Navigate to project
python3 -m app.main                                                   # Start NEW unified backend
ngrok http 8089 --domain=dental-asr.ngrok.app                        # Start tunnel with custom domain
# Frontend always uses: https://dental-asr.ngrok.app
```

## Documentation
- Official docs: https://ngrok.com/docs/agent/
- API reference: https://ngrok.com/docs/api/
- Troubleshooting: https://ngrok.com/docs/guides/