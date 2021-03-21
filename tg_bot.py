from keys import Keys #потом распиши что за файл такой

import pyttsx3
import subprocess
from os import listdir
from telegram import Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    PrefixHandler,
    Filters
)


TOKEN = Keys.tg_token

CHAT_ID = Keys.tg_chat_id

HELP = """
What can I do? Let's take a look.

/start - updater greeting,
/help - current message.

simple calculator:
#run <arithmetic expression> - calculate entered <arithmetic expression>

work with files:
) <filename> <expression> - create new file <filename> and add <expression>
( <filename> <expression> - append <expression> to existing file <filename> 
^ <filename> - open and print <filename>'s content

If you send me a text message, the Google Dude will read it and send you a voice message 
"""

FILES_PATH = './files/{f_name}'

TEMPLATES = {
    'greetings': 'Hi, {firstname} {lastname}! What\'s up?',
    'file_error': {
        'already_exist': ('Such a file already exists.'
                          'Think of a new name for the file'),
        'not_exist': 'This file does not exist. Choose an existing file',

    },
    'wrong_command': ('Something get wrong. '
                      'Did you enter the command correctly?\n'
                      'Try again!'),
    'done': 'Done!'
}


def start(updater, context):
    user = updater.message.from_user
    updater.message.reply_text(TEMPLATES['greetings'].format(
                    firstname=user['first_name'], 
                    lastname=user['last_name'] 
                    ))


def help_cmd(updater, context):
    updater.message.reply_text(HELP)


def run(updater, context):
    data = updater.message.text[5:]
    res = eval(data)
    updater.message.reply_text(str(res))


def new_file(updater, context):
    user_msg = ''
    first_space = 0
    try:
        user_msg = updater.message.text[2:]
        first_space = user_msg.index(' ')
    except ValueError:
        updater.message.reply_text(TEMPLATES['wrong_command'])

    file_name = user_msg[:first_space]
    file_text = user_msg[first_space+1:]
    
    if file_name in listdir('./files/'):
        updater.message.reply_text(TEMPLATES['file_error']['already_exist'])
    else:
        with open(FILES_PATH.format(f_name=file_name), 'w') as file:
            file.write(file_text + '\n')
        updater.message.reply_text(TEMPLATES['done'])
        updater.message.reply_text(str(listdir('./files')))


def add_to_file(updater, context):
    user_msg = ''
    first_space = 0
    try:
        user_msg = updater.message.text[2:]
        first_space = user_msg.index(' ')
    except ValueError:
        updater.message.reply_text(TEMPLATES['wrong_command'])

    file_name = user_msg[:first_space]
    file_text = user_msg[first_space+1:]
    
    if file_name in listdir('./files/'):
        with open(FILES_PATH.format(f_name=file_name), 'a') as file:
            file.write(file_text + '\n')
        updater.message.reply_text(TEMPLATES['done'])
    else:
        updater.message.reply_text(TEMPLATES['file_error']['not_exist'])


def read_file(updater, context):
    file_name = updater.message.text[2:]
    if file_name in listdir('./files/'):
        with open(FILES_PATH.format(f_name=file_name), 'r') as file:
            updater.message.reply_text('\n'.join(line for line in file.readlines()))
    else:
        updater.message.reply_text(TEMPLATES['file_error']['not_exist'])


def message(updater, context):
    bot = Bot(token=TOKEN)
    text = updater.message.text
    # count = len(text)
    # updater.message.reply_text(str(count))

    ru_voice_id = "com.apple.speech.synthesis.voice.yuri"
    engine = pyttsx3.init()
    engine.setProperty('voice', ru_voice_id)
    engine.save_to_file(text, './audio/voice_message.wav')
    engine.runAndWait()

    subprocess.run([
        "ffmpeg", '-i', "./audio/voice_message.wav", 
        '-acodec', 'libopus', "./audio/voice_message.ogg", '-y'
        ])

    bot.send_voice(chat_id=CHAT_ID, voice=open('./audio/voice_message.ogg', 'rb'))


def run_updater():
    updater = Updater(TOKEN, use_context=True)
    # bot = Bot(token=TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_cmd))
    dispatcher.add_handler(PrefixHandler('#', 'run', run))
    dispatcher.add_handler(PrefixHandler(')', '', new_file))
    dispatcher.add_handler(PrefixHandler('(', '', add_to_file))
    dispatcher.add_handler(PrefixHandler('^', '', read_file))
    dispatcher.add_handler(MessageHandler(Filters.text, message))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_updater()
