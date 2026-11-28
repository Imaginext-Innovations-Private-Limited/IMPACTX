Optional consented, human-recorded warnings; NOT required for browser speech if a
matching speech voice exists. Put files in language subfolders, for example:
  static/voices/bn/high.webm
  static/voices/kn/caution.webm
  static/voices/or/no_clear_signal.webm
Supported extensions: .webm, .mp3, .m4a.
Record using http://127.0.0.1:8000/static/voice-studio.html
Browser warning language selection uses these clips first, otherwise a matching
speechSynthesis voice, otherwise a visible unavailability message.
Never include private submitted messages or credentials in voice clips.
Don't commit voice recordings without explicit speaker permission.

Automatic alternative in v1.2.1: run the optional Python voice generator (see docs/AUTOMATIC_VOICES.md) to create high.mp3 or
all risk levels for all languages. The script does not send user messages.
See docs/AUTOMATIC_VOICES.md. Generated MP3s are not included in the ZIP.
