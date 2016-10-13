#!/usr/bin/env python
# coding=utf-8
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
import signal
from tinydb import TinyDB, Query
import requests
from requests import ConnectionError
import re
import logging

import sys

reload(sys)
sys.setdefaultencoding('utf8')

DEV_EMAIL = "AlexPl292@gmail.com"
BASE_URL = "http://localhost:8080/JavaSchool/rest/"

LOGIN, CHANGEPASS = range(2)


logging.basicConfig(filename="log/JSTelegram.log", format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
# ----------------- commands


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a bot!\nMaybe you want to /login?")
    logging.info("/start command")


def tariffs(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        logging.error("/tariffs command fail. Not authorized. chat_id:"+str(update.message.chat_id))
        return

    response = request_get("tariffs", user, bot, update)
    if not response:
        logging.error("/tariffs command fail. Bad response:"+str(response))
        return

    keyboard = []
    for tariff in response.json():
        keyboard.append([InlineKeyboardButton(tariff['name'], callback_data='tariff'+str(tariff['id']))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Available tariffs:', reply_markup=reply_markup)
    logging.info("/tariffs command success.")


def options(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        logging.error("/options command fail. Not authorized. chat_id:"+str(update.message.chat_id))
        return

    response = request_get("options", user, bot, update)
    if not response:
        logging.error("/options command fail. Bad response:"+str(response))
        return

    keyboard = []
    for option in response.json():
        keyboard.append([InlineKeyboardButton(option['name'], callback_data='option'+str(option['id']))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Available option:', reply_markup=reply_markup)
    logging.info("/options command success.")


def login_enter(bot, update):
    user = get_user(update)
    if user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are logged in")
        logging.error("/login command fail. Already logged in. Chat_id:"+str(update.message.chat_id))
        return ConversationHandler.END
    bot.sendMessage(chat_id=update.message.chat_id, text="Enter email and password")
    return LOGIN


def login(bot, update):
    try:
        username, password = update.message.text.split()
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Enter email and password")
        return LOGIN

    try:
        r = requests.get(BASE_URL + "users/me", auth=(username, password))
    except ConnectionError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Service is not available")
        logging.error("/login command fail. ConnectionError exception")
        return ConversationHandler.END

    if r.status_code != requests.codes.ok:
        bot.sendMessage(chat_id=update.message.chat_id, text="Wrong email or password.\nTry again")
        logging.error("/login command fail. Bad response status:" + str(r))
        return LOGIN

    try:
        user = r.json()
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Something is wrong. Try again or write to " + DEV_EMAIL)
        logging.error("/login command fail. Bad response. Cannot convert to JSON:" + str(user.text))
        return ConversationHandler.END

    access = False
    for role in user['roles']:
        if role == "ROLE_USER":
            access = True
        elif role == "ROLE_ADMIN":
            access = False
            break

    if not access:
        bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, this bot available only for customers")
        logging.error("/login command fail. Wrong access rights")
        return ConversationHandler.END

    db.insert({'chat_id': update.message.chat_id, 'user': {'id': user['id'],
                                                           'name': user['name'],
                                                           'surname': user['surname'],
                                                           'email': username,
                                                           'password': password}})
    bot.sendMessage(chat_id=update.message.chat_id, text="Hello, " + user['name']
                                                         + "!\nTry to get available tariffs or something else")
    logging.info("/login command success.")
    return ConversationHandler.END


def logout(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="You are not authorized")
        logging.error("/logout command fail. Not logged in")
        return

    user_search = Query()
    db.remove(user_search.chat_id == update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text="Success!")
    logging.info("/logout command success.")


def my_contracts(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="you are not authorized")
        logging.error("/mycontracts command fail. Not authorized. chat_id:"+str(update.message.chat_id))
        return

    response = request_get("customers/" + str(user['id']), user, bot, update)
    if not response:
        logging.error("/mycontracts command fail. Bad response:"+str(response))
        return

    text = ""
    for contract in response.json()['contracts']:
        text += " " + contract["number"] + "\n"
    bot.sendMessage(chat_id=update.message.chat_id, text="Your contracts:\n" + text)
    logging.info("/mycontracts command success.")


def change_password_enter(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="you are not authorized")
        logging.error("/newpassword command fail. Not authorized. chat_id:"+str(update.message.chat_id))
        return ConversationHandler.END

    bot.sendMessage(chat_id=update.message.chat_id, text="Enter new password")
    return CHANGEPASS


def change_password(bot, update):
    user = get_user(update)
    if not user:
        bot.sendMessage(chat_id=update.message.chat_id, text="you are not authorized")
        logging.error("/newpassword command fail. Not authorized. chat_id:"+str(update.message.chat_id))
        return ConversationHandler.END

    new = update.message.text

    if not re.match("^[A-Za-z0-9_-]*$", new):
        bot.sendMessage(chat_id=update.message.chat_id, text="New password contains wrong characters\n"+
                                                             "Try again")
        logging.error("/newpassword command fail. Bad new password")
        return CHANGEPASS

    if len(new) < 8:
        bot.sendMessage(chat_id=update.message.chat_id, text="New password must be at least eight characters\n"+
                                                             "Try again")
        logging.error("/newpassword command fail. Bad new password")
        return CHANGEPASS

    try:
        data = {'oldPassword': user['password'], "newPassword": new, "newPasswordRepeat": new}
        r = requests.put(BASE_URL + "users/"+str(user['id']), auth=(user["email"], user["password"]), data=data)
    except ConnectionError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Service is not available")
        logging.error("/newpassword command fail. ConnectionError exception")
        return ConversationHandler.END

    if r.status_code != requests.codes.ok:
        bot.sendMessage(chat_id=update.message.chat_id, text="Something is wrong\npassword is not changed")
        logging.error("/newpassword command fail. Bad response status:" + str(r))
        return ConversationHandler.END

    user_search = Query()
    db.remove(user_search.chat_id == update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text="Success! Login again")
    logging.info("/newpassword command success.")
    return ConversationHandler.END


def button(bot, update):
    user = get_user(update)
    if not user:
        logging.error("button methon fail. Not authorized. chat_id:"+str(update.callback_query.message.chat_id))
        bot.sendMessage(chat_id=update.callback_query.message.chat_id, text="you are not authorized")
        return

    query = update.callback_query

    if query.data.startswith("tariff"):
        id = query.data[6:]
        response = request_get("tariffs/"+id, user, bot, update)
        if not response:
            return
        json = response.json()
        text = "Tariff: " + json["name"] + "\n"
        text += "Description: " + json["description"] + "\n"
        text += "Cost: " + "{0:.2f}".format(json["cost"]) + "₽" + "\n"
        text += "Available options:"

        keyboard = []
        for option in json['possibleOptions']:
            keyboard.append([InlineKeyboardButton(option['name'], callback_data='option'+str(option['id']))])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.callback_query.message.reply_text(text, reply_markup=reply_markup)

    elif query.data.startswith("option"):
        id = query.data[6:]
        response = request_get("options/"+id, user, bot, update)
        if not response:
            return
        json = response.json()
        text = "Option: " + json["name"] + "\n"
        text += "Description: " + json["description"] + "\n"
        text += "Cost: " + "{0:.2f}".format(json["cost"]) + "₽" + "\n"
        text += "Connection cost: " + "{0:.2f}".format(json["connectCost"]) + "₽" + "\n"

        if json['requiredFrom']:
            text += "Required:" + "\n"
            for opt in json['requiredFrom']:
                text += "  - "+opt['name'] + "\n"

        if json['requiredMe']:
            text += "Requires this options:" + "\n"
            for opt in json['requiredMe']:
                text += "  - "+opt['name'] + "\n"

        if json['forbiddenWith']:
            text += "Incompatible with:" + "\n"
            for opt in json['forbiddenWith']:
                text += "  - "+opt['name'] + "\n"

        text += "Available tariffs:"

        keyboard = []
        for tariff in json['possibleTariffsOfOption']:
            keyboard.append([InlineKeyboardButton(tariff['name'], callback_data='tariff'+str(tariff['id']))])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    logging.info("button method success.")


def cancel(bot, update):
    user = update.message.from_user
    logging.info("User %s canceled the conversation." % user.first_name)
    update.message.reply_text('Cancelled')

    return ConversationHandler.END
# ----------------- commands end


def request_get(url, user, bot, update):
    message = update.message
    if message is None:
        message = update.callback_query.message

    try:
        response = requests.get(BASE_URL + url, auth=(user["email"], user["password"]))
    except ConnectionError:
        bot.sendMessage(chat_id=message.chat_id, text="Service is not available")
        logging.error("request fail. ConnectionError exception. Url:" + BASE_URL + url)
        return False

    if response.status_code != requests.codes.ok:
        bot.sendMessage(chat_id=message.chat_id, text="Something is wrong. Try again or write to " + DEV_EMAIL)
        logging.error("/newpassword command fail. Bad response status:" + str(response))
        return False
    return response


def get_user(update):
    message = update.message
    if message is None:
        message = update.callback_query.message
    user_search = Query()

    user = db.search(user_search.chat_id == message.chat_id)
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
    dispatcher.add_handler(CommandHandler('logout', logout))
    dispatcher.add_handler(CommandHandler('mycontracts', my_contracts))
    dispatcher.add_handler(CallbackQueryHandler(button))

    login_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login_enter)],
        states={LOGIN: [MessageHandler([Filters.text], login)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(login_handler)

    change_password_handler = ConversationHandler(
        entry_points=[CommandHandler('newpassword', change_password_enter)],
        states={CHANGEPASS: [MessageHandler([Filters.text], change_password)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(change_password_handler)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    token = open('token').read()
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    signal.signal(signal.SIGINT, signal_stop)

    db = TinyDB("db.json")

    set_up()
