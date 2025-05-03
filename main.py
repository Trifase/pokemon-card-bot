import json
import re
from difflib import SequenceMatcher

import aiohttp
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.ext.filters import MessageFilter

import config


async def normalize_name(name):
    """
    Normalizes a card name by removing special characters and converting to lowercase.
    Preserves important suffixes like 'EX'.
    """

    name_parts = name.split()

    special_suffixes = ["EX", "GX"]
    has_suffix = name_parts[-1].upper() in special_suffixes if name_parts else False

    if has_suffix:
        base_name = " ".join(name_parts[:-1])
        suffix = name_parts[-1]
    else:
        base_name = " ".join(name_parts)
        suffix = ""

    # Normalize the base name
    normalized = re.sub(r"[^\w\s]", "", base_name).lower().strip()

    # Reattach suffix if it exists
    if suffix:
        normalized = f"{normalized} {suffix.upper()}"

    return normalized


async def calculate_similarity(s1, s2):
    """
    Calculate similarity ratio between two strings.
    """
    return SequenceMatcher(None, s1, s2).ratio()


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
        image = pokemon.find("td", class_="foocard").find("img")["src"]
        try:
            info = pokemon.find("td", class_="main")
            info = info.get_text(strip=True)
            # Trainer for Celestial Guardians - we get the card name from the alt of the image
            if info == '':
                info = pokemon.find("img", class_="card", alt=True)
                if info:
                    info = info["alt"]
                    name_match = re.search(r"#(?:\d+)\s(.+)", info)
                    if name_match:
                        info = name_match.group(1)

        except AttributeError:
            info_td = pokemon.find("td", class_="cardinfo")
            info_table = info_td.find("table")
            all_trs = info_table.find_all("tr")
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


async def scrape_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = []
    await update.message.reply_text(f"Oh dammi cinque minuti e ti richiamo, ti faccio sapere io, sì, ciao, ciao, cinque min- sì, ciao. Senti facciamo dieci ok.")

    with open("sets.json", "r") as f:
        sets = json.load(f)

    with open("pokemons.json", "r") as pk:
        previous_cards = json.load(pk)

    for s in sets:
        if s["scraped"]:
            continue

        print(f"Scraping set {s}")
        cards.extend(await scrape_set(s))
        s["scraped"] = True

    previous_cards = context.bot_data["cards"]
    previous_cards.extend(cards)

    context.bot_data["cards"] = previous_cards

    with open("pokemons.json", "w") as f:
        json.dump(previous_cards, f)

    with open("sets.json", "w") as f:
        json.dump(sets, f)

    await update.message.reply_text(f"Scraped {len(cards)} cards; total cards: {len(previous_cards)}")


async def sets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.from_user.id == config.admin_id:
        await update.message.reply_text("Non sei autorizzato")
        return
    with open("sets.json", "r") as f:
        sets = json.load(f)
    resp = '<b>Sono presenti i seguenti set:</b>\n'
    for s in sets:
        # print("set", s)
        resp += f"Nome: {s['name']}\nURL: {s['baseURL']}\nLunghezza: {s['length']}\n\n"
        # s['scraped'] = False
    with open("sets.json", "w") as f:
        json.dump(sets, f)
    resp2 = 'Se vuoi aggiungerne uno, usa il comando /addset <nome> <url> <lunghezza>\nGli underscore nel nome verranno convertiti in spazi.'
    await update.message.reply_html(resp, disable_web_page_preview=True)
    await update.message.reply_text(resp2)

async def add_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.from_user.id == config.admin_id:
        await update.message.reply_text("Non sei autorizzato")
        return
    args = context.args
    if not args or len(args) != 3:
        await update.message.reply_text("Devi specificare nome, URL e lunghezza")
        return
    if not args[2].isdigit():
        await update.message.reply_text("La lunghezza deve essere un numero")
        return
    
    with open("sets.json", "r") as f:
        sets = json.load(f)
    name = args[0].replace('_', ' ')
    sets.append({"name": name, "baseURL": args[1], "length": int(args[2]), "scraped": False})
    with open("sets.json", "w") as f:
        json.dump(sets, f)
    await update.message.reply_text(f"Set aggiunto: {args[0]}, lunghezza: {args[2]}, URL: {args[1]}")
    
async def find_cards(cards, search_term, similarity_threshold=0.9):
    """
    Find cards based on a search term, using fuzzy matching.

    Args:
        cards (list): List of card dictionaries
        search_term (str): Term to search for
        similarity_threshold (float): Minimum similarity ratio to consider a match (0-1)

    Returns:
        list: List of matching card dictionaries
    """
    normalized_search = await normalize_name(search_term)
    matches = []

    for card in cards:
        normalized_card_name = await normalize_name(card["name"])

        # If searching for a card with a suffix (like "Venusaur EX"),
        # only match exact suffix
        # if ' ' in normalized_search and normalized_search.split()[-1].upper() in ['EX', 'GX', 'V', 'VMAX', 'VSTAR']:
        #     if normalized_card_name == normalized_search:
        #         matches.append(card)
        # else:
        # For regular searches, use fuzzy matching
        # If the card has a suffix, only compare against its base name
        card_base_name = normalized_card_name
        similarity = await calculate_similarity(normalized_search, card_base_name)
        # print(f"Comparing {normalized_search} with {card_base_name}: {similarity}")

        if similarity >= similarity_threshold:
            matches.append(card)

    return matches


async def make_buttons(cards, pokemon, user_id, index_n=0):
    keyboard = []
    keyboard.append(
        [InlineKeyboardButton(f"→ {i + 1} ←" if i == index_n else f"{i + 1}", callback_data=f"poke;;{pokemon};;{i};;{user_id}") for i in range(cards)]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


async def cambia_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query = update.callback_query

    argomenti = query.data
    # poke;;{pokemon};;{i};;{user_id}
    _, pokemon, index_n, user_id = argomenti.split(";;")
    # if user_id != str(query.from_user.id):
    #     await query.answer('Giù le mani', show_alert=True)
    #     return

    await query.answer()

    try:
        pokemons = context.bot_data.get("cards")
        if not pokemons:
            pokemons = await load_pokemons_data()
            context.bot_data["cards"] = pokemons

        cards = await find_cards(pokemons, pokemon)
        buttons = await make_buttons(len(cards), pokemon, update.effective_user.id, int(index_n))
        poster_url = cards[int(index_n)]["image"]

        await query.edit_message_media(media=InputMediaPhoto(poster_url), reply_markup=buttons)

    except Exception as e:
        pass
        # print("Exception:", e)


async def reply_with_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pokemon_names = re.findall(r"\[\[(.*?)\]\]", update.message.text)
    pokemons = context.bot_data.get("cards")
    if not pokemons:
        pokemons = await load_pokemons_data()
        context.bot_data["cards"] = pokemons
    # print(pokemon_names)

    found_cards = {}
    images = []
    pokemon_names = list(set([pokemon.lower() for pokemon in pokemon_names]))

    for pokemon in pokemon_names:
        cards_found = await find_cards(pokemons, pokemon)
        if cards_found:
            found_cards[pokemon] = cards_found
    effective_user_name = update.effective_user.first_name
    print(f"{effective_user_name} is searching for: {pokemon_names}")
    # for pokemon, cards in found_cards.items():
        # print(f"{pokemon}: {len(cards)}")
    for pokemon in found_cards:
        images.append(found_cards[pokemon][0]["image"])

    if len(found_cards) == 1:  # retrieved a single pokemon
        for pokemon, cards in found_cards.items():
            if len(cards) > 1:  # multiple cards
                # print("(Buttons)")
                buttons = await make_buttons(len(cards), pokemon, update.effective_user.id)
                await update.message.reply_photo(images[0], reply_markup=buttons)
            else:
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
    application.add_handler(CallbackQueryHandler(cambia_pokemon, pattern=r"^poke;;"))
    application.add_handler(CommandHandler("scrape", scrape_cards))
    application.add_handler(CommandHandler("reload", reload_cards))
    application.add_handler(CommandHandler("sets", sets))
    application.add_handler(CommandHandler(["add_set", "addset"], add_set))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
