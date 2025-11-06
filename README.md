# Venice AI Proxy

A proxy server that connects Venice.ai to VAPI for voice AI applications.

## Features

- Venice.ai API integration
- OpenAI-compatible endpoint
- Response sanitization (removes `<think>` blocks)
- Streaming and non-streaming support
- VAPI integration ready

## Quick Deploy

### Railway (Recommended)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template)

### Manual Deployment

1. Clone this repository
2. Install dependencies: `npm install`
3. Set environment variable: `VENICE_API_KEY=your_key_here`
4. Deploy to your preferred platform

## Environment Variables

- `VENICE_API_KEY`: Your Venice.ai API key
- `PORT`: Server port (default: 8080)

## Usage

Once deployed, use your app URL as the OpenAI endpoint in VAPI:
```
https://your-app.railway.app/api/v1/chat/completions
```

## Local Development

```bash
npm install
export VENICE_API_KEY=your_key_here
npm start
```

## Endpoints

- `POST /api/v1/chat/completions` - Main chat endpoint (OpenAI compatible)