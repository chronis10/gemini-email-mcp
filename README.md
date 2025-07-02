
# 📧 FastMCP Gmail Reader Server

Manage Gmail using a FastMCP API server for Gemini-CLI. Supports reading emails and creating drafts (reply or new).

## 🚀 Features

- Fetch recent emails with pagination
- Create reply drafts
- Create new email drafts

## 🔧 Setup

### Install Dependencies

```bash
pip install uv
cd gemini-email-mcp
uv venv
uv pip install
```

### Generate Google API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable **Gmail API**.
3. Go to **APIs & Services → Credentials**.
4. Click **“Create Credentials” → “OAuth client ID” → Application type: Desktop App**.
5. Download `credentials.json` and place it in the project folder.

### Gemini-CLI Configuration

```bash
cd ~/.gemini
nano settings.json
```

```json
"mcpServers": {
    "gmailReader": {
      "command": "uv",
      "args": ["run", "main.py"],
      "cwd": "<<full-path>>/gemini-email-mcp",
      "timeout": 20000
    }
}
```

