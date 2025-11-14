"""Synthesizes speech from the input string of text or ssml.
Make sure to be working in a virtual environment.

Note: ssml must be well-formed according to:
    https://www.w3.org/TR/speech-synthesis/
"""
from google.cloud import texttospeech

# Instantiates a client
client = texttospeech.TextToSpeechClient()

# Set the text input to be synthesized
text = """
You are a prior authorization specialist. You always begin by understanding the relevant medical policy so it can guide your conversation with patients and providers. Review requests carefully against the official medical policy, asking for clarification on any ambiguities. Begin by understanding what policies apply to the situation and request all necessary documentation, clarifying as needed. Be thorough in documenting all details - even minor ones. You tend to interpret requirements strictly and often request additional documentation to ensure complete compliance. While you can approve cases that meet criteria, you prefer to have every detail clearly documented but you happily accept any format of documentation.
"""
synthesis_input = texttospeech.SynthesisInput(text=text)

# Build the voice request, select the language code ("en-US") and the ssml
# voice gender ("neutral")
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US", name = 'en-US-Chirp3-HD-Achird', ssml_gender=texttospeech.SsmlVoiceGender.MALE
)

# Select the type of audio file you want returned
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Perform the text-to-speech request on the text input with the selected
# voice parameters and audio file type
response = client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)

# The response's audio_content is binary.
with open("output.mp3", "wb") as out:
    # Write the response to the output file.
    out.write(response.audio_content)
    print('Audio content written to file "output.mp3"')