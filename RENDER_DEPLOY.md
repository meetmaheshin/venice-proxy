# Deploy Venice Proxy to Render.com

## Step-by-Step Deployment Guide

### 1. Create GitHub Repository (if you don't have one)
```bash
# Initialize git in your project folder
git init
git add .
git commit -m "Initial commit - Venice proxy"

# Create repo on GitHub and push
git remote add origin https://github.com/yourusername/venice-proxy.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render

1. **Go to [render.com](https://render.com) and sign up/login**

2. **Click "New +" → "Web Service"**

3. **Connect your GitHub repository:**
   - Choose "Connect a repository"
   - Select your venice-proxy repository

4. **Configure your service:**
   - **Name:** `venice-proxy` (or any name you prefer)
   - **Environment:** `Node`
   - **Region:** Choose closest to you
   - **Branch:** `main`
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`

5. **Set Environment Variables:**
   - Click "Advanced" 
   - Add environment variable:
     - **Key:** `VENICE_API_KEY`
     - **Value:** `wvOH0kYOVHG7Nqgjd3Ft4nagJztR30fsOLgg5W2TaN`

6. **Choose Plan:**
   - Select "Free" plan (perfect for testing)

7. **Click "Create Web Service"**

### 3. Get Your Live URL

After deployment (takes ~2-3 minutes), you'll get a URL like:
```
https://venice-proxy-abc123.onrender.com
```

### 4. Update VAPI Configuration

Use your new Render URL in VAPI:
```
https://your-app-name.onrender.com/api/v1/chat/completions
```

### 5. Test Your Deployment

```bash
curl -X POST https://your-app-name.onrender.com/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "venice-haiku-v1",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

## Benefits of Render Deployment

✅ **Free hosting** - No credit card required for free tier
✅ **Automatic deployments** - Redeploys when you push to GitHub
✅ **Custom domains** - Can add your own domain later
✅ **SSL certificates** - HTTPS included
✅ **Always online** - 24/7 availability
✅ **Logs & monitoring** - View logs and performance metrics

## Troubleshooting

- **Build fails:** Check that package.json has correct dependencies
- **Service won't start:** Verify start command is `npm start`
- **API key issues:** Double-check environment variable name and value
- **502 errors:** Check logs in Render dashboard

Your Venice proxy will be live at: `https://your-service-name.onrender.com`