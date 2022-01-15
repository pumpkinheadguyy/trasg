import telebot
from telebot import types
import mysql.connector as sql
import configparser

config = configparser.ConfigParser()
config.read("config.ini")
token = config["Tg_bot"]["bot_token"]
bot = telebot.TeleBot(token)


# Connecting to database and executing query
def db_query(query):
    config = configparser.ConfigParser()
    config.read("config.ini")
    c = config["DataBase"]
    try:
        with sql.connect(host=c["host"], user=c["user"], password=c["password"], database=c["database"]) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                if "SELECT" in query or "SHOW" in query:
                    return list(cursor.fetchall())
            connection.commit()
    except sql.Error as ex:
        # print(ex)
        return -1


# Start
@bot.message_handler(commands=["start"])
def start_message(message):
    chat_id = message.chat.id
    query = f"""INSERT INTO users 
                VALUES ('{chat_id}', no, null, null);"""
    db_query(query)
    bot.send_message(chat_id=chat_id, text="You can start talking by pressing 'Start conversation'\
                                            or you can choose category by pressing\
                                            'Choose category'.", reply_markup=start_markup)


# Changing category UI
@bot.message_handler(func=lambda msg: msg.text == "Choose category")
def show_categories(message):
    bot.send_message(chat_id=message.chat.id, text="Choose one of the categories", reply_markup=category_markup)


# Changing category
@bot.message_handler(func=lambda msg: msg.text in categories)
def change_category(message):
    query = f"""UPDATE users
                SET category = '{message.text}'
                WHERE chat_id = '{message.chat.id}'"""
    db_query(query)
    bot.send_message(chat_id=message.chat.id, text=f"{message.text} was chosen", reply_markup=start_markup)


# Adding in queue
@bot.message_handler(func=lambda message: message.text == "Start conversation")
def handle_start(message):
    types.ReplyKeyboardRemove()
    id = message.chat.id
    query = f"""UPDATE users 
                SET in_queue='yes'
                WHERE chat_id='{id}'"""
    db_query(query)
    bot.send_message(chat_id=id, text="You were added in queue. Waiting...", reply_markup=end_queue_markup)
    connect_users(id)


# Ending queue
@bot.message_handler(func=lambda message: message.text == "End queue")
def end_queue(message):
    types.ReplyKeyboardRemove()
    id = message.chat.id
    query = f"""UPDATE users
                SET in_queue = 'no'
                WHERE chat_id = '{id}'"""
    db_query(query)
    bot.send_message(chat_id=id, text="You were disconnected")


# Connecting users
def connect_users(user_1):
    query = """SELECT chat_id FROM users
                WHERE in_queue != 'no'"""
    users_in_queue = db_query(query)
    if len(users_in_queue) > 1:
        for u in users_in_queue:
            if u != user_1:
                query = """SELECT category FROM users
                                WHERE chat_id = {}"""
                if db_query(query.format(user_1)) == db_query(query.format(u)):
                    user_2 = u[0]
                    break
        print(f"[INFO] User 1: {user_1}, user 2: {user_2}")
        query = """UPDATE users
                    SET in_queue = no, connected = {}
                    WHERE chat_id = {}"""
        db_query(query.format(user_1, user_2))
        db_query(query.format(user_2, user_1))
        print(f"{user_2} connected with {user_1}")
        bot.send_message(chat_id=user_1, text="User found! Just text smth.", reply_markup=end_markup)
        bot.send_message(chat_id=user_2, text="User found! Just text smth.", reply_markup=end_markup)


# End conv
@bot.message_handler(func=lambda message: message.text == "End conversation")
def end_conv(message):
    types.ReplyKeyboardRemove()
    user_1 = message.chat.id
    query = f"""SELECT connected FROM users
                WHERE chat_id = '{user_1}'"""
    user_2 = db_query(query)[0]

    query = """UPDATE users
                SET connected = null
                WHERE chat_id = {}"""
    db_query(query.format(user_1))
    db_query(query.format(user_2))
    bot.send_message(chat_id=user_1, text="You were disconnected", reply_markup=start_markup)
    bot.send_message(chat_id=user_2, text="You were disconnected", reply_markup=start_markup)


# Finding if user is connected to someone and returning someone's id
def get_con_user(user):
    query = f"""SELECT connected FROM users
                WHERE chat_id = '{user}'"""
    return db_query(query)


# Sending messages
@bot.message_handler(func=lambda msg: get_con_user(msg.chat.id)[0][0] != 'null')
def send_msg(message):
    con_user = get_con_user(message.chat.id)[0][0]
    if "http" in message.text:
        bot.send_message(chat_id=message.chat.id, text="Sorry but you can't send links")
    bot.send_message(chat_id=con_user, text=message.text)


if __name__ == "__main__":
    # Reading themes from file
    categories = []
    with open("categories.txt", "r") as f:
        for category in f.readlines():
            categories.append(category.strip())

    # Diff markups
    start_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    itembtn = types.KeyboardButton("Start conversation")
    itembtn1 = types.KeyboardButton("Choose category")
    start_markup.add(itembtn, itembtn1)
    end_queue_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    itembtn = types.KeyboardButton("End queue")
    end_queue_markup.add(itembtn)
    end_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    itembtn = types.KeyboardButton("End conversation")
    end_markup.add(itembtn)
    category_markup = types.ReplyKeyboardMarkup()
    for category in categories:
        btn = types.KeyboardButton(category)
        category_markup.add(btn)

    # bot.send_message(chat_id="624008376", text="Startui")
    bot.infinity_polling()
