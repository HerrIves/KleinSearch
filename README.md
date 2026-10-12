# 🔭 KleinSearch

A powerful, headless, profile-driven scraping engine and local dashboard for monitoring items on Kleinanzeigen (formerly eBay Kleinanzeigen).

[![Live Dashboard](https://img.shields.io/badge/GitHub_Pages-Live_Dashboard-success?logo=github)](https://herrives.github.io/KleinSearch/)
![KleinSearch Dashboard](https://img.shields.io/badge/UI-Interactive_Dashboard-0ea5e9)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
[![CI](https://github.com/HerrIves/KleinSearch/actions/workflows/ci.yml/badge.svg)](https://github.com/HerrIves/KleinSearch/actions/workflows/ci.yml)
![Playwright](https://img.shields.io/badge/Playwright-Headless-green)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed)
![License](https://img.shields.io/badge/License-MIT-gray)

## ✨ Features

- **Profile-Driven Engine:** Create multiple search profiles (e.g., "MacBook M1 32GB", "ThinkPad T14").
- **Quick Profile Tabs:** Switch between searches in 1 click using visual bookmark tabs with real-time counters.
- **Smart Filtering:** 
  - **Must-have** criteria (supports aliases via `|`, e.g., `m1 pro|m1 max`).
  - **Exclusion** keywords (globally or per-profile) to instantly filter out irrelevant or broken items.
  - **City & Radius Filtering:** Search within specific cities or postal codes (e.g., `Berlin`, `10115`, `Frankfurt am Main`) with configurable radius (`+5 km` to `+200 km`).
  - Custom price ranges (`Price from` / `Price to`).
- **Interactive UI Dashboard:** A fully local or hosted HTML/CSS/JS frontend to view, sort, and manage your findings.
- **Stealth & Headless:** Runs under the hood using Playwright in headless mode, maintaining persistent browser profiles to avoid bot detection.
- **Local Storage:** All your data remains private and stored in standard `.csv` files.
- **Smart Reevaluation:** Whenever you update your profile rules (like adding an exclusion word), the local database is automatically cleaned up.
- **Flexible Telegram Alerts:** Instant notifications for exact matches (`MATCH`) or partial matches with at least 1 criterion met (`PARTIAL`), with built-in deduplication.
- **Zero-Token Cloud Management:** Safely update search profiles from your phone via pre-filled GitHub Issues with strict repository owner validation.
- **Docker Ready:** 1-click deployment with `docker-compose` for 24/7 autonomous monitoring on a VPS or home server.

## 🚀 Quick Start (Local Desktop)

### 1. Clone the repository

```bash
git clone https://github.com/HerrIves/KleinSearch.git
cd KleinSearch
```

### 2. Run the App

The project comes with automated setup scripts that dynamically create a Python virtual environment, install dependencies, and launch the application.

**Windows:**
```cmd
run.bat
```

**macOS / Linux:**
```bash
./run.sh
```

### 3. Usage
When the application starts, it will automatically open `index.html` in your default browser.
- **Settings (⚙️):** Add profiles, search queries, exclusion rules, and price limits.
- **Start Scan (▶️):** Scrapes Kleinanzeigen for the newest listings according to your active profiles. 
- **Telegram Alerts (📩):** Enter your Bot Token and Chat ID in Settings to get instant notifications when deals appear.
- You can manage notes directly on the listings inside the UI.

---

## 🐳 Docker Deployment (24/7 Server Monitoring)

Run KleinSearch autonomously on a VPS, Synology NAS, Raspberry Pi, or home server:

### 1. Start with Docker Compose

```bash
docker compose up -d
```

### 2. Configure Scans and Telegram

The container mounts `./data` on the host machine. You can configure:
- **`data/config.json`**: Edit search profiles and exclusion rules directly (changes are automatically picked up on each scan cycle).
- **Scan Interval**: Set the environment variable `SCAN_INTERVAL_MINUTES` in `docker-compose.yml` (default is 60 minutes).
- **Dashboard & Results**: Findings are persisted in `data/listings.csv` and rendered to `data/index.html`.

### 3. View Realtime Logs

```bash
docker compose logs -f
```

---

## ☁️ Free Cloud Monitoring (GitHub Actions)

You can run KleinSearch **100% free in the cloud** using GitHub Actions, without keeping your computer on.

### 1. Fork the Repository
Click the **Fork** button at the top right of this page to create your own copy.

### 2. Add Your Telegram Secrets
In your forked repository:
1. Go to **Settings** ➔ **Secrets and variables** ➔ **Actions**.
2. Click **New repository secret** and add:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from [@BotFather](https://t.me/BotFather).
   - `TELEGRAM_CHAT_ID`: Your numerical Telegram user or group ID.

### 3. Enable Workflows
1. Click the **Actions** tab in your repository.
2. Click **"I understand my workflows, go ahead and enable them"**.
3. Under **Workflows** on the left, select **Scheduled Scan** and click **Run workflow** to test it immediately.
4. The scan will automatically execute every 3 hours (at minute 20 past the hour) in the background and send Telegram alerts whenever new listings appear.

### 4. Manage Your Search Queries
You can adjust what the cloud bot searches for in three easy ways:
- **Via Mobile Dashboard (GitHub Pages):** Open your live dashboard on your phone, edit profiles in Settings, and tap **`🚀 Apply via GitHub Issue`** (securely executed only by the repository owner).
- **Via Local Desktop Dashboard:** Launch `run.bat`, adjust your search profiles, and click **`☁️ Sync to GitHub`** in Settings.
- **Via GitHub Web:** Open `config.json` in your repository, click the ✏️ (Edit) icon, change your search terms, and commit.

### 5. Live Mobile Dashboard (GitHub Pages)
View your interactive listings dashboard from your phone or browser anytime:
1. In your repository, go to **Settings** ➔ **Pages**.
2. Under **Build and deployment** ➔ **Source**, select **GitHub Actions**.
3. After the next scheduled scan, your live dashboard will be published at:
   `https://<your-username>.github.io/KleinSearch/`

---

## 🛠️ Tech Stack
- **Backend:** Python (Asyncio, Playwright, BeautifulSoup)
- **Frontend:** Vanilla JS, CSS (Serverless local HTML architecture)
- **Deployment:** Docker & Docker Compose
- **Testing:** Pytest & Ruff

## 📝 License
This project is licensed under the MIT License.

## 🤖 Acknowledgments
Built collaboratively in a pair-programming session with an AI coding assistant. 🚀
