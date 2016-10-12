from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
import signal
import sys
from tinydb import TinyDB, Query
import requests


DEV_EMAIL = "AlexPl292@gmail.com"
BASE_URL = "http://localhost:8080/JavaSchool/rest/"


# ----------------- commands
def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def tariffs(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        return

    response = requests.get(BASE_URL+"tariffs", auth=(user["email"], user["password"]))
    text = ""
    for x in response.json():
        text += "- " + x["name"]+"\n"
    bot.sendMessage(chat_id=update.message.chat_id, text="Available tariffs:\n"+text)

# ----------------- commands end


def login(bot, update):
    user = get_user(update)
    if user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are logged in")
        return
    bot.sendMessage(chat_id=update.message.chat_id, text="Please send email and password")
    dispatcher.add_handler(MessageHandler([Filters.text], _try_login))


def _try_login(bot, update):
    try:
        username, password = update.message.text.split()
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Please send email and password")
        dispatcher.remove_handler([Filters.text])
        return

    r = requests.get(BASE_URL+"users/role", auth=(username, password))

    if r.status_code != requests.codes.ok:
        bot.sendMessage(chat_id=update.message.chat_id, text="Wrong email or password.\nTry again")
        return

    try:
        roles = r.json()
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Something is wrong. Try again or write to " + DEV_EMAIL)
        return

    access = False
    for role in roles:
        if role['authority'] == "ROLE_USER":
            access = True
        elif role['authority'] == "ROLE_ADMIN":
            access = False
            break

    if not access:
        bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, this bot available only for customers")
        dispatcher.remove_handler([Filters.text])
        return

    db.insert({'chat_id':update.message.chat_id, 'user':{'email':username, 'password':password}})
    bot.sendMessage(chat_id=update.message.chat_id, text="Success!\nTry to get available tariffs or something else")
    dispatcher.remove_handler([Filters.text])


def get_user(update):
    user_search = Query()
    user = db.search(user_search.chat_id == update.message.chat_id)
    if not user:
        return None
    return user[0]["user"]


def signal_stop():
    updater.stop()
    sys.exit(0)


def set_up():
    start_handler = CommandHandler('start', start)
    start_handler = CommandHandler('login', login)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(CommandHandler('tariffs', tariffs))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    updater = Updater(token='***REMOVED***')
    dispatcher = updater.dispatcher
    signal.signal(signal.SIGINT, signal_stop)

    db = TinyDB("db.json")

    set_up()
