# OpenAI API Key Setup

## Local Development

The OpenAI API key has been added to your `.env` file in the `config/` directory.

**Important:** The `.env` file is already in `.gitignore` and will NOT be committed to GitHub.

## Server Deployment

To set up the OpenAI API key on your server:

### Option 1: Add to .env file (Recommended)

1. SSH into your server:
```bash
ssh user@your-server-ip
```

2. Navigate to your project:
```bash
cd /var/www/solvey-admin/config
```

3. Add the API key to .env file (replace `YOUR_OPENAI_API_KEY` with your real key):
```bash
echo "OPENAI_API_KEY=YOUR_OPENAI_API_KEY" >> .env
```

4. Restart your application:
```bash
sudo systemctl restart gunicorn
```

### Option 2: Set as Environment Variable

```bash
export OPENAI_API_KEY='YOUR_OPENAI_API_KEY'
```

For permanent setup, add it to your systemd service file or shell profile.

## Verification

After setup, the AI chat assistant should work. Test it by:
1. Clicking the AI chat button in the sidebar
2. Sending a message
3. You should receive an AI response

## Security Notes

- ✅ API key is stored in `.env` file (not in code)
- ✅ `.env` is in `.gitignore` (won't be committed)
- ✅ Settings read from environment variables
- ⚠️ Keep your API key secure and don't share it publicly

## Troubleshooting

If the AI chat doesn't work:
1. Check if `.env` file exists and contains `OPENAI_API_KEY`
2. Verify the API key is correct
3. Check server logs: `sudo journalctl -u gunicorn -f`
4. Restart the application: `sudo systemctl restart gunicorn`

