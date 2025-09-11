from flask import Flask, render_template, jsonify
import threading

app = Flask(__name__)
chat_history = []
scenario_info = {}

def update_chat_history(new_history):
    global chat_history
    chat_history = new_history

def update_scenario_info(new_info):
    global scenario_info
    scenario_info = new_info

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    return jsonify(chat_history)

@app.route('/info')
def info():
    return jsonify(scenario_info)

def run_app():
    app.run(port=5001)

def start_flask_app():
    flask_thread = threading.Thread(target=run_app)
    flask_thread.daemon = True
    flask_thread.start()
