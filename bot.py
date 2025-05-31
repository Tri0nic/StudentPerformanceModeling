import os
import xgboost as xgb
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from dotenv import load_dotenv

SUBJECTS = ['МАТЕМАТИКА(ЕГЭ)', 'ФИЗИКА(ЕГЭ)', 'ИНФОРМАТИКА(ЕГЭ)', 'МАТЕМАТИКА(ДВИ)', 'РУССКИЙ ЯЗЫК(ЕГЭ)']
FACULTIES = ['ВМК МГУ']
user_data = {}

SELECT_FACULTY, ASKING = range(2)

booster = xgb.Booster()
booster.load_model("xgb_model.json")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[fac] for fac in FACULTIES]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите факультет:", reply_markup=reply_markup)
    return SELECT_FACULTY

async def select_faculty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    faculty = update.message.text
    if faculty not in FACULTIES:
        await update.message.reply_text("Пожалуйста, выберите факультет, используя кнопку.")
        return SELECT_FACULTY

    context.user_data['scores'] = {}
    context.user_data['subject_index'] = 0

    await update.message.reply_text(
        f"Вы выбрали: {faculty}.\nВведите балл по предмету {SUBJECTS[0]}:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASKING

async def handle_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['subject_index']
    subject = SUBJECTS[index]

    try:
        score = float(update.message.text)
        context.user_data['scores'][subject] = score
    except ValueError:
        await update.message.reply_text("Введите число.")
        return ASKING

    index += 1
    if index < len(SUBJECTS):
        context.user_data['subject_index'] = index
        await update.message.reply_text(f"Введите балл по предмету {SUBJECTS[index]}:")
        return ASKING
    else:
        input_df = pd.DataFrame([context.user_data['scores']])
        dmatrix = xgb.DMatrix(input_df, feature_names=SUBJECTS)
        prediction = booster.predict(dmatrix)[0]
        await update.message.reply_text(f"Прогнозируемый средний балл в университете: {prediction:.2f}")
        return ConversationHandler.END

if __name__ == "__main__":
    load_dotenv()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_FACULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_faculty)],
            ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_score)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.run_polling()
