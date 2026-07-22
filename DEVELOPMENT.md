# Pokémon Card Bot - Technical & LLM Developer Guide

This document provides system-level architecture specifications, data schema definitions, and implementation details for `pokemon-card-bot`. It is optimized for Large Language Models (LLMs) and developers to extend or debug the bot safely.

---

## 1. System Architecture

`pokemon-card-bot` is an asynchronous Telegram Bot built with `python-telegram-bot` (v20+).
- **Core Entry Point**: `main.py`
- **Configuration**: `config.py` (stores `bot_token` and `admin_id`)
- **Data Persistence**: JSON-based file storage:
  - `pokemons.json`: Catalog of all scraped card objects (`name`, `image` URL).
  - `sets.json`: Metadata array of card sets (`name`, `baseURL`, `length`, `scraped` boolean flag).

---

## 2. Core Workflows & Data Pipelines

### 2.1 Card Name Normalization (`normalize_name`)
- Strip special characters using regex `[^\w\s]`.
- Convert string to lowercase.
- Preserve and uppercase specific card suffixes such as `EX` and `GX` (e.g. `"Pikachu ex"` -> `"pikachu EX"`).

### 2.2 Fuzzy Search & Matching (`find_cards`)
- Queries are normalized via `normalize_name()`.
- Calculates similarity ratio using `difflib.SequenceMatcher(None, query, card_name).ratio()`.
- Sorts matching results by descending similarity score. Default threshold is `0.9`, but falls back dynamically if fewer results are found.

### 2.3 Web Scraping Engine (`scrape_set` / `parse_single_card`)
- Scrapes card data asynchronously using `aiohttp` and parses HTML via `BeautifulSoup4`.
- **Target URL Pattern**: `<baseURL><card_index_3_digits>.shtml` (e.g. `001.shtml`, `002.shtml`).
- Extracts HTML table element `td.foocard img` for card artwork URL (`https://www.serebii.net<path>`) and card title from `td.main` or `td.cardinfo`.

### 2.4 Telegram Bot Handlers & Inline Navigation
- **Message Handler**: Listens for text messages containing card queries. Returns an `InputMediaPhoto` with inline navigation keyboard buttons (`◀ Prev`, `Next ▶`).
- **Callback Query Handler**: `button_click` handles inline pagination (`prev_<index>`, `next_<index>`). Updates message media using `context.bot_data["user_searches"]` to store active pagination states per user.

---

## 3. Data Schemas

### `sets.json` Schema
```json
[
  {
    "name": "Genetic Apex",
    "baseURL": "https://www.serebii.net/tcgpocket/geneticapex/",
    "length": 226,
    "scraped": true
  }
]
```

### `pokemons.json` Schema
```json
[
  {
    "name": "Pikachu EX",
    "image": "https://www.serebii.net/tcgpocket/geneticapex/001.jpg"
  }
]
```

---

## 4. Developer & LLM Guidelines

1. **Maintain Asynchronous I/O**: Use `aiohttp` for network HTTP requests. Avoid synchronous blocking libraries (like `requests`) inside bot handlers.
2. **Handle Scraping Edge Cases**: HTML structures on Serebii may vary slightly between sets (e.g. Trainer cards vs Pokémon cards). Ensure `parse_single_card` gracefully handles missing `td` elements.
3. **State Management**: Active user search sessions are stored in `context.bot_data["user_searches"]` indexed by `user_id`. When extending pagination or search logic, ensure search history objects are maintained cleanly.
