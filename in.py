import logging
import requests
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = 'https://api.51gameapi.com/api/webapi/GetEmerdList'  # Your API URL
user_states = {}

# Initialize the Pyrogram client
api_id = 27570056  # Your API ID
api_hash = "47967c8dfa745b408346c9dbcdbc0aea"  # Your API Hash
bot_token = "7512906526:AAE_UkmnvsezLp_gVWrmOSpAUhS9x9DLeMU"  # Replace with your actual bot token

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def fetch_data() -> dict:
    request_data = {
        "typeId": 1,
        "language": 0,
        "random": "c5acbc8a25b24da1a9ddd084e17cb8b6",
        "signature": "667FC72C2C362975B4C56CACDE81540C",
        "timestamp": int(time.time()),
    }

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'Authorization': 'Bearer YOUR_API_TOKEN_HERE'  # Replace with your actual API token
    }

    try:
        response = requests.post(API_URL, headers=headers, json=request_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return {"error": str(e)}

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    welcome_message = (
        "<b>🎉 Welcome to the Prediction Bot! 🎉</b>\n\n"
        "<b>Simply send a number (0-9) to start receiving predictions. "
        "I'll automatically detect your last drawn number and give you predictions based on that. "
        "To begin, use the command: /predict <number>.</b>"
    )
    await message.reply_text(welcome_message)  # Removed parse_mode

@app.on_message(filters.command("predict"))
async def predict(client: Client, message: Message):
    if message.command and len(message.command) > 1 and message.command[1].isdigit():
        last_drawn_number = int(message.command[1])
        user_id = message.from_user.id

        if user_id not in user_states:
            user_states[user_id] = {'category': 'BIG', 'last_loss': False}

        if 0 <= last_drawn_number <= 9:
            api_data = await fetch_data()

            if "error" in api_data:
                await message.reply_text(f"<b>Error fetching data:</b> {api_data['error']}")  # Removed parse_mode
                return

            await generate_prediction(client, message, api_data, last_drawn_number, user_id)
        else:
            await message.reply_text("<b>Please provide a valid number between 0 and 9.</b>")  # Removed parse_mode
    else:
        await message.reply_text("<b>Usage:</b> /predict <number> (0-9)")  # Removed parse_mode

async def generate_prediction(client: Client, message: Message, data: dict, last_drawn_number: int, user_id: int):
    number_scores = [0] * 10
    drawn_history = [5, 8, 8, 9, 3]  # Example history

    for index, number in enumerate(drawn_history):
        if index < len(drawn_history) - 3:
            number_scores[number] += 1
        else:
            number_scores[number] -= 1

    number_scores[last_drawn_number] += 5

    frequency_data = next((item for item in data['data'] if item['typeName'] == "Frequency"), {})
    missing_data = next((item for item in data['data'] if item['typeName'] == "Missing"), {})

    for i in range(10):
        number_scores[i] += missing_data.get(f'number_{i}', 0) * 2
        number_scores[i] += (10 - frequency_data.get(f'number_{i}', 0))

    ranked_predictions = [{'number': i, 'score': score} for i, score in enumerate(number_scores) if score > 0]
    ranked_predictions.sort(key=lambda x: x['score'], reverse=True)
    top_predictions = ranked_predictions[:7]

    small_count = sum(1 for pred in top_predictions if 0 <= pred['number'] <= 4)
    big_count = sum(1 for pred in top_predictions if 5 <= pred['number'] <= 9)

    if user_states[user_id]['last_loss']:
        user_states[user_id]['category'] = 'SMALL' if user_states[user_id]['category'] == 'BIG' else 'BIG'
        user_states[user_id]['last_loss'] = False
    else:
        user_states[user_id]['category'] = 'BIG' if small_count > big_count else 'SMALL'

    category = user_states[user_id]['category']

    output = (
        f"<b>🎯 Prediction Based on Last Number {last_drawn_number}:</b>\n\n"
        f"<b>Top Predicted Numbers:</b>\n"
    )

    for index, pred in enumerate(top_predictions):
        size_label = 'Big' if pred['number'] >= 5 else 'Small'
        output += f"{index + 1}. <b>{pred['number']} ({size_label})</b>\n"

    output += f"\n<b>➡️ Prediction Bet on :</b> {category}"

    keyboard = [
        [InlineKeyboardButton("Win", callback_data=f"win_{user_id}"), InlineKeyboardButton("Change Pre🔁", callback_data=f"loss_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(output, reply_markup=reply_markup)  # Removed parse_mode

@app.on_callback_query()
async def button_handler(client: Client, query):
    user_id = int(query.data.split('_')[1])
    action = query.data.split('_')[0]

    if user_id not in user_states:
        user_states[user_id] = {'category': 'BIG', 'last_loss': False}

    if action == 'win':
        await query.answer("Win, Congratulations 🎉.")
    elif action == 'loss':
        user_states[user_id]['last_loss'] = True
        await query.answer("Next prediction will switch.")

if __name__ == '__main__':
    app.run()
