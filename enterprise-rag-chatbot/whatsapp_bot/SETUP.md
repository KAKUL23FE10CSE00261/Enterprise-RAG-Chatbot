# WhatsApp Bot Setup Guide

## Quick Start (5 minutes)

### 1. Install dependencies
```bash
pip install twilio flask
```

### 2. Get free Twilio account
- Go to https://twilio.com → Sign up (no credit card for sandbox)
- Go to Messaging → Try it out → Send a WhatsApp message
- Note your Account SID and Auth Token

### 3. Set environment variables
```cmd
set TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxx
set TWILIO_AUTH_TOKEN=your_auth_token
set GROQ_API_KEY=gsk_your_groq_key
```

### 4. Run the bot
```cmd
python whatsapp_bot/bot.py
```

### 5. Expose locally with ngrok (free)
```cmd
ngrok http 5000
```
Copy the HTTPS URL shown (e.g. https://abc123.ngrok.io)

### 6. Configure Twilio Sandbox
1. In Twilio Console → Messaging → Sandbox Settings
2. Set "When a message comes in" = https://YOUR-NGROK-URL/whatsapp
3. Save

### 7. Connect your WhatsApp
- Open WhatsApp → message +1 415 523 8886
- Send: join <your-sandbox-word>
- You're connected!

## Test it
Send "hello" to the bot → you should get the welcome message.
Then ask: "What is the syllabus for Unit 1 DBMS?"

## For production deployment
- Deploy Flask app to Railway/Render (free tier)
- Use a permanent URL instead of ngrok
- Upgrade to Twilio paid plan for custom WhatsApp number
