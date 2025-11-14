from flask import Flask, render_template, jsonify, request
import threading
import signal
import os
from tts_service import tts_service

app = Flask(__name__)
chat_history = []
chat_history_lock = threading.Lock()  # Lock for thread-safe access to chat_history
scenario_info = {}
audio_playback_complete = threading.Event()
audio_playback_complete.set()  # Initially ready
flask_thread = None
is_paused = False  # Global pause state

def update_chat_history(new_history):
    global chat_history
    # Audio is now generated in main.py before this is called
    with chat_history_lock:
        chat_history = new_history

def update_scenario_info(new_info):
    global scenario_info
    scenario_info = new_info

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    with chat_history_lock:
        # Create a copy to avoid holding the lock during JSON serialization
        history_copy = list(chat_history)
    return jsonify(history_copy)

@app.route('/info')
def info():
    return jsonify(scenario_info)

@app.route('/audio_complete', methods=['POST'])
def audio_complete():
    """Frontend calls this when audio playback is complete"""
    global audio_playback_complete
    audio_playback_complete.set()
    return jsonify({"status": "ok"})

@app.route('/pause_state', methods=['GET', 'POST'])
def pause_state():
    """Get or set the pause state"""
    global is_paused
    if request.method == 'POST':
        data = request.get_json()
        is_paused = data.get('paused', False)
        return jsonify({"paused": is_paused})
    else:
        return jsonify({"paused": is_paused})

def is_execution_paused():
    """Check if execution is paused"""
    global is_paused
    return is_paused

def wait_for_audio_playback():
    """Main loop calls this to wait for frontend to finish playing audio"""
    global audio_playback_complete
    audio_playback_complete.wait()
    audio_playback_complete.clear()  # Reset for next message

def run_app():
    app.run(port=5001, use_reloader=False)

def start_flask_app():
    global flask_thread
    flask_thread = threading.Thread(target=run_app)
    flask_thread.daemon = True  # Daemon thread will exit when main thread exits
    flask_thread.start()

def shutdown_flask_app():
    """Shutdown the Flask server gracefully"""
    # Send SIGINT to trigger Flask shutdown
    if flask_thread and flask_thread.is_alive():
        # Flask will shut down when the main thread exits (daemon thread)
        pass
