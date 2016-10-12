from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
import signal
import sys
from tinydb import TinyDB, Query
import requests
from requests import ConnectionError

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

    response = request("tariffs", user, bot, update)
    if not response:
        return

    text = ""
    for x in response.json():
        text += "- " + x["name"] + "\n"
    bot.sendMessage(chat_id=update.message.chat_id, text="Available tariffs:\n" + text)


def options(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        return

    response = request("options", user, bot, update)
    if not response:
        return

    text = ""
    for x in response.json():
        text += "- " + x["name"] + "\n"
    bot.sendMessage(chat_id=update.message.chat_id, text="Available options:\n" + text)


def login(bot, update):
    user = get_user(update)
    if user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are logged in")
        return
    bot.sendMessage(chat_id=update.message.chat_id, text="Please send email and password")
    dispatcher.add_handler(MessageHandler([Filters.text], _try_login))


def logout(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        return

    user_search = Query()
    db.remove(user_search.chat_id == update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text="Success!")


def my_contracts(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        return

    response = request("customers/"+str(user['id']), user, bot, update)
    if not response:
        return

    text = ""
    for contract in response.json()['contracts']:
        text += " " + contract["number"] + "\n"
    bot.sendMessage(chat_id=update.message.chat_id, text="Your contracts:\n" + text)


# ----------------- commands end


def request(url, user, bot, update):
    try:
        response = requests.get(BASE_URL + url, auth=(user["email"], user["password"]))
    except ConnectionError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Service is not available")
        return False

    if response.status_code != requests.codes.ok:
        bot.sendMessage(chat_id=update.message.chat_id, text="Something is wrong. Try again or write to " + DEV_EMAIL)
        return False
    return response


def _try_login(bot, update):
    try:
        username, password = update.message.text.split()
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Please send email and password")
        dispatcher.remove_handler([Filters.text])
        return

    try:
        r = requests.get(BASE_URL + "users/me", auth=(username, password))
    except ConnectionError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Service is not available")
        return

    if r.status_code != requests.codes.ok:
        bot.sendMessage(chat_id=update.message.chat_id, text="Wrong email or password.\nTry again")
        return

    try:
        user = r.json()
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Something is wrong. Try again or write to " + DEV_EMAIL)
        return

    access = False
    for role in user['roles']:
        if role == "ROLE_USER":
            access = True
        elif role == "ROLE_ADMIN":
            access = False
            break

    if not access:
        bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, this bot available only for customers")
        dispatcher.remove_handler([Filters.text])
        return

    db.insert({'chat_id': update.message.chat_id, 'user': {'id': user['id'],
                                                           'name': user['name'],
                                                           'surname': user['surname'],
                                                           'email': username,
                                                           'password': password}})
    bot.sendMessage(chat_id=update.message.chat_id, text="Hello, " + user['name']
                                                         + "!\nTry to get available tariffs or something else")
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
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('tariffs', tariffs))
    dispatcher.add_handler(CommandHandler('options', options))
    dispatcher.add_handler(CommandHandler('login', login))
    dispatcher.add_handler(CommandHandler('logout', logout))
    dispatcher.add_handler(CommandHandler('mycontracts', my_contracts))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    token = open('token').read()
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    signal.signal(signal.SIGINT, signal_stop)

    db = TinyDB("db.json")

    set_up()
