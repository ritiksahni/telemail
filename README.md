# Telemail

## Why?

I made this Telegram chat-bot to have it summarize my emails every morning so that I wouldn't have to go through each one of them everyday.

Telemail takes the plain-text emails, creates an actionable item list for me and texts me on Telegram every morning.

**Note**: Telemail currently supports Gmail only.

## API Keys

Create an .env file with the following content. _Add your own API keys (obviously)_

```env
BOT_TOKEN="<TELEGRAM-BOT-TOKEN>"
OPENAI_API_KEY="<OPENAI-API-KEY>"
EMAIL_ADDRESS="<EMAIL-ADDRESS>"
EMAIL_PASSWORD="<EMAIL-PASSWORD>"
USER_ID="<TELEGRAM-USER-ID>"
```

---

**Note**:

Your regular Google password won't work with Telemail. You need to use an app password.

Instructions on creating an app password:
[https://support.google.com/mail/answer/185833?hl=en](https://support.google.com/mail/answer/185833?hl=en)

---
