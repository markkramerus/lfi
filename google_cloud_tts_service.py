"""
Text-to-Speech service using Google Cloud TTS API.
Provides high-quality voices without requiring pitch shifting.
"""
import os
import hashlib
from pathlib import Path
import threading
import queue
from google.cloud import texttospeech

class GoogleCloudTTSService:
    def __init__(self, audio_dir="static/audio"):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Google Cloud TTS client
        try:
            self.client = texttospeech.TextToSpeechClient()
            print("Google Cloud TTS initialized successfully")
        except Exception as e:
            print(f"Error initializing Google Cloud TTS: {e}")
            raise
        
        # Queue for async audio generation
        self.generation_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
        # Voice configurations for different speakers
        # No pitch shifting needed - these voices are already optimized
        self.voice_configs = {
            "speaker1": {
                "name": "en-US-Wavenet-G", #"en-US-Chirp3-HD-Autonoe",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "speaker2": {
                "name": "en-US-Wavenet-J", #"en-US-Chirp3-HD-Achird",
                "gender": texttospeech.SsmlVoiceGender.MALE
            }
        }
    
    def _get_audio_filename(self, text, speaker_id):
        """Generate a unique filename based on text and speaker."""
        text_hash = hashlib.md5(f"{speaker_id}:{text}".encode()).hexdigest()
        return f"{text_hash}.mp3"
    
    # def _add_sentence_punctuation(self, text):
    #     """Add periods to lines that don't end with proper punctuation."""
    #     lines = text.split('\n')
    #     processed_lines = []
        
    #     for line in lines:
    #         stripped = line.rstrip()
    #         if not stripped:
    #             # Keep empty lines as is
    #             processed_lines.append(line)
    #             continue
            
    #         # Check if line ends with punctuation
    #         if stripped[-1] not in '.!?:;,':
    #             # Add a period to make it a proper sentence
    #             processed_lines.append(stripped + '.')
    #         else:
    #             processed_lines.append(line)
        
    #     return '\n'.join(processed_lines)
    
    def _generate_audio_file(self, text, speaker_id):
        """Generate audio file for the given text and speaker."""
        filename = self._get_audio_filename(text, speaker_id)
        filepath = self.audio_dir / filename
        
        # Skip if already exists and is non-empty
        if filepath.exists() and filepath.stat().st_size > 0:
            return filename
        
        try:
            # Clean text for better TTS
            clean_text = text.strip()
            if not clean_text:
                return None
            
            # Add periods to lines without proper punctuation
            #lean_text = self._add_sentence_punctuation(clean_text)
            
            # Get voice config for speaker
            voice_config = self.voice_configs.get(speaker_id, self.voice_configs["speaker1"])
            
            # Set the text input
            synthesis_input = texttospeech.SynthesisInput(text=clean_text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_config["name"],
                ssml_gender=voice_config["gender"]
            )
            
            # Select the audio file type
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Write the response to the output file
            with open(filepath, "wb") as out:
                out.write(response.audio_content)
            
            # Verify file was created and has content
            if filepath.exists() and filepath.stat().st_size > 0:
                print(f"Generated audio: {filename} ({filepath.stat().st_size} bytes)")
                return filename
            else:
                print(f"Error: Generated empty audio file for: {text[:50]}...")
                return None
                
        except Exception as e:
            print(f"Error generating audio for '{text[:50]}...': {e}")
            return None
    
    def _process_queue(self):
        """Background worker to process audio generation queue."""
        while True:
            try:
                task = self.generation_queue.get()
                if task is None:
                    break
                
                text, speaker_id = task
                self._generate_audio_file(text, speaker_id)
                self.generation_queue.task_done()
            except Exception as e:
                print(f"Error in TTS worker: {e}")
    
    def generate_audio_async(self, text, speaker_id):
        """Queue audio generation for async processing."""
        self.generation_queue.put((text, speaker_id))
    
    def generate_audio(self, text, speaker_id):
        """Generate audio synchronously and return filename."""
        return self._generate_audio_file(text, speaker_id)
    
    def get_audio_url(self, text, speaker_id):
        """Get the URL for the audio file (generate if needed)."""
        filename = self._get_audio_filename(text, speaker_id)
        filepath = self.audio_dir / filename
        
        if not filepath.exists():
            filename = self._generate_audio_file(text, speaker_id)
        
        if filename:
            return f"/static/audio/{filename}"
        return None

# Global TTS service instance - will be initialized by main.py
google_cloud_tts_service = None
