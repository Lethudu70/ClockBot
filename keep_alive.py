from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    # Lance Flask dans un thread séparé
    Thread(target=app.run, kwargs={'host':'0.0.0.0','port':5000}).start()
