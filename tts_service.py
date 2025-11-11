"""
Text-to-Speech service for generating audio from conversation messages.
Uses gTTS for simple TTS generation with different voices for each speaker.
"""
import os
import hashlib
import subprocess
from gtts import gTTS
from pathlib import Path
import threading
import queue

class TTSService:
    def __init__(self, audio_dir="static/audio"):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Queue for async audio generation
        self.generation_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
        # Voice configurations for different speakers   see https://gtts.readthedocs.io/en/latest/module.html
        # We'll use different languages/accents to differentiate voices
        self.voice_configs = {
            "speaker1": {"lang": "en", "tld": "ie", "slow": False}, 
            "speaker2": {"lang": "en", "tld": "co.uk", "slow": False}
        }
    
    def _get_sample_rate(self, filepath):
        """Detect the sample rate of an audio file using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'stream=sample_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(filepath)
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
            return 24000  # Default fallback
        except Exception as e:
            print(f"Error detecting sample rate: {e}")
            return 24000  # Default fallback
    
    def _apply_pitch_shift(self, filepath, pitch_factor=0.80, tempo_factor=1.15):
        """
        Apply pitch shifting and tempo adjustment to an audio file using ffmpeg.
        pitch_factor < 1.0 lowers the pitch (more masculine)
        pitch_factor > 1.0 raises the pitch (more feminine)
        tempo_factor > 1.0 speeds up playback, < 1.0 slows it down
        """
        try:
            temp_output = filepath.with_suffix('.pitched.mp3')
            
            # Detect the actual sample rate of the input file
            sample_rate = self._get_sample_rate(filepath)
            print(f"Detected sample rate: {sample_rate} Hz")
            
            # Use ffmpeg to shift pitch and adjust tempo
            # asetrate changes the sample rate (lower = deeper pitch)
            # atempo adjusts playback speed without affecting pitch
            # aresample maintains the original sample rate
            cmd = [
                'ffmpeg',
                '-i', str(filepath),
                '-af', f'asetrate={sample_rate}*{pitch_factor},atempo={tempo_factor},aresample={sample_rate}',
                '-y',  # Overwrite output file
                str(temp_output)
            ]
            
            # Run ffmpeg with suppressed output
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0 and temp_output.exists():
                # Replace original with pitched version
                temp_output.replace(filepath)
                print(f"Applied pitch shift (factor={pitch_factor}) to {filepath.name}")
                return True
            else:
                print(f"ffmpeg pitch shift failed for {filepath.name}")
                if temp_output.exists():
                    temp_output.unlink()
                return False
                
        except Exception as e:
            print(f"Error applying pitch shift to {filepath.name}: {e}")
            return False
    
    def _get_audio_filename(self, text, speaker_id):
        """Generate a unique filename based on text and speaker."""
        text_hash = hashlib.md5(f"{speaker_id}:{text}".encode()).hexdigest()
        return f"{text_hash}.mp3"
    
    def _generate_audio_file(self, text, speaker_id):
        """Generate audio file for the given text and speaker."""
        filename = self._get_audio_filename(text, speaker_id)
        filepath = self.audio_dir / filename
        
        # Skip if already exists and is non-empty
        if filepath.exists() and filepath.stat().st_size > 0:
            return filename
        
        try:
            # Get voice config for speaker
            voice_config = self.voice_configs.get(speaker_id, self.voice_configs["speaker1"])
            
            # Clean text for better TTS
            clean_text = text.strip()
            if not clean_text:
                return None
            
            # Generate speech
            tts = gTTS(
                text=clean_text,
                lang=voice_config["lang"],
                tld=voice_config["tld"],
                slow=voice_config["slow"]
            )
            
            # Save to file
            temp_filepath = filepath.with_suffix('.tmp.mp3')
            tts.save(str(temp_filepath))
            
            # Verify file was created and has content
            if temp_filepath.exists() and temp_filepath.stat().st_size > 0:
                temp_filepath.rename(filepath)
                #print(f"Generated audio: {filename} ({filepath.stat().st_size} bytes)")
                
                # Apply pitch shift for speaker2 to make voice more masculine and faster
                if speaker_id == "speaker2":
                    self._apply_pitch_shift(filepath, pitch_factor=0.75, tempo_factor=1.5)
                
                return filename
            else:
                print(f"Error: Generated empty audio file for: {text[:50]}...")
                if temp_filepath.exists():
                    temp_filepath.unlink()
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

# Global TTS service instance
tts_service = TTSService()
