# Pokémon Card Bot 🃏🤖

> A Telegram bot to search, inspect, and share Pokémon TCG Pocket cards with fuzzy matching.

`pokemon-card-bot` is an interactive Telegram bot built in Python. It allows users to search for cards from Pokémon TCG Pocket card sets, inspect card images and details, and browse set catalogs via inline pagination.

---

## ✨ Features

- **Card Search & Fuzzy Matching**: Find cards easily even if user queries contain typos or partial names (powered by `difflib.SequenceMatcher`).
- **Interactive Inline Pagination**: Navigate through search results smoothly using Telegram inline keyboard buttons.
- **Card Set Management & Web Scraping**: Scrapes card sets from Serebii.net and persists card datasets locally in `pokemons.json`.
- **Admin Commands**:
  - `/scrape`: Scrapes newly added or unscraped card sets.
  - `/sets`: Displays existing card sets and configuration status.
  - `/addset <name> <url> <length>`: Registers a new card set for scraping.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python >= 3.10
- A Telegram Bot Token from [@BotFather](https://telegram.me/BotFather)

### 2. Installation & Configuration

```bash
# Clone the repository
git clone https://github.com/Trifase/pokemon-card-bot.git
cd pokemon-card-bot

# Install required packages
pip install python-telegram-bot aiohttp beautifulsoup4
```

Create a `config.py` file in the root directory:

```python
bot_token = "YOUR_TELEGRAM_BOT_TOKEN"
admin_id = 123456789  # Your Telegram User ID
```

### 3. Running the Bot

```bash
python main.py
```

---

## 🛠️ Tech Stack

- **Language**: Python 3
- **Framework**: `python-telegram-bot` (Async)
- **Web Scraping & HTTP**: `aiohttp`, `BeautifulSoup4`
- **Data Persistence**: JSON (`pokemons.json`, `sets.json`)

---

## 🤖 AI / LLM Developer Documentation

For technical architecture details, web scraping specifications, data structures, and state management designed for AI agents and developers, please read:

👉 **[DEVELOPMENT.md](DEVELOPMENT.md)**
