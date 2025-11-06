# Venice AI Proxy Deployment Guide

## Option 1: Railway (Recommended - Free)

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Deploy:**
   ```bash
   railway deploy
   ```

4. **Set environment variables:**
   ```bash
   railway variables set VENICE_API_KEY=wvOH0kYOVHG7Nqgjd3Ft4nagJztR30fsOLgg5W2TaN
   railway variables set PORT=8080
   ```

5. **Get your URL:**
   ```bash
   railway status
   ```

## Option 2: Render (Free Tier)

1. Go to https://render.com
2. Connect your GitHub repository
3. Create a new Web Service
4. Set environment variables:
   - `VENICE_API_KEY`: wvOH0kYOVHG7Nqgjd3Ft4nagJztR30fsOLgg5W2TaN
   - `PORT`: 8080

## Option 3: Vercel (Free)

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   vercel
   ```

3. Set environment variables in Vercel dashboard

## Option 4: Heroku (Paid)

1. Install Heroku CLI
2. Create app:
   ```bash
   heroku create your-venice-proxy
   ```

3. Set environment variables:
   ```bash
   heroku config:set VENICE_API_KEY=wvOH0kYOVHG7Nqgjd3Ft4nagJztR30fsOLgg5W2TaN
   ```

4. Deploy:
   ```bash
   git push heroku main
   ```

## Option 5: DigitalOcean App Platform

1. Go to DigitalOcean Apps
2. Connect repository
3. Set environment variables
4. Deploy

## Usage

Once deployed, replace your ngrok URL in VAPI with your new deployed URL:
`https://your-app.railway.app/api/v1/chat/completions`