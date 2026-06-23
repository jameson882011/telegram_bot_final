import asyncio
import time
import threading
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

# ---------- ТРЕЛЛО ----------
from trello import TrelloClient

# ---------- КОНФИГУРАЦИЯ ----------
BOT_TOKEN = "8885379423:AAGbn9nfZj-I4_nzC0mU9Aec0y23GGbzaLY"
ADMIN_ID = 5206473963
CHAT_ID = -1003978554378

# ---------- ТРЕЛЛО (ключи из переменных окружения Render) ----------
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
BOARD_ID = "6a39c84c8c9284ceffa8bed8"
LIST_ID_NEW = "6a39c84d8c9284ceffa8bf0b"

def add_card_to_trello(name, phone, address, work_type, area):
    try:
        client = TrelloClient(
            api_key=TRELLO_API_KEY,
            token=TRELLO_TOKEN
        )
        board = client.get_board(BOARD_ID)
        list_obj = board.get_list(LIST_ID_NEW)
        card = list_obj.add_card(
            name=f"Заявка от {name}",
            desc=f"Имя: {name}\nТелефон: {phone}\nАдрес: {address}\nВид работ: {work_type}\nОбъём: {area} м²"
        )
        print(f"✅ Карточка создана в Трелло: {card.id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании карточки в Трелло: {e}")
        return False

# ---------- ОСТАЛЬНОЙ КОД ----------
STATS_FILE = "stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"orders": 0, "messages": 0}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

stats = load_stats()

services = [
    {"name": "Покраска стен", "price": 500, "price_text": "от 500 ₽/м²", "photo": "https://i.imgur.com/your_painting.jpg", "desc": "Качественные краски, гарантия 5 лет."},
    {"name": "Штукатурка стен", "price": 800, "price_text": "от 800 ₽/м²", "photo": "https://i.imgur.com/your_plaster.jpg", "desc": "Идеально ровные стены под обои или покраску."},
    {"name": "Укладка плитки", "price": 1500, "price_text": "от 1500 ₽/м²", "photo": "https://i.imgur.com/your_tile.jpg", "desc": "Для ванных, кухонь, прихожих."},
    {"name": "Натяжные потолки", "price": 700, "price_text": "от 700 ₽/м²", "photo": "https://i.imgur.com/your_ceiling.jpg", "desc": "Матовые, глянцевые, тканевые."},
    {"name": "Устранение косяков", "price": 2000, "price_text": "от 2000 ₽/стену", "photo": "https://i.imgur.com/your_fix.jpg", "desc": "Убираем светотени, кривые углы, неровности."},
]

faq = {
    "светотень": "Светотени на стенах возникают из-за неравномерного нанесения краски или плохой подготовки. Обычно помогает перекраска с валиком с длинным ворсом.",
    "штукатурка": "Штукатурка должна сохнуть минимум 7 дней перед покраской.",
    "потолок": "Для потолка лучше использовать матовую краску – она скрывает неровности.",
    "плитка": "Для ванной используйте влагостойкий клей и затирку с антигрибковыми добавками.",
    "цена": "Цены зависят от объёма и состояния поверхностей. Напишите мне в личные сообщения.",
    "сроки": "Обычно отделка квартиры 50 м² занимает 2–3 недели.",
}

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Стоимость и услуги", callback_data="prices")],
        [InlineKeyboardButton("🧮 Рассчитать стоимость", callback_data="calculator")],
        [InlineKeyboardButton("📝 Записаться на замер", callback_data="order")],
        [InlineKeyboardButton("❓ Готовые ответы", callback_data="faq")],
        [InlineKeyboardButton("📸 Показать проблему на фото", callback_data="report")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Вернуться в меню", callback_data="back")]])

def get_service_keyboard(index):
    total = len(services)
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"svc_{index-1}"))
    if index < total - 1:
        buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"svc_{index+1}"))
    buttons.append(InlineKeyboardButton("🏠 В меню", callback_data="back"))
    return InlineKeyboardMarkup([buttons])

def get_calc_service_keyboard():
    buttons = []
    for i, service in enumerate(services):
        buttons.append([InlineKeyboardButton(f"{service['name']} ({service['price_text']})", callback_data=f"calc_{i}")])
    buttons.append([InlineKeyboardButton("⬅️ Вернуться в меню", callback_data="back")])
    return InlineKeyboardMarkup(buttons)

def get_work_type_keyboard():
    buttons = [
        [InlineKeyboardButton("🖌️ Малярные работы", callback_data="work_малярка")],
        [InlineKeyboardButton("🧱 Штукатурка", callback_data="work_штукатурка")],
        [InlineKeyboardButton("🛁 Укладка плитки", callback_data="work_плитка")],
        [InlineKeyboardButton("🌟 Натяжные потолки", callback_data="work_потолки")],
        [InlineKeyboardButton("🏠 Отделка под ключ", callback_data="work_под_ключ")],
        [InlineKeyboardButton("✏️ Свой вариант", callback_data="work_other")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_area_keyboard():
    buttons = [
        [InlineKeyboardButton("📏 до 20 м²", callback_data="area_до20")],
        [InlineKeyboardButton("📏 20–50 м²", callback_data="area_20-50")],
        [InlineKeyboardButton("📏 50–100 м²", callback_data="area_50-100")],
        [InlineKeyboardButton("📏 более 100 м²", callback_data="area_более100")],
        [InlineKeyboardButton("✏️ Свой вариант", callback_data="area_other")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_phone_code_keyboard():
    buttons = [
        [InlineKeyboardButton("🇷🇺 +7", callback_data="code_+7")],
        [InlineKeyboardButton("🇧🇾 +375", callback_data="code_+375")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Вернуться в меню", callback_data="cancel_order")]])

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник по отделке.\n"
        "Выберите, что вам нужно:",
        reply_markup=get_main_menu()
    )
    stats["messages"] += 1
    save_stats(stats)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_data = context.user_data

    if data == "calculator":
        await query.edit_message_text(
            "🧮 Рассчитаем примерную стоимость\n\n"
            "Выберите вид работ:",
            reply_markup=get_calc_service_keyboard()
        )
        return

    elif data.startswith("calc_"):
        index = int(data.split("_")[1])
        user_data["calc_service_index"] = index
        user_data["calc_step"] = "area"
        await query.edit_message_text(
            f"Вы выбрали: {services[index]['name']}\n"
            f"Стоимость: {services[index]['price_text']}\n\n"
            "Теперь напишите площадь в м²:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if data.startswith("work_"):
        work_type = data.split("_")[1]
        if work_type == "other":
            await query.edit_message_text(
                "Напишите свой вариант:",
                reply_markup=get_cancel_keyboard()
            )
            user_data["order_step"] = "work_type_custom"
        else:
            user_data["order_work_type"] = work_type
            user_data["order_step"] = "area"
            await query.edit_message_text(
                "Укажите объём работ:",
                reply_markup=get_area_keyboard()
            )
        return

    elif data.startswith("area_"):
        area = data.split("_")[1]
        if area == "other":
            await query.edit_message_text(
                "Напишите объём в м²:",
                reply_markup=get_cancel_keyboard()
            )
            user_data["order_step"] = "area_custom"
        else:
            user_data["order_area"] = area
            await finish_order(update, context, query)
        return

    elif data.startswith("code_"):
        code = data.split("_")[1]
        user_data["phone_code"] = code
        user_data["order_step"] = "phone"
        await query.edit_message_text(
            f"Теперь напишите номер (например, 9123456789):",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif data == "cancel_order":
        user_data.clear()
        await query.edit_message_text(
            "Возврат в главное меню.",
            reply_markup=get_main_menu()
        )
        return

    if data == "prices":
        index = 0
        user_data["service_index"] = index
        service = services[index]
        caption = f"💰 **{service['name']}**\nЦена: {service['price_text']}\n\n{service['desc']}"
        keyboard = get_service_keyboard(index)
        msg = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=service['photo'],
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        user_data["service_message_id"] = msg.message_id
        user_data["service_chat_id"] = update.effective_chat.id
        await query.delete_message()
        return

    elif data.startswith("svc_"):
        index = int(data.split("_")[1])
        user_data["service_index"] = index
        service = services[index]
        caption = f"💰 **{service['name']}**\nЦена: {service['price_text']}\n\n{service['desc']}"
        keyboard = get_service_keyboard(index)
        msg_id = user_data.get("service_message_id")
        chat_id = user_data.get("service_chat_id")
        if msg_id and chat_id:
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=msg_id,
                media=InputMediaPhoto(media=service['photo'], caption=caption, parse_mode="Markdown"),
                reply_markup=keyboard
            )
        else:
            msg = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=service['photo'],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            user_data["service_message_id"] = msg.message_id
            user_data["service_chat_id"] = update.effective_chat.id
        return

    elif data == "order":
        user_data["order_step"] = "name"
        await query.edit_message_text(
            "📝 Напишите ваше имя:",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif data == "faq":
        text = "❓ Готовые ответы:\n\n"
        for keyword, answer in faq.items():
            text += f"• {keyword.capitalize()} — {answer}\n\n"
        text += "Если не нашли ответ, просто напишите свой вопрос."
        await query.edit_message_text(text, reply_markup=get_back_menu())

    elif data == "report":
        await query.edit_message_text(
            "📸 Отправьте фото или видео проблемы, затем описание.",
            reply_markup=get_back_menu()
        )
        context.user_data["report_step"] = "waiting_media"

    elif data == "back":
        msg_id = user_data.get("service_message_id")
        chat_id = user_data.get("service_chat_id")
        if msg_id and chat_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение: {e}")
            user_data.pop("service_message_id", None)
            user_data.pop("service_chat_id", None)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Главное меню:",
            reply_markup=get_main_menu()
        )
        await query.delete_message()

async def finish_order(update, context, query=None):
    user_data = context.user_data
    name = user_data.get("order_name", "не указано")
    phone = user_data.get("order_phone", "не указано")
    address = user_data.get("order_address", "не указано")
    work_type = user_data.get("order_work_type", "не указано")
    area = user_data.get("order_area", "не указано")

    msg = (
        f"🔔 НОВАЯ ЗАЯВКА НА ЗАМЕР\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Адрес: {address}\n"
        f"Вид работ: {work_type}\n"
        f"Объём: {area} м²"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

    add_card_to_trello(name, phone, address, work_type, area)

    if query:
        await query.edit_message_text(
            "✅ Заявка принята! Мы свяжемся с вами.",
            reply_markup=get_main_menu()
        )
    else:
        await update.message.reply_text(
            "✅ Заявка принята! Мы свяжемся с вами.",
            reply_markup=get_main_menu()
        )

    stats["orders"] += 1
    save_stats(stats)
    user_data.clear()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    step = user_data.get("order_step")
    calc_step = user_data.get("calc_step")
    text = update.message.text

    if text.startswith('/'):
        return

    if calc_step == "area":
        try:
            area = float(text.replace(",", "."))
            if area <= 0:
                raise ValueError
            service_index = user_data.get("calc_service_index", 0)
            service = services[service_index]
            total = service["price"] * area
            await update.message.reply_text(
                f"🧮 Расчёт стоимости:\n\n"
                f"Услуга: {service['name']}\n"
                f"Площадь: {area} м²\n"
                f"Цена за м²: {service['price_text']}\n\n"
                f"💸 Примерная стоимость: {total:,.0f} ₽\n\n"
                "Точная стоимость после замера.",
                reply_markup=get_main_menu()
            )
            user_data.pop("calc_step", None)
            user_data.pop("calc_service_index", None)
            return
        except (ValueError, TypeError):
            await update.message.reply_text(
                "Введите число (например, 45):",
                reply_markup=get_cancel_keyboard()
            )
            return

    if step:
        if step == "name":
            user_data["order_name"] = text
            user_data["order_step"] = "phone_code"
            await update.message.reply_text(
                "Выберите код страны:",
                reply_markup=get_phone_code_keyboard()
            )
        elif step == "phone":
            phone_code = user_data.get("phone_code", "+7")
            full_phone = phone_code + text
            user_data["order_phone"] = full_phone
            user_data["order_step"] = "address"
            keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Отправить местоположение", request_location=True)]],
                resize_keyboard=True, one_time_keyboard=True
            )
            await update.message.reply_text(
                "Укажите адрес (геолокация или текст):",
                reply_markup=keyboard
            )
        elif step == "address":
            user_data["order_address"] = text
            user_data["order_step"] = "work_type"
            await update.message.reply_text(
                "Выберите вид работ:",
                reply_markup=get_work_type_keyboard()
            )
            await update.message.reply_text(
                "Выберите вид работ:",
                reply_markup=ReplyKeyboardRemove()
            )
        elif step == "work_type_custom":
            user_data["order_work_type"] = text
            user_data["order_step"] = "area"
            await update.message.reply_text(
                "Укажите объём работ:",
                reply_markup=get_area_keyboard()
            )
        elif step == "area_custom":
            user_data["order_area"] = text
            await finish_order(update, context)
        return

    if update.effective_chat.type == "private":
        if text:
            text_lower = text.lower()
            for keyword, answer in faq.items():
                if keyword in text_lower:
                    await update.message.reply_text(answer)
                    stats["messages"] += 1
                    save_stats(stats)
                    return

    if update.effective_chat.id == CHAT_ID:
        try:
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id
            )
            print("Сообщение переслано")
        except Exception as e:
            print(f"Ошибка пересылки: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if user_data.get("order_step") == "address":
        location = update.message.location
        maps_link = f"https://www.google.com/maps?q={location.latitude},{location.longitude}"
        user_data["order_address"] = maps_link
        user_data["order_step"] = "work_type"
        await update.message.reply_text(
            "📍 Местоположение получено. Выберите вид работ:",
            reply_markup=get_work_type_keyboard()
        )
        await update.message.reply_text(
            "Выберите вид работ:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text("Сейчас не нужно отправлять геолокацию.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        if context.user_data.get("report_step") == "waiting_media":
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
            elif update.message.video:
                file_id = update.message.video.file_id
            else:
                await update.message.reply_text("Отправьте фото или видео.")
                return
            context.user_data["media_file_id"] = file_id
            context.user_data["report_step"] = "waiting_description"
            await update.message.reply_text("Напишите описание проблемы:")
        else:
            await update.message.reply_text(
                "Нажмите «Показать проблему на фото» в меню.",
                reply_markup=get_main_menu()
            )

async def handle_report_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("report_step") == "waiting_description":
        description = update.message.text
        file_id = context.user_data.get("media_file_id")
        if file_id:
            caption = f"📸 Проблема от пользователя\nОписание: {description}"
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption)
            await update.message.reply_text("✅ Отчёт отправлен мастеру!", reply_markup=get_main_menu())
            stats["messages"] += 1
            save_stats(stats)
            context.user_data.clear()
        else:
            await update.message.reply_text("Ошибка. Попробуйте заново.")
            context.user_data.clear()

def main():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    app = Application.builder().token(BOT_TOKEN).connect_timeout(300).read_timeout(300).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("cancel", cancel_order))

    app.add_handler(CallbackQueryHandler(button_callback))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_description))

    print("Бот запущен и слушает сообщения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if "order_step" in user_data or "calc_step" in user_data:
        user_data.clear()
        await update.message.reply_text("Возврат в главное меню.", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("Нет активной операции.", reply_markup=get_main_menu())

if __name__ == "__main__":
    main()
