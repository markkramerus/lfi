# Text-to-Speech Feature

## Overview

This application now includes text-to-speech (TTS) functionality that converts the two-person conversation into spoken audio. Each message is rendered both as text in speech bubbles and spoken aloud with different voices for each speaker.

## Implementation

### Technology Stack
- **gTTS (Google Text-to-Speech)**: Simple, reliable TTS engine that works without complex dependencies
- **pydub**: Audio processing library (for future enhancements)
- **Flask**: Serves audio files and manages the TTS service

### Architecture

#### 1. TTS Service (`tts_service.py`)
- **Singleton Pattern**: Global `tts_service` instance handles all audio generation
- **Voice Differentiation**: Two distinct voices using different TTS accents:
  - Speaker 1 (Initiating Agent): US English (en-com)
  - Speaker 2 (Other Agent): UK English (en-co.uk)
- **Caching**: Audio files are cached based on content hash to avoid regenerating the same speech
- **Async Processing**: Background thread processes audio generation queue

#### 2. Flask Integration (`app.py`)
- Automatically generates audio URLs for each message
- Identifies speakers based on agent IDs
- Serves audio files from `static/audio/` directory

#### 3. Frontend (`templates/index.html`)
- HTML5 audio players embedded in each speech bubble
- Auto-play for new messages (with fallback for browser restrictions)
- Synchronized text and audio display

#### 4. Styling (`static/style.css`)
- Audio player controls integrated into speech bubbles
- Responsive design maintaining visual hierarchy

## Features

### Current Features
✅ Two distinct voices for different speakers
✅ Text appears simultaneously with audio generation
✅ Audio playback controls (play, pause, seek)
✅ Cached audio files for efficiency
✅ Automatic audio generation for new messages
✅ Audio players embedded in speech bubbles

### How It Works

1. **Message Processing**: When a conversation message is created in `main.py`, it's sent to the Flask app with agent identification
2. **Audio Generation**: The TTS service:
   - Checks if audio already exists (based on content hash)
   - Generates audio using appropriate voice for the speaker
   - Saves MP3 file to `static/audio/` directory
   - Returns audio URL
3. **Frontend Rendering**: The browser:
   - Displays the text message in a speech bubble
   - Embeds an audio player with the generated audio
   - Optionally auto-plays new messages

### Voice Configuration

Voices can be customized in `tts_service.py`:

```python
self.voice_configs = {
    "speaker1": {"lang": "en", "tld": "com", "slow": False},  # US English
    "speaker2": {"lang": "en", "tld": "co.uk", "slow": False}  # UK English
}
```

Available TLD options for English:
- `com` - US English
- `co.uk` - UK English
- `com.au` - Australian English
- `co.in` - Indian English
- `ca` - Canadian English

## Usage

1. **Run the application normally**: `python main.py <scenario_name>`
2. **Audio files are automatically generated** as the conversation progresses
3. **Click play** on any audio player to hear that message
4. **Audio files are cached** in `static/audio/` directory

## File Structure

```
├── tts_service.py           # TTS service implementation
├── app.py                   # Flask app with TTS integration
├── main.py                  # Updated to pass speaker information
├── requirements.txt         # Updated with TTS dependencies
├── static/
│   ├── audio/              # Generated audio files (cached)
│   │   └── .gitkeep        # Keeps directory in git
│   └── style.css           # Updated with audio player styles
└── templates/
    └── index.html          # Updated with audio players
```

## Future Enhancements

Potential improvements for more advanced TTS:
- **Voice Cloning**: Integrate XTTS-v2 for realistic voice cloning (requires C++ build tools)
- **Real-time Streaming**: Stream audio as it's generated
- **Voice Customization**: Allow users to select different voices
- **Emotion/Tone**: Adjust voice characteristics based on message sentiment
- **Background Music**: Add ambient sound during conversations
- **Export Options**: Export entire conversation as audio file

## Troubleshooting

### Audio Not Playing
- Check browser console for errors
- Verify audio files are being generated in `static/audio/`
- Some browsers block auto-play - user interaction may be required

### No Voice Differentiation
- Verify speaker IDs are being passed correctly from `main.py`
- Check TTS service logs for voice configuration errors

### Performance Issues
- Audio generation happens asynchronously
- First-time generation may have slight delay
- Subsequent plays use cached audio files

## Dependencies

```
gtts>=2.5.0          # Google Text-to-Speech
pydub>=0.25.1        # Audio processing
```

Install with: `pip install gtts pydub`

## Notes

- Audio files are cached indefinitely - you may want to clean `static/audio/` periodically
- gTTS requires internet connection for audio generation
- Audio quality is suitable for demonstration purposes
- For production use, consider offline TTS solutions or voice cloning with XTTS-v2
