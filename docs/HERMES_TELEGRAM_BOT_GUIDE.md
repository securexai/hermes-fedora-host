# Hermes Telegram Bot Configuration Guide

This guide describes how to configure, secure, and update the Telegram bot token
for the Hermes Agent appliance running on Fedora Server 44.

## Overview

Hermes Agent connects to Telegram via a persistent gateway service running in a
rootless Podman container under the `hermes` user. All environment variables and
persistent data reside on the host at `/home/hermes/data/` (mounted into the
container at `/opt/data`).

## Credentials and Security Architecture

Telegram integration requires two environment variables:

| Variable | Description | Example |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot API token issued by `@BotFather` | `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ` |
| `TELEGRAM_ALLOWED_USERS` | Comma-separated list of authorized numeric Telegram user IDs | `123456789,987654321` |

> [!CAUTION]
> Always define `TELEGRAM_ALLOWED_USERS`. Without this restriction, any Telegram
> user who discovers your bot can execute queries and consume inference credits.

### 1. Obtain Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to create your bot.
3. Save the token provided (do not wrap in quotes when adding to `.env`).
4. *(Optional for group chats)*: If you want the bot to read messages in groups,
   send `/setprivacy` to `@BotFather` and set it to **Disabled**.

### 2. Obtain Your Numeric User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram.
2. Note the numeric `Id` returned (e.g., `123456789`).

---

## Updating the Token on the Hermes Host

Because Hermes runs rootless under container sub-UID mapping, data files in
`/home/hermes/data/` are owned by container sub-UIDs. Standard user access
requires `sudo` privileges.

### Step 1: Connect via SSH

Connect to the management IP (`10.0.30.10`) as the `aicowork` operator:

```bash
ssh aicowork@10.0.30.10
```

### Step 2: Edit `/home/hermes/data/.env`

Open the environment file as root using `sudo`:

```bash
sudo vi /home/hermes/data/.env
```

Add or update the Telegram configuration keys:

```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_ALLOWED_USERS=123456789
```

> [!NOTE]
> Do not wrap `TELEGRAM_BOT_TOKEN` in quotation marks. Some parsers fail on colons
> if quotes are present.

Save and exit in `vi` by pressing `Esc`, typing `:wq`, and pressing `Enter`.

### Step 3: Ensure Read Permissions

Set the permissions so the rootless container process can read the updated file:

```bash
sudo chmod 0644 /home/hermes/data/.env
```

### Step 4: Restart the Hermes Service

Restart the user systemd service to reload the updated `.env`:

```bash
sudo systemctl --machine=hermes@.host --user restart hermes.service
```

---

## Verification & Troubleshooting

### Check Service Health and Status

```bash
sudo hermes-status
```

### Stream Live Gateway Logs

```bash
sudo hermes-logs
```

Look for successful Telegram initialization lines in the logs.

### Troubleshooting Checklist

| Symptom | Cause | Resolution |
| --- | --- | --- |
| `E212: Can't open file for writing` or `[Permission Denied]` | Opened with relative path `~/data` or without `sudo` | Use `sudo vi /home/hermes/data/.env` |
| Bot responds with `"Unauthorized"` | Telegram user ID is missing from `TELEGRAM_ALLOWED_USERS` | Verify user ID via `@userinfobot` and add to `.env` |
| Bot does not reply in groups | Telegram Privacy Mode is enabled | Run `/setprivacy` in `@BotFather` and set to **Disabled** |
| Gateway crash on startup | Syntax error or invalid token in `.env` | Verify `.env` formatting and inspect `sudo hermes-logs` |
