# 🔭 KleinSearch

A powerful, headless, profile-driven scraping engine and local dashboard for monitoring items on Kleinanzeigen (formerly eBay Kleinanzeigen).

![KleinSearch Dashboard](https://img.shields.io/badge/UI-Interactive_Dashboard-0ea5e9)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Playwright](https://img.shields.io/badge/Playwright-Headless-green)
![License](https://img.shields.io/badge/License-MIT-gray)

## ✨ Features

- **Profile-Driven Engine:** Create multiple search profiles (e.g., "MacBook M1 32GB", "ThinkPad T14").
- **Smart Filtering:** 
  - **Must-have** criteria (supports aliases via `|`, e.g., `m1 pro|m1 max`).
  - **Exclusion** keywords (globally or per-profile) to instantly filter out irrelevant or broken items.
  - Custom price ranges (`Price from` / `Price to`).
- **Interactive UI Dashboard:** A fully local HTML/CSS/JS frontend to view, sort, and manage your findings.
- **Stealth & Headless:** Runs under the hood using Playwright in headless mode, maintaining persistent browser profiles to avoid bot detection.
- **Local Storage:** All your data remains private and stored in standard `.csv` files.
- **Smart Reevaluation:** Whenever you update your profile rules (like adding an exclusion word), the local database is automatically cleaned up.

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/kleinanzeigen-scout.git
cd kleinanzeigen-scout
```

### 2. Run the App

The project comes with automated setup scripts that will dynamically create a Python virtual environment, install dependencies, and launch the application.

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
- You can manage notes directly on the listings inside the UI.

## 🛠️ Tech Stack
- **Backend:** Python (Asyncio, Playwright, BeautifulSoup)
- **Frontend:** Vanilla JS, CSS (Serverless local HTML architecture)
- **Testing:** Pytest

## 📝 License
This project is licensed under the MIT License.

## 🤖 Acknowledgments
Built collaboratively in a pair-programming session with an AI coding assistant. 🚀
