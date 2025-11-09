from flask import Flask, render_template, jsonify, request
import threading
from tts_service import tts_service

app = Flask(__name__)
chat_history = []
scenario_info = {}
audio_playback_complete = threading.Event()
audio_playback_complete.set()  # Initially ready

def update_chat_history(new_history):
    global chat_history
    # Audio is now generated in main.py before this is called
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

@app.route('/audio_complete', methods=['POST'])
def audio_complete():
    """Frontend calls this when audio playback is complete"""
    global audio_playback_complete
    audio_playback_complete.set()
    return jsonify({"status": "ok"})

def wait_for_audio_playback():
    """Main loop calls this to wait for frontend to finish playing audio"""
    global audio_playback_complete
    audio_playback_complete.wait()
    audio_playback_complete.clear()  # Reset for next message

def run_app():
    app.run(port=5001)

def start_flask_app():
    flask_thread = threading.Thread(target=run_app)
    flask_thread.daemon = True
    flask_thread.start()
