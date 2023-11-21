import logging
from datetime import datetime

from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

from model import Poll, User
from repository import PollRepository, UserRepository

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

MENU, CREATE_POLL, POLL_DOW, POLL_TIME, POLL_DURATION, LIST_POLL, DELETE_POLL = range(7)
TOKEN = "Вставьте ваш токен"
poll_repo, user_repo = PollRepository(), UserRepository()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало"""
    user = update.message.from_user
    reply_keyboard = [["Создать опрос", "Удалить опрос", "Cтатистика"]]
    logger.info("Пользователь %s запустил бота.", user.first_name)
    await update.message.reply_text(
        "Привет. Этот бот поможет тебе создавать регулярные опросы",
    )
    await update.message.reply_text(
        "Пожалуйста выбери действие на клавиатуре ниже",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Мены",
            resize_keyboard=True,
        ),
    )
    return MENU


async def new_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Создание опроса"""
    user = update.message.from_user
    logger.info("Пользователь %s создает опрос.", user.first_name)
    await update.message.reply_text(
        "Пожалуйста отправьте опрос который хотите сделать периодическим",
        reply_markup=ReplyKeyboardRemove(),
    )
    return CREATE_POLL


async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение опроса"""
    user = update.message.from_user
    context.user_data["question"] = update.message.poll.question
    context.user_data["options"] = ",".join(
        [option["text"] for option in update.message.poll.options],
    )
    logger.info(
        """Пользователь %s отправил опрос.
           Вопрос: %s,
           Доступные опции: %s""",
        user.first_name,
        update.message.poll.question,
        [option["text"] for option in update.message.poll.options],
    )
    await update.message.reply_text("Укажите дни недели публикации опроса")
    await update.message.reply_text("Например: ПН,СР,ПТ")
    return POLL_DOW


async def poll_dow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение дней недели опроса"""
    user = update.message.from_user
    context.user_data["dows"] = update.message.text
    logger.info("Пользователь %s установил день недели.", user.first_name)
    await update.message.reply_text("Укажите время публикации опроса")
    await update.message.reply_text("Например: 12:30")
    return POLL_TIME


async def poll_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени опроса"""
    user = update.message.from_user
    context.user_data["start_time"] = update.message.text
    logger.info("Пользователь %s установил время начала опроса.", user.first_name)
    await update.message.reply_text("Укажите время закрытия опроса")
    await update.message.reply_text("Например: 15:00")
    return POLL_DURATION


async def poll_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение продолжительности опроса"""
    user = update.message.from_user
    context.user_data["end_time"] = update.message.text
    context.user_data["chat_id"] = update.message.chat_id
    logger.info("Пользователь %s установил время закрытия опроса.", user.first_name)
    logger.info("Создан опрос %s", context.user_data)
    poll_repo.add(Poll(**context.user_data))
    await update.message.reply_text("Опрос успешно создан")
    return ConversationHandler.END


async def list_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление опроса"""
    logger.info("Этот метод еще не готов")
    polls = list(poll_repo.get(update.message.chat_id))
    if polls:
        reply_keyboard = [[str(poll.id) for poll in polls]]
        await update.message.reply_text(
            "\n".join([f"{poll.id}: {poll.question}" for poll in polls]),
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                input_field_placeholder="Опросы",
                resize_keyboard=True,
            ),
        )
        return DELETE_POLL
    await update.message.reply_text(
        "У вас нет опросов",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def delete_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление опроса"""
    logger.info("Этот метод еще не готов")
    poll_repo.delete(int(update.message.text))
    await update.message.reply_text(
        "Опрос удален",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выход из контекста"""
    user = update.message.from_user
    logger.info("Пользователь %s закрыл контекст.", user.first_name)
    await update.message.reply_text(
        "Контекст закрыт.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rez = {}
    rez["user_id"] = update.poll_answer.user.id
    rez["name"] = update.poll_answer.user.username
    poll = list(poll_repo.get(poll_id=update.poll_answer.poll_id))
    rez["poll_id"] = update.poll_answer.poll_id
    rez["chat_id"] = poll[0].chat_id
    rez["poll_question"] = poll[0].question
    options = poll[0].options.split(",")
    rez["user_options"] = ",".join(
        [options[option] for option in update.poll_answer.option_ids]
    )
    logger.info("Перехвачен ответ %s", rez)
    user_repo.add(User(**rez))


async def poll_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    cur_time = datetime.now().time().strftime("%H:%M")
    days_of_week = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    dow = days_of_week[datetime.now().weekday()]
    for poll in poll_repo.get(start_time=cur_time, dow=dow):
        msg = await context.bot.send_poll(
            chat_id=poll.chat_id,
            question=poll.question,
            options=poll.options.split(","),
            is_anonymous=False,
        )
        poll.poll_id = msg.poll.id
        poll.message_id = msg.message_id
        poll_repo.update(poll)
    for poll in poll_repo.get(end_time=cur_time, dow=dow):
        end_poll = await context.bot.stopPoll(
            chat_id=poll.chat_id, message_id=poll.message_id
        )
        logger.info("Опроса %s завершен", end_poll)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Статистика опросов"""
    users = user_repo.get(
        chat_id=update.message.chat_id, user_id=update.message.from_user.id
    )
    if users:
        for user in users:
            await update.message.reply_text(
                f"""Пользователь: {user[0]}\nОтветил на вопрос: {user[1]}\n{user[2]} раз:""",
                reply_markup=ReplyKeyboardRemove(),
            )
    return ConversationHandler.END


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                MessageHandler(filters.Regex("Создать опрос"), new_poll),
                MessageHandler(filters.Regex("Удалить опрос"), list_poll),
                MessageHandler(filters.Regex("Cтатистика"), stats),
            ],
            CREATE_POLL: [
                MessageHandler(filters.POLL, create_poll),
            ],
            POLL_DOW: [
                MessageHandler(filters.Regex(r"^[ПНВТСРЧБ,]+$"), poll_dow),
            ],
            POLL_TIME: [
                MessageHandler(filters.Regex(r"\b\d{1,2}:\d{2}\b"), poll_time),
            ],
            POLL_DURATION: [
                MessageHandler(filters.Regex(r"\b\d{1,2}:\d{2}\b"), poll_duration),
            ],
            LIST_POLL: [
                MessageHandler(filters.Regex("Удалить опрос"), list_poll),
            ],
            DELETE_POLL: [
                MessageHandler(filters.Regex(r"^\d+$"), delete_poll),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(PollAnswerHandler(poll_answer))
    application.add_handler(conv_handler)
    job_queue = application.job_queue
    job_queue.run_repeating(poll_job, interval=60, first=3)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
