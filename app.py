from datetime import datetime

from loguru import logger
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

from config import TOKEN
from model import Poll, User
from repository import poll_repo, user_repo

MENU, CREATE_POLL, POLL_DOW, POLL_TIME, POLL_DURATION, LIST_POLL, DELETE_POLL = range(7)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало. Точка входа в контекст"""
    user = update.message.from_user
    reply_keyboard = [["Создать опрос", "Удалить опрос", "Cтатистика"]]
    logger.info(f"Пользователь {user.name} запустил бота.")
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
    logger.info(f"Пользователь {user.name} создает опрос.")
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
        f"Пользователь {user.name} отправил опрос.\n Вопрос: {update.message.poll.question},\n Доступные опции: {context.user_data['options']}",
    )
    await update.message.reply_text("Укажите дни недели публикации опроса")
    await update.message.reply_text("Например: ПН,СР,ПТ")
    return POLL_DOW


async def poll_dow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение дней недели опроса"""
    user = update.message.from_user
    context.user_data["dows"] = update.message.text
    logger.info(f"Пользователь {user.name} установил день недели.")
    await update.message.reply_text("Укажите время публикации опроса")
    await update.message.reply_text("Например: 12:30")
    return POLL_TIME


async def poll_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени публикации опроса в формате HH:MM"""
    user = update.message.from_user
    context.user_data["start_time"] = update.message.text
    logger.info(f"Пользователь {user.name} установил время начала опроса.")
    await update.message.reply_text("Укажите время закрытия опроса")
    await update.message.reply_text("Например: 15:00")
    return POLL_DURATION


async def poll_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени окончания опроса в формате HH:MM"""
    user = update.message.from_user
    context.user_data["end_time"] = update.message.text
    context.user_data["chat_id"] = update.message.chat_id
    logger.info(f"Пользователь {user.name} установил время закрытия опроса.")
    poll_repo.add(Poll(**context.user_data))
    logger.info(f"Создан опрос {context.user_data}")
    await update.message.reply_text("Опрос успешно создан")
    return ConversationHandler.END


async def list_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вывод списка опросов"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.name} открыл список опросов.")
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
    user = update.message.from_user
    poll_repo.delete(int(update.message.text))
    logger.info(f"Пользователь {user.name} удалил опрос.")
    await update.message.reply_text(
        "Опрос удален",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выход из контекста"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.name} закрыл контекст.")
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
        [options[option] for option in update.poll_answer.option_ids],
    )
    logger.info(f"Перехвачен ответ на опрос {rez}")
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
        logger.info(f"Опроса {msg} опубликован")
    for poll in poll_repo.get(end_time=cur_time, dow=dow):
        end_poll = await context.bot.stopPoll(
            chat_id=poll.chat_id, message_id=poll.message_id,
        )
        logger.info(f"Опроса {end_poll} завершен")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Статистика опросов"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.name} запросил статистику.")
    users = user_repo.get(
        chat_id=update.message.chat_id, user_id=update.message.from_user.id,
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
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
