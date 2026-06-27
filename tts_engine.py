"""
tts_engine.py — AI Voice Assistant for Bank Kiosk

Supports 6 Indian languages:
  en (English)   — pyttsx3 offline  ✓
  ta (Tamil)     — gTTS online      ✓
  hi (Hindi)     — gTTS online      ✓
  te (Telugu)    — gTTS online      ✓
  kn (Kannada)   — gTTS online      ✓
  ml (Malayalam) — gTTS online      ✓

Speak calls are always non-blocking (background thread).
Falls back to English pyttsx3 if gTTS / internet fails.
"""

import os
import threading
import tempfile
import queue

# ─────────────────────────────────────────────────────────
# Voice script translations (key phrases in all languages)
# ─────────────────────────────────────────────────────────

VOICE_SCRIPTS = {
    "welcome": {
        "en": "Welcome to the AI Bank Form Filling Kiosk. Please select your language.",
        "ta": "AI வங்கி படிவ நிரப்பும் கியோஸ்க்கிற்கு வரவேற்கிறோம். உங்கள் மொழியை தேர்ந்தெடுக்கவும்.",
        "hi": "AI बैंक फॉर्म भरने के कियोस्क में आपका स्वागत है। कृपया अपनी भाषा चुनें।",
        "te": "AI బ్యాంక్ ఫారం పూరించే కియోస్క్‌కు స్వాగతం. దయచేసి మీ భాషను ఎంచుకోండి.",
        "kn": "AI ಬ್ಯಾಂಕ್ ಫಾರ್ಮ್ ಭರ್ತಿ ಕಿಯೋಸ್ಕ್‌ಗೆ ಸ್ವಾಗತ. ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.",
        "ml": "AI ബാങ്ക് ഫോം ഫില്ലിംഗ് കിയോസ്‌ക്കിലേക്ക് സ്വാഗതം. ദയവായി നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കുക.",
    },
    "language_selected": {
        "en": "English selected. Welcome! Please select the banking service you need.",
        "ta": "தமிழ் தேர்ந்தெடுக்கப்பட்டது. வரவேற்கிறோம்! தேவையான வங்கி சேவையை தேர்ந்தெடுக்கவும்.",
        "hi": "हिंदी चुनी गई। स्वागत है! कृपया आवश्यक बैंकिंग सेवा चुनें।",
        "te": "తెలుగు ఎంచుకోబడింది. స్వాగతం! అవసరమైన బ్యాంకింగ్ సేవను ఎంచుకోండి.",
        "kn": "ಕನ್ನಡ ಆಯ್ಕೆಯಾಗಿದೆ. ಸ್ವಾಗತ! ಬೇಕಾದ ಬ್ಯಾಂಕಿಂಗ್ ಸೇವೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.",
        "ml": "മലയാളം തിരഞ്ഞെടുത്തു. സ്വാഗതം! ആവശ്യമായ ബാങ്കിംഗ് സേവനം തിരഞ്ഞെടുക്കുക.",
    },
    "select_service": {
        "en": "Please select the banking service you require.",
        "ta": "தேவையான வங்கி சேவையை தேர்ந்தெடுக்கவும்.",
        "hi": "कृपया आवश्यक बैंकिंग सेवा चुनें।",
        "te": "దయచేసి అవసరమైన బ్యాంకింగ్ సేవను ఎంచుకోండి.",
        "kn": "ಬೇಕಾದ ಬ್ಯಾಂಕಿಂಗ್ ಸೇವೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.",
        "ml": "ആവശ്യമായ ബാങ്കിംഗ് സേവനം തിരഞ്ഞെടുക്കുക.",
    },
    "select_document": {
        "en": "Please select your document type and place it on the scanner.",
        "ta": "உங்கள் ஆவண வகையை தேர்ந்தெடுத்து ஸ்கேனரில் வைக்கவும்.",
        "hi": "कृपया अपना दस्तावेज़ प्रकार चुनें और स्कैनर पर रखें।",
        "te": "దయచేసి మీ పత్రం రకాన్ని ఎంచుకుని స్కానర్‌పై ఉంచండి.",
        "kn": "ನಿಮ್ಮ ದಾಖಲೆ ಪ್ರಕಾರ ಆಯ್ಕೆ ಮಾಡಿ ಮತ್ತು ಸ್ಕ್ಯಾನರ್‌ನಲ್ಲಿ ಇರಿಸಿ.",
        "ml": "നിങ്ങളുടെ രേഖ തരം തിരഞ്ഞെടുത്ത് സ്കാനറിൽ വയ്ക്കുക.",
    },
    "scanning": {
        "en": "Scanning your document. Please wait.",
        "ta": "உங்கள் ஆவணம் ஸ்கேன் செய்யப்படுகிறது. காத்திருக்கவும்.",
        "hi": "आपका दस्तावेज़ स्कैन हो रहा है। कृपया प्रतीक्षा करें।",
        "te": "మీ పత్రం స్కాన్ అవుతోంది. దయచేసి వేచి ఉండండి.",
        "kn": "ನಿಮ್ಮ ದಾಖಲೆ ಸ್ಕ್ಯಾನ್ ಆಗುತ್ತಿದೆ. ದಯವಿಟ್ಟು ಕಾಯಿರಿ.",
        "ml": "നിങ്ങളുടെ രേഖ സ്കാൻ ചെയ്യുന്നു. ദയവായി കാത്തിരിക്കുക.",
    },
    "scan_done": {
        "en": "Document scanned successfully. Please review the extracted information.",
        "ta": "ஆவணம் வெற்றிகரமாக ஸ்கேன் செய்யப்பட்டது. பிரித்தெடுக்கப்பட்ட தகவலை சரிபார்க்கவும்.",
        "hi": "दस्तावेज़ सफलतापूर्वक स्कैन हुआ। कृपया निकाली गई जानकारी की समीक्षा करें।",
        "te": "పత్రం విజయవంతంగా స్కాన్ అయింది. సేకరించిన సమాచారాన్ని సమీక్షించండి.",
        "kn": "ದಾಖಲೆ ಯಶಸ್ವಿಯಾಗಿ ಸ್ಕ್ಯಾನ್ ಆಗಿದೆ. ಹೊರತೆಗೆದ ಮಾಹಿತಿ ಪರಿಶೀಲಿಸಿ.",
        "ml": "രേഖ വിജയകരമായി സ്കാൻ ചെയ്തു. ലഭ്യമായ വിവരങ്ങൾ പരിശോധിക്കുക.",
    },
    "enter_missing": {
        "en": "Some information is missing. Please enter the required details using the keypad.",
        "ta": "சில தகவல்கள் காணவில்லை. விசைப்பலகை மூலம் தேவையான விவரங்களை உள்ளிடவும்.",
        "hi": "कुछ जानकारी नहीं मिली। कृपया कीपैड का उपयोग करके आवश्यक विवरण दर्ज करें।",
        "te": "కొంత సమాచారం లేదు. కీప్యాడ్ ఉపయోగించి అవసరమైన వివరాలు నమోదు చేయండి.",
        "kn": "ಕೆಲವು ಮಾಹಿತಿ ಇಲ್ಲ. ಕೀಪ್ಯಾಡ್ ಬಳಸಿ ಅಗತ್ಯ ವಿವರ ನಮೂದಿಸಿ.",
        "ml": "ചില വിവരങ്ങൾ ഇല്ല. കീപ്പാഡ് ഉപയോഗിച്ച് ആവശ്യമായ വിവരങ്ങൾ നൽകുക.",
    },
    "form_complete": {
        "en": "Your form is complete. Please confirm to print.",
        "ta": "உங்கள் படிவம் முடிந்தது. அச்சிட உறுதிப்படுத்தவும்.",
        "hi": "आपका फॉर्म पूरा हो गया। प्रिंट करने के लिए पुष्टि करें।",
        "te": "మీ ఫారం పూర్తయింది. ముద్రించడానికి నిర్ధారించండి.",
        "kn": "ನಿಮ್ಮ ಫಾರ್ಮ್ ಪೂರ್ಣಗೊಂಡಿದೆ. ಮುದ್ರಿಸಲು ದೃಢೀಕರಿಸಿ.",
        "ml": "നിങ്ങളുടെ ഫോം പൂർത്തിയായി. പ്രിന്റ് ചെയ്യാൻ സ്ഥിരീകരിക്കുക.",
    },
    "print_done": {
        "en": "Your form has been printed. Please collect it and submit at the counter. Thank you.",
        "ta": "உங்கள் படிவம் அச்சிடப்பட்டது. அதை சேகரித்து கவுண்டரில் சமர்ப்பிக்கவும். நன்றி.",
        "hi": "आपका फॉर्म प्रिंट हो गया। कृपया इसे लेकर काउंटर पर जमा करें। धन्यवाद।",
        "te": "మీ ఫారం ముద్రించబడింది. దానిని తీసుకొని కౌంటర్‌లో సమర్పించండి. ధన్యవాదాలు.",
        "kn": "ನಿಮ್ಮ ಫಾರ್ಮ್ ಮುದ್ರಿಸಲಾಗಿದೆ. ಅದನ್ನು ತೆಗೆದುಕೊಂಡು ಕೌಂಟರ್‌ನಲ್ಲಿ ಸಲ್ಲಿಸಿ. ಧನ್ಯವಾದ.",
        "ml": "നിങ്ങളുടെ ഫോം പ്രിന്റ് ചെയ്തു. അത് ശേഖരിച്ച് കൗണ്ടറിൽ സമർപ്പിക്കുക. നന്ദി.",
    },
    "error": {
        "en": "An error occurred. Please try again or ask for assistance.",
        "ta": "பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும் அல்லது உதவி கேளுங்கள்.",
        "hi": "एक त्रुटि हुई। कृपया पुनः प्रयास करें या सहायता मांगें।",
        "te": "ఒక లోపం సంభవించింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",
        "kn": "ದೋಷ ಸಂಭವಿಸಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "ml": "ഒരു പിശക് സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക.",
    },
}

# gTTS language codes
_GTTS_LANG_MAP = {
    "en": "en",
    "ta": "ta",
    "hi": "hi",
    "te": "te",
    "kn": "kn",
    "ml": "ml",
}

# Single background speech queue (prevents overlapping audio)
_speech_queue: queue.Queue = queue.Queue()
_tts_thread: threading.Thread = None
_tts_running = False


def _pyttsx3_speak(text: str):
    """Speak text using pyttsx3 (offline, English only)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.setProperty("volume", 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        print(f"[TTS] pyttsx3 error: {exc}")


def _gtts_speak(text: str, lang_code: str):
    """Speak text using gTTS (online, multi-language)."""
    tmp_path = None
    try:
        from gtts import gTTS
        from playsound import playsound

        gtts_lang = _GTTS_LANG_MAP.get(lang_code, "en")
        tts = gTTS(text=text, lang=gtts_lang, slow=False)

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()
        tts.save(tmp_path)

        playsound(tmp_path)

    except Exception as exc:
        print(f"[TTS] gTTS error: {exc}")
        # Fall back to pyttsx3 with English
        _pyttsx3_speak(text)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _worker():
    """Background thread that processes the speech queue."""
    global _tts_running
    _tts_running = True
    while _tts_running:
        try:
            item = _speech_queue.get(timeout=0.5)
            if item is None:
                break
            text, lang_code = item
            if lang_code == "en":
                _pyttsx3_speak(text)
            else:
                _gtts_speak(text, lang_code)
            _speech_queue.task_done()
        except queue.Empty:
            continue
    _tts_running = False


def _ensure_worker():
    """Start TTS worker thread if not running."""
    global _tts_thread, _tts_running
    if _tts_thread is None or not _tts_thread.is_alive():
        _tts_running = True
        _tts_thread = threading.Thread(target=_worker, daemon=True)
        _tts_thread.start()


def speak(text: str, lang_code: str = "en"):
    """
    Speak *text* in the given language — non-blocking.

    Args:
        text      : The text to speak (already translated).
        lang_code : One of 'en', 'ta', 'hi', 'te', 'kn', 'ml'.
    """
    if not text:
        return
    _ensure_worker()
    # Clear queue to avoid backlog (latest speech wins)
    while not _speech_queue.empty():
        try:
            _speech_queue.get_nowait()
        except queue.Empty:
            break
    _speech_queue.put((text, lang_code))


def speak_script(key: str, lang_code: str = "en"):
    """
    Speak a predefined voice script by key.

    Falls back to English if the key/lang combo is not found.
    """
    scripts = VOICE_SCRIPTS.get(key, {})
    text = scripts.get(lang_code) or scripts.get("en", "")
    speak(text, lang_code)


def stop():
    """Stop the TTS worker cleanly."""
    global _tts_running
    _tts_running = False
    _speech_queue.put(None)
