# Nexus Bot Control — Telegram group management + web dashboard

Python Telegram bot with SQLite storage and a dark web dashboard. Includes:
- `/id`, `/info`, `/ban`, `/unban`, `/mute`, `/unmute`
- Reply-to-user, numeric user ID, and previously-seen `@username` target lookup
- Manual join-request notifications to the owner with Approve/Decline buttons
- Text keyword filters that can delete matching group messages and send a response
- Sticker/media auto-replies: reply to a sticker, photo, video, GIF, document, audio, voice message, or video note with `/filter your reply text`
- Web dashboard login, user list, text/media filter management, stats, and audit log
- No Free/Premium plan system
- Random group couple picker with a 6-hour per-group cooldown; replying to a member with `/couple` creates a fresh pair
- Owner-set couple photo saved from Telegram using `/setcoupleimage`
- Premium-style `/start` welcome screen with Add to Group and Help buttons, plus `/ping` latency check
- Group word and puzzle games: `/hidden`, `/scramble`, `/anagram`, `/wordle`, `/hangman`, `/wordchain`, `/riddle`, `/emojiquiz`, `/mathquiz`, `/guessnumber`, `/fasttype`, `/truefalse`, `/trivia`; correct answers award 10 group points and 5 Aura; answers expire after 10 minutes
- Per-group total points and Aura scoring with `/points`, `/top`, and `/auratop` leaderboards
- Aura changes based on an embedded positive/negative English word list: positive words add 5 Aura, negative words subtract 5 Aura (per-message change capped at 50); Aura cannot fall below zero
- `/protect 1d` spends 500 total points and `/protect 2d` spends 1000 total points to protect Aura from losses for the chosen duration

## Important limitations
Telegram does not offer a universal method to resolve every `@username` to a user ID. Username commands work only after the bot has observed the user and saved the username, or when replying to their message. Numeric IDs are the most reliable. Usernames can change.
Media filters match the same Telegram media identity (`file_unique_id`) and reply with the saved text; they do not copy/re-send the original media. Text keyword filters and media auto-replies work in groups where Telegram delivers the messages to the bot. The bot must have admin rights to delete messages or moderate users.
Manual join requests are sent to the owner in a private message with Approve and Decline buttons. The bot must be an admin with permission to manage join requests, and the owner must have started the bot in private chat.
Couple picker chooses from members the bot has observed in that specific group; Telegram does not expose a complete group-member list to bots. The owner must set the couple photo by replying to a photo with `/setcoupleimage`. The 6-hour cooldown is per group and is persisted in SQLite; replying to a member with `/couple` intentionally bypasses the cooldown for a fresh pair. Puzzle rounds are in-memory (one active puzzle per group) and reset on bot restart.

This starter project uses polling and one web process. Use a persistent disk for SQLite in cloud hosting. Never commit `.env` or share your bot token.

## 1. Create bot and get IDs
1. Open Telegram and message `@BotFather`, use `/newbot`, and copy the token.
2. Get your numeric Telegram user ID from a trusted ID bot or your own bot's `/id` command after starting it.
3. Add your bot to the group and make it an admin with permissions to delete messages, ban users, restrict members, and manage join requests as needed.
4. For group keyword/media filters, disable privacy mode in BotFather if the bot must inspect ordinary group messages. Check Telegram's current privacy-mode behavior.

## 2. Run locally
Python 3.11+ recommended.
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` and set real `BOT_TOKEN`, numeric `OWNER_ID`, `WEB_SECRET`, and a strong `DASHBOARD_PASSWORD`.
Generate a secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Start:
```bash
python bot.py
```
Open `http://127.0.0.1:8080`. Keep the terminal open while using the bot.

## 3. Commands
- `/start`, `/help`, `/id`
- `/info @username` or reply to a message with `/info`
- `/ban @username`, `/ban 123456789`, or reply with `/ban`
- `/unban 123456789` or `/unban @knownusername`
- `/mute @knownusername 30` or reply to a user's message with `/mute 30` (minutes; default 60)
- `/unmute 123456789` or reply with `/unmute`
- `/filter spam This message was removed` — keyword filter
- Reply to a sticker/media message with `/filter I recognize this sticker` — save a media auto-reply
- `/filters` — list saved filters
- `/couple` — random couple every 6 hours per group; reply to a member with `/couple` for a fresh pair
- Reply to a photo with `/setcoupleimage` — save the couple image (owner only)
- `/hidden`, `/scramble`, `/anagram`, `/wordle`, `/hangman`, `/wordchain`, `/riddle`, `/emojiquiz`, `/mathquiz`, `/guessnumber`, `/fasttype`, `/truefalse`, `/trivia` — mini games; `/puzzlehelp` lists them
- `/ping` — bot response latency check
- `/points` — show your group total points, Aura, and shield status
- `/top` — top 10 group total-points leaderboard
- `/auratop` — top 10 group Aura leaderboard
- `/protect 1d` / `/protect 2d` — Aura shield for 1/2 days, costing 500/1000 total points
- `/start` — welcome screen with Add to Group and Help buttons

Moderation commands require the owner or a group admin. Filter management requires the configured bot owner. Dashboard login is separate and protected by a username/password.


## 4. Cloud deployment
Use a persistent-volume host that supports Docker and a persistent disk:
1. Push the project to a private Git repository. Do not include `.env` or the database file.
2. Create a Docker web service using `Dockerfile`.
3. Add environment variables from `.env.example`.
4. Attach a persistent disk mounted at `/data` and set `DB_PATH=/data/nexusbot.sqlite3` so the SQLite database survives redeploys.
5. Ensure only one instance runs polling; multiple replicas will compete for Telegram updates.
6. Use HTTPS for the dashboard. Restrict access at the hosting platform/firewall if possible.
7. Set strong unique dashboard credentials and rotate the bot token if it leaks.

`render.yaml` is a starting template. Confirm the host's current persistent-disk rules and pricing. Free tiers often sleep or lack persistent disks and are not suitable for reliable 24/7 bot polling.

## Security checklist
- Never commit `.env`, token, or database file.
- Keep dashboard password unique and long; use HTTPS.
- Limit access to the web dashboard via platform access controls/VPN where possible.
- Back up `nexusbot.sqlite3` securely.
- Before public production use, add rate limiting, CSRF protection, login throttling, and preferably network/IP restrictions.
- Only one bot polling process should run.
- Do not grant bot permissions it does not need.


## DM start requirement
Open the bot privately and press **Start** before using `/couple` or starting/answering group games. Each player must start the bot in DM once. The `/start` screen contains **Add Nexus Bot to Group**, **Help & All Commands**, and **Ping** buttons. `/help` lists all registered commands. Moderation and filters remain available in groups so they can protect the chat even when members have not started the bot privately.

## Deploying the Telegram bot on Vercel (webhook mode)

This project now includes `api/webhook.py` and `set_webhook.py` for Telegram webhook delivery. Vercel Functions are request-based; do **not** run `python bot.py` or long polling on Vercel.

1. Push the **contents of this folder** (including `api/`, `vercel.json`, `requirements.txt`, `bot.py`, and `db.py`) to a GitHub repository.
2. Import that repository in Vercel. Set the project Root Directory to the folder containing `bot.py` and `vercel.json` if the repository has a parent folder.
3. Add these Environment Variables in Vercel Project Settings → Environment Variables:
   - `BOT_TOKEN` — token from @BotFather
   - `OWNER_ID` — your numeric Telegram user ID
   - `WEB_SECRET` — long random value
   - `DASHBOARD_USER` — a dashboard username (e.g. `admin`)
   - `DASHBOARD_PASSWORD` — strong dashboard password
   - `TELEGRAM_WEBHOOK_SECRET` — random 16–256 character value using only letters, digits, `_` or `-`
   - `DB_PATH` — `/tmp/nexusbot.sqlite3` (temporary storage only)
4. Deploy the project and copy its HTTPS URL, e.g. `https://your-project.vercel.app`.
5. On your laptop, in this project folder, create `.env` from `.env.example`, fill in the same `BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`, install requirements, then run once:
   `python set_webhook.py https://your-project.vercel.app`
6. Visit `https://your-project.vercel.app/api/webhook` to confirm the endpoint responds, then test the bot in Telegram.

### Important limitations

- Vercel serverless functions are not an always-running worker. This webhook endpoint handles updates only when Telegram sends a request.
- **SQLite at `/tmp` is temporary and instance-local on Vercel.** Scores, filters, protection timers, and other bot data may disappear or diverge across cold starts/instances. This setup is suitable for a deployment trial, not reliable production data. For reliable persistence, migrate `db.py` to a managed PostgreSQL database and test the bot end-to-end.
- The Flask admin dashboard is not served by this webhook function. This deployment configuration is for Telegram updates; deploy a separate dashboard app if you need the admin UI on Vercel.
- After every code change, redeploy from Vercel. If you change the webhook secret, update the local `.env` and run `set_webhook.py` again.
