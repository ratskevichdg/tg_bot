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
from ibm_watson import VisualRecognitionV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator


TOKEN = '{your_telegram_bot_token}'
CHAT_ID = '{your_telegram_chat_id}'
IBM_TOKEN = '{your_ibm_watson_key}'
IBM_URL = '{your_ibm_watson_url}'
IBM_VERSION = '{your_ibm_watson_version}'

HELP = """
What can I do? Let's take a look.

/start - bot greeting,
/help - current message.

simple calculator:
#run <arithmetic expression> - calculate entered <arithmetic expression>

work with files:
) <filename> <expression> - create new file <filename> and add <expression>
( <filename> <expression> - append <expression> to existing file <filename> 
^ <filename> - open and print <filename>'s content

If you send me a text message, the Google Dude will read it and send you a voice message 

If you send me a photo, I try to recognise what is shown in a photo
"""

FILES_PATH = './files/{f_name}'

TEMPLATES = {
    'greetings': 'Hi, {firstname} {lastname}! What\'s up?',
    'file_error': {
        'already_exist': ('Such a file already exists. '
                          'Think of a new name for the file\n'
                          'I already have the following filenames:\n{files_list}'),
        'not_exist': ('This file does not exist. Choose an existing file.'
                    'I already have the following files:\n{files_list}')

    },
    'wrong_command': ('Something get wrong. '
                      'Did you enter the command correctly?\n'
                      'Try again!'),
    'done': 'Done!',
    'image_recognition': 'I think it\'s a {name}.\nAnd I\'m {percent:.0%} sure of it'
}


def start(updater, context):
    """
    returns greetings from the bot
    """
    user = updater.message.from_user
    updater.message.reply_text(TEMPLATES['greetings'].format(
        firstname=user['first_name'], 
        lastname=user['last_name'] 
        ))


def help_cmd(updater, context):
    """
    returns <HELP> message
    """
    updater.message.reply_text(HELP)


def run(updater, context):
    """
    returns the result of the <eval> function
    """
    data = updater.message.text[5:]
    res = eval(data)
    updater.message.reply_text(str(res))


def new_file(updater, context):
    """
    create new file <filename> and add <expression>
    """
    try:
        user_msg = updater.message.text[2:]
        first_space = user_msg.index(' ')
    except ValueError:
        updater.message.reply_text(TEMPLATES['wrong_command'])

    file_name = user_msg[:first_space]
    file_text = user_msg[first_space+1:]
    
    if file_name in listdir('./files/'):
        updater.message.reply_text(TEMPLATES['file_error']['already_exist'].format(
            files_list=str(listdir('./files'))[1:-1]
        ))
    else:
        with open(FILES_PATH.format(f_name=file_name), 'w') as file:
            file.write(file_text + '\n')
        updater.message.reply_text(TEMPLATES['done'])


def add_to_file(updater, context):
    """
    append <expression> to existing file <filename>
    """
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
        updater.message.reply_text(TEMPLATES['file_error']['not_exist'].format(
            files_list=str(listdir('./files'))[1:-1]
        ))


def read_file(updater, context):
    """
    open and print <filename>'s content
    """
    file_name = updater.message.text[2:]
    if file_name in listdir('./files/'):
        with open(FILES_PATH.format(f_name=file_name), 'r') as file:
            updater.message.reply_text('\n'.join(line for line in file.readlines()))
    else:
        updater.message.reply_text(TEMPLATES['file_error']['not_exist'].format(
            files_list=str(listdir('./files'))[1:-1]
        ))


def message(updater, context):
    """
    takes the text and returns audio file where robot reads the text
    (str -> voice_message.ogg)
    """
    bot = Bot(token=TOKEN)
    text = updater.message.text
    ru_voice_id = "com.apple.speech.synthesis.voice.yuri"
    engine = pyttsx3.init()
    engine.setProperty('voice', ru_voice_id)
    engine.save_to_file(text, './audio/voice_message.wav')
    engine.runAndWait()

    # Formatting to the required codec
    subprocess.run([
        "ffmpeg", '-i', "./audio/voice_message.wav", 
        '-acodec', 'libopus', "./audio/voice_message.ogg", '-y'
        ])

    bot.send_voice(chat_id=CHAT_ID, voice=open('./audio/voice_message.ogg', 'rb'))


def image(updater, context):
    """
    takes an image and returns what is drawn in the image from IBM Watson API
    """
    bot = Bot(token=TOKEN)
    file_id = updater.message.photo[-1]
    newFile = bot.get_file(file_id)
    newFile.download('./images/img.jpg')

    # Set up IBM Watson VisualRecognition API
    authenticator = IAMAuthenticator(IBM_TOKEN)
    visual_recognition = VisualRecognitionV3(
        version=IBM_VERSION,
        authenticator=authenticator
        )
    visual_recognition.set_service_url(IBM_URL) 

    # Send a request to IBM Watson and recieve the result
    with open('./images/img.jpg', 'rb') as image_file:
        classes = visual_recognition.classify(images_file=image_file,
            threshold='0.6'
            ).get_result()

    img_recognition = classes['images'][0]['classifiers'][0]['classes'][0]['class']
    recognition_score = classes['images'][0]['classifiers'][0]['classes'][0]['score']
    updater.message.reply_text(TEMPLATES['image_recognition'].format(
        name=img_recognition, percent=recognition_score
        ))


def run_updater():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_cmd))
    dispatcher.add_handler(PrefixHandler('#', 'run', run))
    dispatcher.add_handler(PrefixHandler(')', '', new_file))
    dispatcher.add_handler(PrefixHandler('(', '', add_to_file))
    dispatcher.add_handler(PrefixHandler('^', '', read_file))
    dispatcher.add_handler(MessageHandler(Filters.text, message))
    dispatcher.add_handler(MessageHandler(Filters.photo, image))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    run_updater()
