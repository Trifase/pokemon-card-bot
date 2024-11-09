import json
import re

import aiohttp
from bs4 import BeautifulSoup
from telegram import InputMediaPhoto, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.ext.filters import MessageFilter

import config


async def scrape_set(set):
    print(f"Scraping set {set['name']}: {set['length']}")
    cards = []
    base_url = set["baseURL"]
    for i in range(1, set["length"] + 1):
        url = base_url + f"{i:03d}.shtml"
        try:
            card_raw = await get_single_card_html(url)
            print(f"Scraped card {i}: {url}")
        except Exception as e:
            print(f"Failed to scrape card {i}: {e}")
            continue

        card_data = await parse_single_card(card_raw)
        # print(card_data)
        if card_data:
            cards.append(card_data)
    return cards


async def get_single_card_html(url):
    """
    Download a single carc webpage
    """

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
        ) as response:
            data = await response.text()

    return data


async def parse_single_card(data):
    """
    Parse the pokemon webpage and extract the pokemon name and image
    """
    soup = BeautifulSoup(data, "html.parser")
    pokemon = soup.find("table", class_="tcgtable")

    if pokemon:
        # print(pokemon.prettify())
        image = pokemon.find("td", class_="foocard").find("img")["src"]
        try:
            info = pokemon.find("td", class_="main").get_text(strip=True)
        except AttributeError:
            info_td = pokemon.find("td", class_="cardinfo")
            # print(info_td)
            info_table = info_td.find("table")
            # print(info_table)
            all_trs = info_table.find_all("tr")
            # print(all_trs)
            info = all_trs[1].get_text(strip=True)

        info = info.replace("Trainer", "").replace("Supporter", "")
        if info.endswith("ex") and info != "Pokedex":
            info = info.replace("ex", " EX")

        pk = {"name": info, "image": f"https://www.serebii.net{image}"}
        return pk
    return None


async def save_pokemon_data(pokemons):
    with open("pokemons.json", "w") as f:
        json.dump(pokemons, f)


async def load_pokemons_data():
    with open("pokemons.json", "r") as f:
        pokemons = json.load(f)
    return pokemons


async def get_pokemon_image(pokemon, pokemons):
    for pk in pokemons:
        if pokemon.lower().strip() in pk["name"].lower().strip():
            return pk["image"]
    return None


async def scrape_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = []
    await update.message.reply_text(f"Oh dammi cinque minuti e ti richiamo, ti faccio sapere io, sì, ciao, ciao, cinque min- sì, ciao.")
    with open("sets.json", "r") as f:
        sets = json.load(f)
    for s in sets:
        print(f"Scraping set {s}")
        cards.extend(await scrape_set(s))
        # print(cards)
    await save_pokemon_data(cards)
    context.bot_data["cards"] = cards
    await update.message.reply_text(f"Scraped all cards: {len(cards)}")


async def reply_with_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pokemon_names = re.findall(r"\[\[(.*?)\]\]", update.message.text)
    pokemons = context.bot_data.get("cards")
    if not pokemons:
        pokemons = await load_pokemons_data()
        context.bot_data["cards"] = pokemons
    # print(pokemon_names)
    images = []
    pokemon_names = list(set([pokemon.lower() for pokemon in pokemon_names]))
    print('Card names:', pokemon_names)
    for pokemon in pokemon_names:
        pokemon = pokemon.lower()
        # print('pokemon:', pokemon)
        image = await get_pokemon_image(pokemon, pokemons)
        if image:
            # print('image: ', image)
            images.append(image)
    if len(images) == 1:
        await update.message.reply_photo(images[0])
    elif len(images) > 1:
        media_group = [InputMediaPhoto(image) for image in images[:10]]
        await update.message.reply_media_group(media_group)

async def reload_cards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cards = await load_pokemons_data()
    context.bot_data["cards"] = cards
    await update.message.reply_text(f"Reloaded all cards: {len(cards)}")

async def post_init(app: Application) -> None:
    cards = await load_pokemons_data()
    app.bot_data["cards"] = cards
    print("Ready!\n")

class PokemonFilter(MessageFilter):
    def filter(self, message):
        matches = re.findall(r"\[\[(.*?)\]\]", message.text)
        if matches:
            return True
        return False
pokemon_filter = PokemonFilter()


def main():
    application = Application.builder().token(config.bot_token).post_init(post_init).build()

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & pokemon_filter, reply_with_pokemon))
    application.add_handler(CommandHandler("scrape", scrape_cards))
    application.add_handler(CommandHandler("reload", reload_cards))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
