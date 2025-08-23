"""
Comprehensive accessibility features manager for DataScope application.
Provides high contrast mode, large text, keyboard navigation, screen reader support,
and voice commands for enhanced accessibility.
"""

import flet as ft
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Try to import text-to-speech libraries
try:
    import pyttsx3
    TTS_AVAILABLE = True
    print("[Accessibility] Text-to-speech library available")
except ImportError:
    TTS_AVAILABLE = False
    print("[Accessibility] Text-to-speech library not available - install pyttsx3 for audio feedback")

# Try to import Windows SAPI for better screen reader integration
try:
    import win32com.client
    SAPI_AVAILABLE = True
    print("[Accessibility] Windows SAPI available for enhanced screen reader support")
except ImportError:
    SAPI_AVAILABLE = False
    print("[Accessibility] Windows SAPI not available - install pywin32 for enhanced screen reader support")

class AccessibilityManager:
    """Comprehensive accessibility features manager for DataScope application."""
    
    def __init__(self, page: ft.Page, preferences_dir: Path):
        self.page = page
        self.preferences_dir = preferences_dir
        self.settings_file = preferences_dir / "accessibility.json"
        
        # Accessibility states
        self.high_contrast = False
        self.large_text = False
        self.reduce_motion = False
        self.screen_reader_mode = False
        self.keyboard_navigation = True
        self.focus_indicators = True
        self.audio_feedback = False
        
        # Screen magnification features
        self.magnification_enabled = False
        self.magnification_level = 100  # Percentage (50% to 300%)
        self.min_magnification = 50
        self.max_magnification = 300
        self.magnification_step = 25
        self._last_magnification_level = 100  # For error recovery
        
        # Enhanced accessibility features
        self.color_blind_mode = "none"  # none, deuteranopia, protanopia, tritanopia
        self.tts_speed = 200  # words per minute
        self.tts_volume = 0.9  # 0.0 to 1.0
        self.show_shortcuts_overlay = False
        self.live_announcements = True
        self.focus_management = True
        self.error_prevention = True
        
        # Enhanced voice selection properties
        self.tts_voice_id = None  # Current selected voice ID
        self.tts_voice_gender = "female"  # "female", "male", or "any"
        self.tts_available_voices = []  # List of discovered voices
        self.voice_pitch = 0  # Voice pitch adjustment (-50 to +50)
        
        # Speech-to-text functionality
        self.speech_to_text_enabled = False  # Speech-to-text toggle state
        
        # Operation control
        self.operations_paused = False  # Global pause state for operations
        
        # NVDA-like behavior settings - fast and responsive
        self._last_announcement_time = 0
        self._announcement_queue = []
        self._debounce_delay = 0.15  # NVDA-like fast response (150ms)
        self._batch_timeout = 0.4   # Quick batching timeout
        self._announcement_lock = threading.Lock()
        self._nvda_mode = True  # Enable NVDA-like behavior
        
        # NVDA-style speech settings
        self.instant_speech = True  # Immediate speech without delays
        self.interrupt_speech = True  # Interrupt previous speech for new announcements
        self.priority_announcements = True  # Priority system like NVDA
        
        print("[Accessibility] NVDA-like mode enabled - fast, responsive speech")
        
        # Detect NVDA screen reader
        self._detect_nvda_screen_reader()
        
        # ADVANCED SCREEN READER IMPROVEMENTS - BETTER THAN NVDA
        # Smart batching and context awareness
        self.smart_batching = True  # Intelligent message batching
        self.context_aware = True   # Context-sensitive announcements
        self.user_verbosity_level = "normal"  # "minimal", "normal", "verbose"
        self.quiet_mode = False     # Suppress non-critical announcements
        
        # Advanced announcement tracking
        self._recent_announcements = []  # Track recent messages to avoid duplicates
        self._context_stack = []    # Track navigation context
        self._last_focus_context = ""  # Last focused element context
        
        # User customization settings
        self.announcement_settings = {
            "announce_tab_changes": True,
            "announce_data_loading": True,
            "announce_progress": True,
            "announce_errors": True,
            "announce_search_results": True,
            "announce_navigation": False,  # Reduced verbosity by default
            "batch_similar_messages": True,
            "interrupt_for_urgent": True,
            "use_context_hints": True,
        }
        
        # Smart message filtering
        self._message_filters = {
            "progress": {"last_announced": 0, "interval": 25},  # Only announce every 25%
            "navigation": {"suppress_rapid": True, "debounce": 0.3},
            "data_update": {"batch_similar": True, "max_frequency": 2.0},  # Max 2 per second
        }
        
        # Speech enhancement
        self.enhanced_speech = {
            "use_prosody": True,        # Vary pitch/rate for different message types
            "emphasize_errors": True,   # Higher pitch for errors
            "softer_progress": True,    # Lower volume for progress updates
            "quick_confirmations": True, # Fast speech for confirmations
        }
        
        print("[Accessibility] Advanced screen reader features enabled - optimized for DataScope workflow")
        
        # Detect NVDA screen reader
        self._detect_nvda_screen_reader()
        
        # Tab system reference
        self.tabs_control = None
        
        # Initialize text-to-speech engine
        self.tts_engine = None
        self.sapi_voice = None
        self._init_tts()
        
        # Keyboard shortcuts
        self.shortcuts = {
            "ctrl+h": self._toggle_high_contrast,
            "ctrl+shift+l": self._toggle_large_text,
            "ctrl+shift+m": self._toggle_reduce_motion,
            "ctrl+shift+s": self._toggle_screen_reader_mode,
            "alt+1": lambda: self._focus_tab(0),  # Console
            "alt+2": lambda: self._focus_tab(1),  # Data View
            "alt+3": lambda: self._focus_tab(2),  # Data Tools
            "alt+4": lambda: self._focus_tab(3),  # Advanced
            "alt+5": lambda: self._focus_tab(4),  # Settings
            "f1": self._show_help,
            "ctrl+slash": self._show_shortcuts,
            "ctrl+shift+t": self._test_accessibility,  # New: Test accessibility
            "ctrl+shift+o": self._toggle_shortcuts_overlay,  # New: Toggle overlay
            "ctrl+shift+c": self._cycle_color_blind_mode,  # New: Color blind support
            "ctrl+shift+up": self._increase_tts_speed,  # New: Increase TTS speed
            "ctrl+shift+down": self._decrease_tts_speed,  # New: Decrease TTS speed
            "ctrl+shift+right": self._increase_tts_volume,  # New: Increase TTS volume
            "ctrl+shift+left": self._decrease_tts_volume,  # New: Decrease TTS volume
            "ctrl+shift+v": self.cycle_voice_gender,  # New: Cycle voice gender
            "ctrl+shift+g": self.test_current_voice,  # New: Test current voice
            "ctrl+shift+f": self._focus_summary,  # New: Focus summary
            "ctrl+shift+n": self._table_cell_navigation_mode,  # New: Table navigation
            "ctrl+equal": self._increase_magnification,  # New: Increase magnification (Ctrl+=)
            "ctrl+plus": self._increase_magnification,  # New: Increase magnification (Ctrl++)
            "ctrl+minus": self._decrease_magnification,  # New: Decrease magnification (Ctrl+-)
            "ctrl+digit_0": self._reset_magnification,  # New: Reset magnification (Ctrl+0)
            "ctrl+shift+r": self._run_accessibility_audit,  # New: Accessibility audit
            "ctrl+shift+d": self.demo_accessibility_features,  # New: Demo all features
            "ctrl+shift+p": self._toggle_pause_operations,  # New: Pause/Resume operations
            # Advanced screen reader shortcuts
            "ctrl+shift+q": self.toggle_quiet_mode,  # New: Toggle quiet mode
            "ctrl+shift+1": lambda: self.set_verbosity_level("minimal"),  # New: Minimal verbosity
            "ctrl+shift+2": lambda: self.set_verbosity_level("normal"),   # New: Normal verbosity
            "ctrl+shift+3": lambda: self.set_verbosity_level("verbose"),  # New: Verbose verbosity
            "ctrl+shift+b": self._process_announcement_batch,  # New: Force process batch
            "ctrl+shift+e": lambda: self.announce_with_prosody("Testing emotional speech", "success"),  # New: Test prosody
            "ctrl+shift+y": self._toggle_speech_to_text,  # New: Toggle speech-to-text
        }
        
        # Advanced accessibility features
        self.table_navigation_mode = False
        self.current_cell_position = {"row": 0, "col": 0}
        self.custom_shortcuts = {}  # User-defined shortcuts
        self.audit_mode = False
        
        # Live region for screen reader announcements
        self.live_region = None
        self._setup_live_region()
        
        # Load saved preferences
        self._load_preferences()
        
        # Note: Keyboard handler is setup by main UI to avoid conflicts
        # The main UI will call our shortcuts directly
        
        print(f"[Accessibility] Manager initialized with settings from {self.settings_file}")

    def _setup_live_region(self):
        """Setup invisible live region for screen reader announcements."""
        self.live_region = ft.Text(
            value="",
            visible=False,
            size=1,
            tooltip="Live region for accessibility announcements"
        )
        
    def get_live_region(self):
        """Get the live region control to be added to the page."""
        return self.live_region

    def _init_tts(self):
        """Initialize text-to-speech engines with enhanced voice configuration."""
        try:
            # Try to initialize pyttsx3 first
            if TTS_AVAILABLE:
                self.tts_engine = pyttsx3.init()
                
                # Configure TTS settings with user preferences
                self.tts_engine.setProperty('rate', self.tts_speed)
                self.tts_engine.setProperty('volume', self.tts_volume)
                
                # Discover and categorize available voices
                self._discover_voices()
                
                # Set the best voice based on preferences
                self._set_optimal_voice()
                
                print(f"[Accessibility] pyttsx3 TTS engine initialized (rate: {self.tts_speed}, volume: {self.tts_volume})")
                print(f"[Accessibility] Found {len(self.tts_available_voices)} voices")
            
            # Try to initialize Windows SAPI for better screen reader integration
            if SAPI_AVAILABLE:
                try:
                    self.sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                    print("[Accessibility] Windows SAPI voice initialized")
                except Exception as e:
                    print(f"[Accessibility] Failed to initialize SAPI: {e}")
                    
        except Exception as e:
            print(f"[Accessibility] Failed to initialize TTS: {e}")
            self.tts_engine = None

    def _discover_voices(self):
        """Discover and categorize available TTS voices."""
        self.tts_available_voices = []
        
        if not self.tts_engine:
            return
            
        try:
            voices = self.tts_engine.getProperty('voices')
            if not voices:
                return
                
            for voice in voices:
                # Extract voice information
                voice_info = {
                    'id': voice.id,
                    'name': voice.name,
                    'gender': self._detect_voice_gender(voice.name),
                    'language': getattr(voice, 'languages', ['en']) if hasattr(voice, 'languages') else ['en'],
                    'quality': self._assess_voice_quality(voice.name),
                    'is_neural': 'neural' in voice.name.lower() or 'cortana' in voice.name.lower(),
                    'is_human_like': self._is_human_like_voice(voice.name)
                }
                
                self.tts_available_voices.append(voice_info)
                print(f"[Accessibility] Found voice: {voice_info['name']} ({voice_info['gender']}, Quality: {voice_info['quality']})")
                
            # Sort voices by quality and human-likeness
            self.tts_available_voices.sort(key=lambda v: (
                v['is_human_like'],
                v['is_neural'], 
                v['quality'] == 'high',
                v['gender'] == self.tts_voice_gender
            ), reverse=True)
            
        except Exception as e:
            print(f"[Accessibility] Error discovering voices: {e}")

    def _detect_voice_gender(self, voice_name: str) -> str:
        """Detect voice gender from voice name."""
        name_lower = voice_name.lower()
        
        # Common female voice indicators
        female_indicators = [
            'female', 'zira', 'hazel', 'susan', 'helen', 'aria', 'jenny', 
            'jane', 'mary', 'anna', 'emma', 'eva', 'cortana', 'sophia',
            'samantha', 'victoria', 'voice female', 'woman', 'lady'
        ]
        
        # Common male voice indicators  
        male_indicators = [
            'male', 'david', 'mark', 'james', 'richard', 'michael', 'voice male',
            'man', 'guy', 'ryan', 'brian', 'jacob', 'william', 'benjamin'
        ]
        
        for indicator in female_indicators:
            if indicator in name_lower:
                return 'female'
                
        for indicator in male_indicators:
            if indicator in name_lower:
                return 'male'
                
        return 'unknown'

    def _assess_voice_quality(self, voice_name: str) -> str:
        """Assess voice quality based on voice name indicators."""
        name_lower = voice_name.lower()
        
        # High quality indicators
        if any(indicator in name_lower for indicator in [
            'neural', 'premium', 'hd', 'enhanced', 'natural', 'cortana', 
            'aria', 'jenny', 'guy', 'professional', 'studio'
        ]):
            return 'high'
            
        # Medium quality indicators
        if any(indicator in name_lower for indicator in [
            'standard', 'clear', 'improved', 'plus'
        ]):
            return 'medium'
            
        return 'low'

    def _is_human_like_voice(self, voice_name: str) -> bool:
        """Determine if a voice is more human-like."""
        name_lower = voice_name.lower()
        
        # Human-like voice indicators
        human_indicators = [
            'neural', 'natural', 'cortana', 'aria', 'jenny', 'guy',
            'premium', 'enhanced', 'professional', 'studio', 'expressive'
        ]
        
        return any(indicator in name_lower for indicator in human_indicators)

    def _set_optimal_voice(self):
        """Set the best available voice based on user preferences."""
        if not self.tts_available_voices:
            return
            
        # If user has a saved voice preference and we're not cycling genders, try to use it
        if self.tts_voice_id:
            for voice in self.tts_available_voices:
                if voice['id'] == self.tts_voice_id:
                    # Check if this voice matches the current gender preference
                    if (self.tts_voice_gender == "any" or 
                        voice['gender'] == self.tts_voice_gender or 
                        voice['gender'] == 'unknown'):
                        self.tts_engine.setProperty('voice', voice['id'])
                        print(f"[Accessibility] Using saved voice: {voice['name']}")
                        return
        
        # Find the best voice based on preferences
        if self.tts_voice_gender == "any":
            # For "any", prefer voices in this order: female, male, unknown
            preferred_voices = self.tts_available_voices
        else:
            # Find voices of the preferred gender
            preferred_voices = [
                v for v in self.tts_available_voices 
                if v['gender'] == self.tts_voice_gender
            ]
            
            # If no voices of preferred gender, fall back to any
            if not preferred_voices:
                preferred_voices = self.tts_available_voices
        
        if preferred_voices:
            best_voice = preferred_voices[0]  # Already sorted by quality
            self.tts_voice_id = best_voice['id']
            self.tts_engine.setProperty('voice', best_voice['id'])
            
            # Also update SAPI voice if available
            if self.sapi_voice:
                self._set_sapi_voice(best_voice)
            
            print(f"[Accessibility] Selected optimal voice: {best_voice['name']} ({best_voice['gender']}, {best_voice['quality']})")
        else:
            # Fallback to first available voice
            best_voice = self.tts_available_voices[0]
            self.tts_voice_id = best_voice['id']
            self.tts_engine.setProperty('voice', best_voice['id'])
            
            # Also update SAPI voice if available
            if self.sapi_voice:
                self._set_sapi_voice(best_voice)
            
            print(f"[Accessibility] Using fallback voice: {best_voice['name']}")

    def get_voice_by_id(self, voice_id: str):
        """Get voice information by ID."""
        return next((v for v in self.tts_available_voices if v['id'] == voice_id), None)

    def set_voice(self, voice_id: str):
        """Set the current voice by ID."""
        if not self.tts_engine:
            print("[Accessibility] No TTS engine available")
            return False
            
        voice_info = self.get_voice_by_id(voice_id)
        if not voice_info:
            print(f"[Accessibility] Voice ID not found: {voice_id}")
            return False
            
        try:
            # Set pyttsx3 voice
            print(f"[Accessibility] Setting pyttsx3 voice to: {voice_info['name']}")
            self.tts_engine.setProperty('voice', voice_id)
            
            # Also set SAPI voice if available
            if self.sapi_voice:
                self._set_sapi_voice(voice_info)
            
            # Update our stored voice ID
            self.tts_voice_id = voice_id
            self._save_preferences()
            
            print(f"[Accessibility] Voice successfully changed to: {voice_info['name']} ({voice_info['gender']})")
            return True
            
        except Exception as e:
            print(f"[Accessibility] Error setting voice: {e}")
            return False

    def get_voices_by_gender(self, gender: str):
        """Get all voices of a specific gender."""
        return [v for v in self.tts_available_voices if v['gender'] == gender]

    def get_human_like_voices(self):
        """Get all human-like voices."""
        return [v for v in self.tts_available_voices if v['is_human_like']]

    def cycle_voice_gender(self):
        """Cycle through voice gender preferences."""
        genders = ["female", "male", "any"]
        current_index = genders.index(self.tts_voice_gender)
        self.tts_voice_gender = genders[(current_index + 1) % len(genders)]
        
        # Clear the saved voice ID so we can find a new voice of the desired gender
        self.tts_voice_id = None
        
        # Automatically switch to the best voice of the new gender
        self._set_optimal_voice()
        self._save_preferences()
        
        current_voice = self.get_voice_by_id(self.tts_voice_id)
        voice_name = current_voice['name'] if current_voice else "Unknown"
        self._speak_text(f"Voice gender preference: {self.tts_voice_gender}. Now using {voice_name}", priority="test")

    def test_current_voice(self):
        """Test the current voice with a sample message."""
        current_voice = self.get_voice_by_id(self.tts_voice_id)
        if current_voice:
            test_message = f"Hello! This is {current_voice['name']}, a {current_voice['quality']} quality {current_voice['gender']} voice. How do I sound?"
            self._speak_text(test_message, priority="test")
        else:
            self._speak_text("Voice test: Current voice information not available.", priority="test")

    def _speak_text(self, text: str, priority: str = "normal"):
        """Speak text using available TTS engines."""
        # Check if operations are paused - if so, don't speak unless it's urgent priority
        if self.operations_paused and priority != "urgent":
            print(f"[Accessibility] TTS blocked - operations paused: {text}")
            return
            
        # Allow speaking if any TTS mode is enabled OR if we're testing voices OR urgent priority
        speak_enabled = (self.audio_feedback or self.screen_reader_mode or 
                        "Voice changed" in text or "test" in text.lower() or 
                        priority in ["test", "urgent"])
        
        if not speak_enabled:
            print(f"[Accessibility] TTS disabled - screen_reader_mode: {self.screen_reader_mode}, audio_feedback: {self.audio_feedback}")
            return
            
        # Use threading to prevent blocking the UI
        def speak_async():
            try:
                # Get current voice info for debugging
                current_voice = self.get_voice_by_id(self.tts_voice_id)
                voice_name = current_voice['name'] if current_voice else 'Unknown'
                
                if self.screen_reader_mode and self.sapi_voice:
                    # Use SAPI for screen reader mode (better integration)
                    print(f"[Accessibility] SAPI speaking with voice: {voice_name}")
                    # Try to set SAPI voice to match our selection
                    if current_voice:
                        self._set_sapi_voice(current_voice)
                    self.sapi_voice.Speak(text, 1)  # Async flag = 1
                    print(f"[Accessibility] SAPI spoke: {text}")
                    
                elif (self.audio_feedback or priority == "test") and self.tts_engine:
                    # Use pyttsx3 for audio feedback or testing
                    print(f"[Accessibility] pyttsx3 speaking with voice: {voice_name}")
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                    print(f"[Accessibility] TTS spoke: {text}")
                    
                else:
                    print(f"[Accessibility] No appropriate TTS mode active for: {text}")
                    
            except Exception as e:
                print(f"[Accessibility] TTS error: {e}")
        
        # Run TTS in background thread
        if self.tts_engine or self.sapi_voice:
            threading.Thread(target=speak_async, daemon=True).start()

    def _set_sapi_voice(self, voice_info):
        """Set SAPI voice to match the selected voice."""
        try:
            if not self.sapi_voice:
                return
                
            # Get available SAPI voices
            sapi_voices = self.sapi_voice.GetVoices()
            
            # Try to find a matching voice by name
            for i in range(sapi_voices.Count):
                sapi_voice = sapi_voices.Item(i)
                if voice_info['name'] in sapi_voice.GetDescription():
                    self.sapi_voice.Voice = sapi_voice
                    print(f"[Accessibility] SAPI voice set to: {sapi_voice.GetDescription()}")
                    return
                    
            print(f"[Accessibility] Could not find matching SAPI voice for: {voice_info['name']}")
            
        except Exception as e:
            print(f"[Accessibility] Error setting SAPI voice: {e}")

    def _update_tts_settings(self):
        """Update TTS engine settings based on user preferences."""
        try:
            if self.tts_engine:
                # Update pyttsx3 settings
                self.tts_engine.setProperty('rate', self.tts_speed)
                self.tts_engine.setProperty('volume', self.tts_volume)
                
                # Update voice if tts_voice_id is set
                if self.tts_voice_id:
                    self.tts_engine.setProperty('voice', self.tts_voice_id)
                
                print(f"[Accessibility] Updated TTS: speed={self.tts_speed}, volume={self.tts_volume}")
                
            if self.sapi_voice:
                # Update SAPI settings
                self.sapi_voice.Rate = max(-10, min(10, (self.tts_speed - 200) // 10))  # Convert to SAPI range
                self.sapi_voice.Volume = int(self.tts_volume * 100)
                
                # Set voice pitch if supported
                if hasattr(self.sapi_voice, 'Voice') and hasattr(self.sapi_voice.Voice, 'SetPitch'):
                    try:
                        self.sapi_voice.Voice.SetPitch(self.voice_pitch)
                    except:
                        pass  # Some voices don't support pitch control
                
                print(f"[Accessibility] Updated SAPI: rate={self.sapi_voice.Rate}, volume={self.sapi_voice.Volume}, pitch={self.voice_pitch}")
                
        except Exception as e:
            print(f"[Accessibility] Error updating TTS settings: {e}")

    def _setup_keyboard_handler(self):
        """Setup global keyboard event handler for accessibility shortcuts."""
        original_handler = getattr(self.page, 'on_keyboard_event', None)
        
        async def accessibility_keyboard_handler(e: ft.KeyboardEvent):
            # Build key combination string
            key_combo = ""
            if e.ctrl:
                key_combo += "ctrl+"
            if e.shift:
                key_combo += "shift+"
            if e.alt:
                key_combo += "alt+"
            key_combo += e.key.lower()
            
            # Check for accessibility shortcuts
            if key_combo in self.shortcuts:
                try:
                    # Execute the shortcut
                    result = self.shortcuts[key_combo]()
                    if hasattr(result, '__await__'):
                        await result
                    return
                except Exception as ex:
                    print(f"[Accessibility] Shortcut error for {key_combo}: {ex}")
            
            # Call original handler if it exists
            if original_handler:
                await original_handler(e)
        
        self.page.on_keyboard_event = accessibility_keyboard_handler

    def _load_preferences(self):
        """Load accessibility preferences from disk."""
        if self.settings_file.exists():
            try:
                with self.settings_file.open("r") as f:
                    data = json.load(f)
                
                self.high_contrast = data.get("high_contrast", False)
                self.large_text = data.get("large_text", False)
                self.reduce_motion = data.get("reduce_motion", False)
                self.screen_reader_mode = data.get("screen_reader_mode", False)
                self.keyboard_navigation = data.get("keyboard_navigation", True)
                self.focus_indicators = data.get("focus_indicators", True)
                self.audio_feedback = data.get("audio_feedback", False)
                
                # Enhanced accessibility features
                self.color_blind_mode = data.get("color_blind_mode", "none")
                self.tts_speed = data.get("tts_speed", 200)
                self.tts_volume = data.get("tts_volume", 0.8)
                self.live_announcements = data.get("live_announcements", True)
                self.focus_management = data.get("focus_management", True)
                self.error_prevention = data.get("error_prevention", True)
                
                # Enhanced voice settings
                self.tts_voice_id = data.get("tts_voice_id", None)
                self.tts_voice_gender = data.get("tts_voice_gender", "female")
                self.voice_pitch = data.get("voice_pitch", 0)
                
                # Magnification settings
                self.magnification_enabled = data.get("magnification_enabled", False)
                self.magnification_level = data.get("magnification_level", 100)
                self._last_magnification_level = data.get("_last_magnification_level", 100)
                
                # Speech-to-text settings
                self.speech_to_text_enabled = data.get("speech_to_text_enabled", False)
                
                # Operation control
                self.operations_paused = data.get("operations_paused", False)
                
                print(f"[Accessibility] Loaded enhanced preferences: HC={self.high_contrast}, LT={self.large_text}, CBM={self.color_blind_mode}")
                print(f"[Accessibility] Voice preferences: gender={self.tts_voice_gender}, pitch={self.voice_pitch}")
                print(f"[Accessibility] Magnification: enabled={self.magnification_enabled}, level={self.magnification_level}%")
                print(f"[Accessibility] TTS modes: screen_reader={self.screen_reader_mode}, audio_feedback={self.audio_feedback}")
                print(f"[Accessibility] Operations paused: {self.operations_paused}")
                
                # Apply TTS settings after loading
                self._update_tts_settings()
                
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"[Accessibility] Failed to load preferences: {e}")

    def _save_preferences(self):
        """Save accessibility preferences to disk."""
        try:
            self.preferences_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                "high_contrast": self.high_contrast,
                "large_text": self.large_text,
                "reduce_motion": self.reduce_motion,
                "screen_reader_mode": self.screen_reader_mode,
                "keyboard_navigation": self.keyboard_navigation,
                "focus_indicators": self.focus_indicators,
                "audio_feedback": self.audio_feedback,
                
                # Enhanced accessibility features
                "color_blind_mode": self.color_blind_mode,
                "tts_speed": self.tts_speed,
                "tts_volume": self.tts_volume,
                "live_announcements": self.live_announcements,
                "focus_management": self.focus_management,
                "error_prevention": self.error_prevention,
                
                # Enhanced voice settings
                "tts_voice_id": self.tts_voice_id,
                "tts_voice_gender": self.tts_voice_gender,
                "voice_pitch": self.voice_pitch,
                
                # Magnification settings
                "magnification_enabled": self.magnification_enabled,
                "magnification_level": self.magnification_level,
                "_last_magnification_level": self._last_magnification_level,
                
                # Speech-to-text settings
                "speech_to_text_enabled": self.speech_to_text_enabled,
                
                # Operation control
                "operations_paused": self.operations_paused,
            }
            
            with self.settings_file.open("w") as f:
                json.dump(data, f, indent=2)
                
            print(f"[Accessibility] Saved enhanced preferences to {self.settings_file}")
            
        except Exception as e:
            print(f"[Accessibility] Failed to save preferences: {e}")

    def apply_high_contrast(self):
        """Apply high contrast color scheme."""
        if self.high_contrast:
            # High contrast dark theme
            if hasattr(self.page, '_dark_mode_active') and self.page._dark_mode_active:
                self.page.dark_theme = ft.Theme(
                    color_scheme=ft.ColorScheme(
                        primary="#FFFF00",  # Bright yellow
                        secondary="#00FFFF",  # Bright cyan
                        surface="#000000",  # Pure black
                        background="#000000",  # Pure black
                        error="#FF0000",  # Bright red
                        on_primary="#000000",  # Black text on yellow
                        on_secondary="#000000",  # Black text on cyan
                        on_surface="#FFFFFF",  # White text on black
                        on_background="#FFFFFF",  # White text on black
                        outline="#FFFFFF",  # White borders
                    )
                )
            else:
                # High contrast light theme
                self.page.theme = ft.Theme(
                    color_scheme=ft.ColorScheme(
                        primary="#000000",  # Pure black
                        secondary="#0000FF",  # Bright blue
                        surface="#FFFFFF",  # Pure white
                        background="#FFFFFF",  # Pure white
                        error="#FF0000",  # Bright red
                        on_primary="#FFFFFF",  # White text on black
                        on_secondary="#FFFFFF",  # White text on blue
                        on_surface="#000000",  # Black text on white
                        on_background="#000000",  # Black text on white
                        outline="#000000",  # Black borders
                    )
                )
            print(f"[Accessibility] Applied high contrast theme")
        else:
            # Restore normal theme (handled by main theme system)
            self._restore_normal_theme()

    def _restore_normal_theme(self):
        """Restore normal theme colors."""
        # Use the main app's theme restoration logic
        if hasattr(self.page, '_dark_mode_active') and self.page._dark_mode_active:
            dark_seed = "#1E90FF"  # Tech Blue for Dark Theme
            self.page.dark_theme = ft.Theme(color_scheme_seed=dark_seed)
        else:
            light_seed = "#00FF7F"  # Tech Green for Light Theme
            self.page.theme = ft.Theme(color_scheme_seed=light_seed)

    def apply_large_text(self):
        """Apply large text scaling."""
        if self.large_text:
            # Increase text scaling
            if self.page.theme:
                self.page.theme.text_theme = ft.TextTheme(
                    body_large=ft.TextStyle(size=18),
                    body_medium=ft.TextStyle(size=16),
                    body_small=ft.TextStyle(size=14),
                    label_large=ft.TextStyle(size=16),
                    label_medium=ft.TextStyle(size=14),
                    label_small=ft.TextStyle(size=12),
                )
            if self.page.dark_theme:
                self.page.dark_theme.text_theme = ft.TextTheme(
                    body_large=ft.TextStyle(size=18),
                    body_medium=ft.TextStyle(size=16),
                    body_small=ft.TextStyle(size=14),
                    label_large=ft.TextStyle(size=16),
                    label_medium=ft.TextStyle(size=14),
                    label_small=ft.TextStyle(size=12),
                )
            print(f"[Accessibility] Applied large text scaling")

    def apply_focus_indicators(self):
        """Apply enhanced focus indicators for keyboard navigation."""
        if self.focus_indicators:
            # This would be applied to individual controls
            # Implementation depends on specific control styling
            print(f"[Accessibility] Enhanced focus indicators enabled")

    def _toggle_high_contrast(self):
        """Toggle high contrast mode."""
        print(f"[Accessibility] Toggling high contrast from {self.high_contrast} to {not self.high_contrast}")
        self.high_contrast = not self.high_contrast
        self.apply_high_contrast()
        self._save_preferences()
        
        # Update page immediately
        self.page.update()
        
        # Announce change in background to avoid blocking
        message = f"High contrast {'enabled' if self.high_contrast else 'disabled'}"
        threading.Thread(target=lambda: self._announce_change(message), daemon=True).start()

    def _toggle_large_text(self):
        """Toggle large text mode."""
        print(f"[Accessibility] Toggling large text from {self.large_text} to {not self.large_text}")
        self.large_text = not self.large_text
        self.apply_large_text()
        self._save_preferences()
        
        # Update page immediately
        self.page.update()
        
        # Announce change in background to avoid blocking
        message = f"Large text {'enabled' if self.large_text else 'disabled'}"
        threading.Thread(target=lambda: self._announce_change(message), daemon=True).start()

    def set_magnification_level(self, level: int):
        """Set magnification level with error handling and validation."""
        try:
            # Validate magnification level
            if not isinstance(level, (int, float)):
                raise ValueError(f"Magnification level must be numeric, got {type(level)}")
            
            level = int(level)
            if level < self.min_magnification or level > self.max_magnification:
                raise ValueError(f"Magnification level must be between {self.min_magnification}% and {self.max_magnification}%")
            
            # Store previous level for recovery
            self._last_magnification_level = self.magnification_level
            
            # Set new level
            old_level = self.magnification_level
            self.magnification_level = level
            
            # Apply magnification
            self.apply_magnification()
            
            # Save preferences
            self._save_preferences()
            
            # Announce change if level actually changed
            if old_level != level:
                message = f"Magnification set to {level}%"
                self._announce_change(message)
                print(f"[Accessibility] Magnification changed from {old_level}% to {level}%")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to set magnification level to {level}%: {e}")
            # Attempt recovery to last known good level
            try:
                self.magnification_level = self._last_magnification_level
                self.apply_magnification()
                self._announce_change(f"Magnification reset to {self._last_magnification_level}% due to error")
            except Exception as recovery_error:
                print(f"[ERROR] Failed to recover magnification: {recovery_error}")
                # Fall back to default
                self.magnification_level = 100
                self._last_magnification_level = 100
            return False

    def toggle_magnification(self):
        """Toggle magnification on/off with error handling."""
        try:
            self.magnification_enabled = not self.magnification_enabled
            
            if self.magnification_enabled:
                # Enable magnification at current level
                if self.magnification_level == 100:
                    self.magnification_level = 150  # Default to 150% when enabling
                self.apply_magnification()
                message = f"Magnification enabled at {self.magnification_level}%"
            else:
                # Disable magnification (reset to 100%)
                self.apply_magnification()
                message = "Magnification disabled"
            
            self._save_preferences()
            self._announce_change(message)
            print(f"[Accessibility] {message}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to toggle magnification: {e}")
            # Reset to safe state
            self.magnification_enabled = False
            self.magnification_level = 100
            try:
                self.apply_magnification()
            except:
                pass
            return False

    def increase_magnification(self):
        """Increase magnification level by one step."""
        try:
            new_level = min(self.max_magnification, self.magnification_level + self.magnification_step)
            if new_level != self.magnification_level:
                return self.set_magnification_level(new_level)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to increase magnification: {e}")
            return False

    def decrease_magnification(self):
        """Decrease magnification level by one step."""
        try:
            new_level = max(self.min_magnification, self.magnification_level - self.magnification_step)
            if new_level != self.magnification_level:
                return self.set_magnification_level(new_level)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to decrease magnification: {e}")
            return False

    def reset_magnification(self):
        """Reset magnification to 100% with error handling."""
        try:
            if self.magnification_level != 100:
                return self.set_magnification_level(100)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to reset magnification: {e}")
            return False

    def apply_magnification(self):
        """Apply magnification to the page with comprehensive error handling."""
        try:
            if not self.magnification_enabled:
                # Magnification disabled - reset to normal
                scale_factor = 1.0
            else:
                # Calculate scale factor from percentage
                scale_factor = self.magnification_level / 100.0
                
                # Validate scale factor
                if scale_factor < 0.5 or scale_factor > 3.0:
                    raise ValueError(f"Invalid scale factor: {scale_factor}")
            
            # Apply scaling to page if supported
            if hasattr(self.page, 'scale'):
                self.page.scale = scale_factor
                print(f"[Accessibility] Applied page scale: {scale_factor}x ({int(scale_factor * 100)}%)")
            
            # Apply text scaling for better readability at different magnifications
            if hasattr(self.page, 'theme') and self.page.theme:
                self._apply_magnified_text_theme(scale_factor)
            
            if hasattr(self.page, 'dark_theme') and self.page.dark_theme:
                self._apply_magnified_text_theme(scale_factor, dark_mode=True)
            
            # Update the page to apply changes
            self.page.update()
            
            print(f"[Accessibility] Successfully applied magnification: {self.magnification_level}% (enabled: {self.magnification_enabled})")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to apply magnification: {e}")
            # Attempt fallback to normal scaling
            try:
                if hasattr(self.page, 'scale'):
                    self.page.scale = 1.0
                self.page.update()
                print("[Accessibility] Fallback: Reset to normal scale")
            except Exception as fallback_error:
                print(f"[ERROR] Even fallback scaling failed: {fallback_error}")
            return False

    def _apply_magnified_text_theme(self, scale_factor: float, dark_mode: bool = False):
        """Apply text theme optimized for magnification levels."""
        try:
            # Base text sizes that work well with magnification
            base_sizes = {
                'body_large': 14,
                'body_medium': 12,
                'body_small': 10,
                'label_large': 12,
                'label_medium': 10,
                'label_small': 8,
            }
            
            # Adjust text sizes for magnification
            # At higher magnifications, we can use slightly smaller base sizes to prevent oversized text
            if scale_factor > 1.5:
                adjustment = 0.9  # Slightly smaller text at high magnification
            elif scale_factor < 0.8:
                adjustment = 1.1  # Slightly larger text at low magnification
            else:
                adjustment = 1.0
            
            adjusted_sizes = {key: max(8, int(size * adjustment)) for key, size in base_sizes.items()}
            
            # Create text theme
            text_theme = ft.TextTheme(
                body_large=ft.TextStyle(size=adjusted_sizes['body_large']),
                body_medium=ft.TextStyle(size=adjusted_sizes['body_medium']),
                body_small=ft.TextStyle(size=adjusted_sizes['body_small']),
                label_large=ft.TextStyle(size=adjusted_sizes['label_large']),
                label_medium=ft.TextStyle(size=adjusted_sizes['label_medium']),
                label_small=ft.TextStyle(size=adjusted_sizes['label_small']),
            )
            
            # Apply to appropriate theme
            if dark_mode:
                self.page.dark_theme.text_theme = text_theme
            else:
                self.page.theme.text_theme = text_theme
                
            print(f"[Accessibility] Applied magnified text theme (scale: {scale_factor}, adjustment: {adjustment})")
            
        except Exception as e:
            print(f"[ERROR] Failed to apply magnified text theme: {e}")

    def get_magnification_info(self):
        """Get current magnification information."""
        try:
            return {
                "enabled": self.magnification_enabled,
                "level": self.magnification_level,
                "min_level": self.min_magnification,
                "max_level": self.max_magnification,
                "step": self.magnification_step,
                "scale_factor": self.magnification_level / 100.0 if self.magnification_enabled else 1.0
            }
        except Exception as e:
            print(f"[ERROR] Failed to get magnification info: {e}")
            return {
                "enabled": False,
                "level": 100,
                "min_level": 50,
                "max_level": 300,
                "step": 25,
                "scale_factor": 1.0
            }

    def _toggle_reduce_motion(self):
        """Toggle reduced motion mode."""
        print(f"[Accessibility] Toggling reduce motion from {self.reduce_motion} to {not self.reduce_motion}")
        self.reduce_motion = not self.reduce_motion
        self._save_preferences()
        
        # Update page immediately
        self.page.update()
        
        # Announce change in background to avoid blocking
        message = f"Reduced motion {'enabled' if self.reduce_motion else 'disabled'}"
        threading.Thread(target=lambda: self._announce_change(message), daemon=True).start()

    def _toggle_screen_reader_mode(self):
        """Toggle screen reader optimizations."""
        print(f"[Accessibility] Toggling screen reader mode from {self.screen_reader_mode} to {not self.screen_reader_mode}")
        self.screen_reader_mode = not self.screen_reader_mode
        self._save_preferences()
        
        # Update page immediately
        self.page.update()
        
        # Announce changes in background to avoid blocking
        message = f"Screen reader mode {'enabled' if self.screen_reader_mode else 'disabled'}"
        
        def announce_and_test():
            self._announce_change(message)
            # Test screen reader integration when enabled
            if self.screen_reader_mode and self.sapi_voice:
                time.sleep(0.5)  # Brief pause between announcements
                self._speak_text("Screen reader integration is now active using Windows SAPI")
        
        threading.Thread(target=announce_and_test, daemon=True).start()

    def _toggle_audio_feedback(self):
        """Toggle audio feedback mode."""
        print(f"[Accessibility] Toggling audio feedback from {self.audio_feedback} to {not self.audio_feedback}")
        self.audio_feedback = not self.audio_feedback
        self._save_preferences()
        
        # Update page immediately
        self.page.update()
        
        message = f"Audio feedback {'enabled' if self.audio_feedback else 'disabled'}"
        
        if self.audio_feedback:
            # Test audio when enabling - run in background
            threading.Thread(target=lambda: self._speak_text(message), daemon=True).start()
        else:
            print(f"[Accessibility] {message}")
            # Show visual notification when disabling audio
            snack = ft.SnackBar(
                content=ft.Text(f"♿ {message}"),
                duration=2000,
                bgcolor=ft.Colors.BLUE_GREY_800,
            )
            self.page.show_snack_bar(snack)

    def _toggle_speech_to_text(self):
        """Toggle speech-to-text functionality."""
        print(f"[Accessibility] Toggling speech-to-text from {self.speech_to_text_enabled} to {not self.speech_to_text_enabled}")
        self.speech_to_text_enabled = not self.speech_to_text_enabled
        self._save_preferences()
        
        # Update page immediately
        if hasattr(self, 'page') and self.page:
            self.page.update()
        
        # Announce change in background to avoid blocking
        message = f"Speech to text {'enabled' if self.speech_to_text_enabled else 'disabled'}"
        threading.Thread(target=lambda: self._announce_change(message), daemon=True).start()

    def _test_accessibility(self):
        """Test accessibility features - comprehensive check."""
        if not hasattr(self, 'page') or not self.page:
            return
            
        test_results = []
        
        # Test TTS engines
        tts_available = bool(self.tts_engine or self.sapi_voice)
        test_results.append(f"TTS Available: {'✅ Yes' if tts_available else '❌ No'}")
        
        # Test current settings
        test_results.append(f"High Contrast: {'✅ On' if self.high_contrast else '❌ Off'}")
        test_results.append(f"Large Text: {'✅ On' if self.large_text else '❌ Off'}")
        test_results.append(f"Screen Reader Mode: {'✅ On' if self.screen_reader_mode else '❌ Off'}")
        test_results.append(f"Audio Feedback: {'✅ On' if self.audio_feedback else '❌ Off'}")
        test_results.append(f"Live Announcements: {'✅ On' if self.live_announcements else '❌ Off'}")
        test_results.append(f"Color Blind Mode: {self.color_blind_mode}")
        
        # Show test results
        results_text = "ACCESSIBILITY TEST RESULTS:\n\n" + "\n".join(test_results)
        
        test_dialog = ft.AlertDialog(
            title=ft.Text("Accessibility Test Results", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Text(results_text, selectable=True),
                width=400,
                height=300,
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Test Audio",
                    on_click=lambda e: self._speak_text("Audio test successful - all systems working"),
                    disabled=not tts_available
                ),
                ft.TextButton(
                    "Close",
                    on_click=lambda e: self._close_dialog(test_dialog)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = test_dialog
        test_dialog.open = True
        self.page.update()
        
        # Announce test completion
        self._announce_change("Accessibility test completed")

    def _toggle_pause_operations(self):
        """Toggle pause/resume state for operations."""
        # IMMEDIATELY stop all current TTS/speech before doing anything else
        self._stop_all_speech()
        
        self.operations_paused = not self.operations_paused
        status = "PAUSED" if self.operations_paused else "RESUMED"
        print(f"[Accessibility] Operations {status}")
        
        # Announce the change with appropriate priority
        message = f"Operations {status.lower()}. Press Ctrl+Shift+P to {('resume' if self.operations_paused else 'pause')} again."
        
        # Show visual status overlay immediately
        self._show_pause_status_overlay(f"⏸️ PAUSED" if self.operations_paused else "▶️ RESUMED")
        
        # Use urgent priority so the pause/resume notification always gets through
        # Add a small delay to ensure speech engines are ready after stopping
        import threading
        import time
        
        def delayed_announce():
            time.sleep(0.2)  # Small delay to ensure speech is fully stopped
            if self.operations_paused:
                # For pause: use urgent priority to bypass the pause check
                print(f"[Accessibility] URGENT PAUSE NOTIFICATION: {message}")
                self._speak_text(message, priority="urgent")
            else:
                # For resume: normal announcement
                self._announce_change(message)
        
        # Run announcement in separate thread to not block the UI
        threading.Thread(target=delayed_announce, daemon=True).start()
        
        # Save the pause state
        self._save_preferences()
        
        return self.operations_paused

    def _stop_all_speech(self):
        """Immediately stop all TTS and SAPI speech."""
        try:
            # Stop pyttsx3 engine
            if self.tts_engine:
                self.tts_engine.stop()
                print("[Accessibility] Stopped pyttsx3 TTS")
            
            # Stop Windows SAPI - multiple methods for thoroughness
            if self.sapi_voice:
                try:
                    # Method 1: Skip all remaining speech
                    self.sapi_voice.Skip("Sentence", 9999)
                    # Method 2: Speak empty string to interrupt
                    self.sapi_voice.Speak("", 3)  # Flag 3 = purge before speak + async
                    print("[Accessibility] Stopped Windows SAPI speech")
                except Exception as e:
                    print(f"[Accessibility] Error stopping SAPI: {e}")
                    
        except Exception as e:
            print(f"[Accessibility] Error stopping speech: {e}")

        # Add a small delay to ensure speech stops
        import time
        time.sleep(0.1)

    def _show_pause_status_overlay(self, message: str):
        """Show a brief visual overlay for pause status."""
        if not hasattr(self, 'page') or not self.page:
            return
            
        try:
            # Create a small status overlay
            status_overlay = ft.Container(
                content=ft.Text(
                    message,
                    color=ft.Colors.WHITE,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                bgcolor=ft.Colors.RED if "paused" in message.lower() else ft.Colors.GREEN,
                padding=15,
                border_radius=10,
                alignment=ft.alignment.center,
                width=300,
                height=60,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=10,
                    color=ft.Colors.BLACK54
                )
            )
            
            # Position it at the top center of the screen
            positioned_overlay = ft.Container(
                content=status_overlay,
                alignment=ft.alignment.top_center,
                margin=ft.margin.only(top=50)
            )
            
            # Add overlay to page
            self.page.overlay.append(positioned_overlay)
            self.page.update()
            
            # Remove overlay after 2 seconds
            import threading
            import time
            
            def remove_overlay():
                time.sleep(2)
                try:
                    if positioned_overlay in self.page.overlay:
                        self.page.overlay.remove(positioned_overlay)
                        self.page.update()
                except Exception as e:
                    print(f"[Accessibility] Error removing status overlay: {e}")
            
            threading.Thread(target=remove_overlay, daemon=True).start()
            print(f"[Accessibility] Showed status overlay: {message}")
            
        except Exception as e:
            print(f"[Accessibility] Error showing status overlay: {e}")

    def is_operations_paused(self):
        """Check if operations are currently paused."""
        return getattr(self, 'operations_paused', False)

    def _toggle_shortcuts_overlay(self):
        """Toggle the keyboard shortcuts overlay."""
        self.show_keyboard_shortcuts_overlay()

    def _cycle_color_blind_mode(self):
        """Cycle through color blindness support modes via keyboard shortcut."""
        self.cycle_color_blind_mode()

    def _increase_tts_speed(self):
        """Increase TTS speech speed."""
        self.tts_speed = min(300, self.tts_speed + 25)
        self._update_tts_settings()
        self._save_preferences()
        self._speak_text(f"Speech speed increased to {self.tts_speed}")

    def _decrease_tts_speed(self):
        """Decrease TTS speech speed."""
        self.tts_speed = max(50, self.tts_speed - 25)
        self._update_tts_settings()
        self._save_preferences()
        self._speak_text(f"Speech speed decreased to {self.tts_speed}")

    def _increase_tts_volume(self):
        """Increase TTS volume."""
        self.tts_volume = min(1.0, self.tts_volume + 0.1)
        self._update_tts_settings()
        self._save_preferences()
        self._speak_text(f"Speech volume increased to {int(self.tts_volume * 100)} percent")

    def _decrease_tts_volume(self):
        """Decrease TTS volume."""
        self.tts_volume = max(0.1, self.tts_volume - 0.1)
        self._update_tts_settings()
        self._save_preferences()
        self._speak_text(f"Speech volume decreased to {int(self.tts_volume * 100)} percent")

    def _increase_magnification(self):
        """Increase magnification level by 25%."""
        try:
            current_level = self.magnification_level
            new_level = min(300, current_level + 25)  # Max 300%
            
            if new_level != current_level:
                success = self.set_magnification_level(new_level)
                if success:
                    self._announce_change(f"Magnification increased to {new_level}%")
                    print(f"[Accessibility] Magnification increased via keyboard: {current_level}% → {new_level}%")
                else:
                    self._announce_change("Failed to increase magnification")
            else:
                self._announce_change("Magnification already at maximum level")
        except Exception as e:
            print(f"[Accessibility] Error increasing magnification: {e}")
            self._announce_change("Error adjusting magnification")

    def _decrease_magnification(self):
        """Decrease magnification level by 25%."""
        try:
            current_level = self.magnification_level
            new_level = max(50, current_level - 25)  # Min 50%
            
            if new_level != current_level:
                success = self.set_magnification_level(new_level)
                if success:
                    self._announce_change(f"Magnification decreased to {new_level}%")
                    print(f"[Accessibility] Magnification decreased via keyboard: {current_level}% → {new_level}%")
                else:
                    self._announce_change("Failed to decrease magnification")
            else:
                self._announce_change("Magnification already at minimum level")
        except Exception as e:
            print(f"[Accessibility] Error decreasing magnification: {e}")
            self._announce_change("Error adjusting magnification")

    def _reset_magnification(self):
        """Reset magnification to 100% (normal size)."""
        try:
            current_level = self.magnification_level
            success = self.set_magnification_level(100)
            if success:
                self._announce_change("Magnification reset to normal size")
                print(f"[Accessibility] Magnification reset via keyboard: {current_level}% → 100%")
            else:
                self._announce_change("Failed to reset magnification")
        except Exception as e:
            print(f"[Accessibility] Error resetting magnification: {e}")
            self._announce_change("Error resetting magnification")

    def _focus_summary(self):
        """Announce the currently focused element and its context."""
        if not hasattr(self, 'page') or not self.page:
            return
            
        try:
            # Get the currently focused element information
            focus_info = "Focus summary: "
            
            if self.table_navigation_mode:
                row, col = self.current_cell_position["row"], self.current_cell_position["col"]
                focus_info += f"Table navigation mode active. Current position: Row {row + 1}, Column {col + 1}"
            else:
                focus_info += "Standard navigation mode active. Use Ctrl+Shift+N to enable table navigation."
            
            # Add current tab information if available
            focus_info += f" Current interface mode: {'High contrast' if self.high_contrast else 'Standard contrast'}"
            focus_info += f", TTS {'enabled' if self.audio_feedback else 'disabled'}"
            
            self._announce_change(focus_info)
            
        except Exception as e:
            print(f"[Accessibility] Error getting focus summary: {e}")

    def _table_cell_navigation_mode(self):
        """Toggle enhanced table cell navigation mode."""
        self.table_navigation_mode = not self.table_navigation_mode
        
        if self.table_navigation_mode:
            self.current_cell_position = {"row": 0, "col": 0}
            self._announce_change("Table navigation mode enabled. Use arrow keys to navigate cells.")
            print("[Accessibility] Table navigation mode enabled")
        else:
            self._announce_change("Table navigation mode disabled. Standard navigation restored.")
            print("[Accessibility] Table navigation mode disabled")

    def navigate_table_cell(self, direction: str, data_df=None):
        """Navigate to adjacent table cell and announce content."""
        if not self.table_navigation_mode or data_df is None:
            return
            
        try:
            max_rows, max_cols = data_df.shape
            row, col = self.current_cell_position["row"], self.current_cell_position["col"]
            
            # Calculate new position
            if direction == "up":
                row = max(0, row - 1)
            elif direction == "down":
                row = min(max_rows - 1, row + 1)
            elif direction == "left":
                col = max(0, col - 1)
            elif direction == "right":
                col = min(max_cols - 1, col + 1)
            elif direction == "home":
                col = 0
            elif direction == "end":
                col = max_cols - 1
                
            self.current_cell_position = {"row": row, "col": col}
            
            # Get cell content and announce
            cell_value = data_df.iloc[row, col]
            column_name = data_df.columns[col]
            
            announcement = f"Row {row + 1}, Column {column_name}: {cell_value}"
            self._announce_change(announcement)
            
        except Exception as e:
            print(f"[Accessibility] Error navigating table cell: {e}")

    def _run_accessibility_audit(self):
        """Run an accessibility audit of the current interface."""
        if not hasattr(self, 'page') or not self.page:
            return
            
        audit_results = []
        
        # Check accessibility features status
        audit_results.append("🔍 ACCESSIBILITY AUDIT RESULTS:")
        audit_results.append("")
        
        # Core features audit
        audit_results.append("✅ Core Features:")
        audit_results.append(f"  • High Contrast: {'✅ Enabled' if self.high_contrast else '⚠️ Disabled'}")
        audit_results.append(f"  • Large Text: {'✅ Enabled' if self.large_text else '⚠️ Disabled'}")
        audit_results.append(f"  • Screen Reader: {'✅ Enabled' if self.screen_reader_mode else '⚠️ Disabled'}")
        audit_results.append(f"  • Audio Feedback: {'✅ Enabled' if self.audio_feedback else '⚠️ Disabled'}")
        audit_results.append(f"  • Live Announcements: {'✅ Enabled' if self.live_announcements else '⚠️ Disabled'}")
        
        # Advanced features audit
        audit_results.append("")
        audit_results.append("🚀 Advanced Features:")
        audit_results.append(f"  • Color Blindness Support: {'✅ ' + self.color_blind_mode if self.color_blind_mode != 'none' else '⚠️ Standard colors'}")
        audit_results.append(f"  • Table Navigation: {'✅ Active' if self.table_navigation_mode else '⚠️ Standard mode'}")
        audit_results.append(f"  • Focus Management: {'✅ Enhanced' if self.focus_management else '⚠️ Standard'}")
        audit_results.append(f"  • Error Prevention: {'✅ Enabled' if self.error_prevention else '⚠️ Disabled'}")
        
        # Technical audit
        audit_results.append("")
        audit_results.append("🔧 Technical Status:")
        audit_results.append(f"  • TTS Engine: {'✅ Available' if self.tts_engine else '❌ Not available'}")
        audit_results.append(f"  • Windows SAPI: {'✅ Available' if self.sapi_voice else '❌ Not available'}")
        audit_results.append(f"  • Live Region: {'✅ Connected' if hasattr(self.live_region, 'page') and self.live_region.page else '❌ Not connected'}")
        audit_results.append(f"  • Keyboard Shortcuts: {'✅ ' + str(len(self.shortcuts)) + ' registered' if self.shortcuts else '❌ None'}")
        
        # Recommendations
        audit_results.append("")
        audit_results.append("💡 Recommendations:")
        if not self.screen_reader_mode and not self.audio_feedback:
            audit_results.append("  • Consider enabling Screen Reader mode or Audio Feedback")
        if self.color_blind_mode == "none":
            audit_results.append("  • Test color blindness modes if you have color vision differences")
        if not self.table_navigation_mode:
            audit_results.append("  • Try table navigation mode (Ctrl+Shift+N) for detailed data exploration")
        
        # Show results in dialog
        audit_text = "\n".join(audit_results)
        
        audit_dialog = ft.AlertDialog(
            title=ft.Text("Accessibility Audit Report", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Text(audit_text, selectable=True, size=12),
                width=600,
                height=400,
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Run TTS Test",
                    on_click=lambda e: self._speak_text("Accessibility audit completed. All systems functional."),
                    disabled=not (self.tts_engine or self.sapi_voice)
                ),
                ft.TextButton(
                    "Close",
                    on_click=lambda e: self._close_dialog(audit_dialog)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = audit_dialog
        audit_dialog.open = True
        self.page.update()
        
        self._announce_change("Accessibility audit completed. Check dialog for detailed results.")

    def _close_dialog(self, dialog):
        """Helper method to close a dialog."""
        if dialog and hasattr(dialog, 'open'):
            dialog.open = False
            if hasattr(self, 'page') and self.page:
                self.page.update()

    def add_custom_shortcut(self, key_combination: str, function_callback, description: str):
        """Add a custom accessibility shortcut."""
        try:
            self.custom_shortcuts[key_combination] = {
                'callback': function_callback,
                'description': description
            }
            print(f"[Accessibility] Custom shortcut added: {key_combination} - {description}")
            
        except Exception as e:
            print(f"[Accessibility] Error adding custom shortcut: {e}")

    def get_available_shortcuts(self) -> dict:
        """Get all available keyboard shortcuts."""
        all_shortcuts = {}
        
        # Add built-in shortcuts
        for key, value in self.shortcuts.items():
            all_shortcuts[key] = value.__name__ if hasattr(value, '__name__') else str(value)
        
        # Add custom shortcuts
        for key, value in self.custom_shortcuts.items():
            all_shortcuts[key] = value['description']
            
        return all_shortcuts

    def enhance_modal_accessibility(self, dialog: ft.AlertDialog):
        """Enhance modal dialog accessibility with focus trapping and ARIA roles."""
        if not dialog:
            return
            
        try:
            # Add ARIA attributes
            if hasattr(dialog, 'content'):
                dialog.modal = True
                
            # Add keyboard handler for focus trapping
            def handle_modal_keys(e):
                if e.key == "Escape":
                    self._close_dialog(dialog)
                    return
                    
                # Handle Tab navigation within modal
                if e.key == "Tab":
                    # Focus management for modal
                    if hasattr(dialog, 'actions') and dialog.actions:
                        # Cycle through action buttons
                        pass
                        
            dialog.on_dismiss = lambda e: self._announce_change("Dialog closed")
            
            # Announce dialog opening
            if hasattr(dialog, 'title') and dialog.title:
                title_text = dialog.title.value if hasattr(dialog.title, 'value') else str(dialog.title)
                self._announce_change(f"Dialog opened: {title_text}")
            else:
                self._announce_change("Dialog opened")
                
        except Exception as e:
            print(f"[Accessibility] Error enhancing modal accessibility: {e}")

    def setup_voice_commands(self):
        """Setup basic voice command recognition (placeholder for future implementation)."""
        # This is a placeholder for future voice command integration
        # Would require speech recognition library like SpeechRecognition
        print("[Accessibility] Voice commands feature ready for implementation")
        
    def export_accessibility_settings(self) -> dict:
        """Export current accessibility settings for backup/sharing."""
        return {
            'high_contrast': self.high_contrast,
            'large_text': self.large_text,
            'screen_reader_mode': self.screen_reader_mode,
            'audio_feedback': self.audio_feedback,
            'live_announcements': self.live_announcements,
            'color_blind_mode': self.color_blind_mode,
            'tts_rate': self.tts_rate,
            'tts_volume': self.tts_volume,
            'focus_management': self.focus_management,
            'error_prevention': self.error_prevention,
            'table_navigation_mode': self.table_navigation_mode,
            'custom_shortcuts': {k: v['description'] for k, v in self.custom_shortcuts.items()}
        }

    def import_accessibility_settings(self, settings: dict):
        """Import accessibility settings from backup."""
        try:
            for key, value in settings.items():
                if key == 'custom_shortcuts':
                    continue  # Skip custom shortcuts import for security
                if hasattr(self, key):
                    setattr(self, key, value)
                    
            self._update_tts_settings()
            self._save_preferences()
            self._announce_change("Accessibility settings imported successfully")
            
        except Exception as e:
            print(f"[Accessibility] Error importing settings: {e}")
            self._announce_change("Error importing accessibility settings")

    def handle_key_event(self, e, data_df=None):
        """Enhanced keyboard event handler with table navigation support."""
        if not e.key:
            return
            
        try:
            # Handle table navigation if in table mode
            if self.table_navigation_mode and data_df is not None:
                if e.key in ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End"]:
                    direction_map = {
                        "ArrowUp": "up",
                        "ArrowDown": "down", 
                        "ArrowLeft": "left",
                        "ArrowRight": "right",
                        "Home": "home",
                        "End": "end"
                    }
                    self.navigate_table_cell(direction_map[e.key], data_df)
                    return
            
            # Build key combination string correctly
            key_combo = []
            if e.ctrl:
                key_combo.append("ctrl")
            if e.shift:
                key_combo.append("shift")
            if e.alt:
                key_combo.append("alt")
            key_combo.append(e.key.lower())
            
            # Join with + to match shortcut keys
            key_string = "+".join(key_combo)
            
            print(f"[Accessibility] Processing key combination: {key_string}")
            
            # Check built-in shortcuts
            if key_string in self.shortcuts:
                print(f"[Accessibility] Executing shortcut: {key_string}")
                # Run in thread to avoid blocking UI
                threading.Thread(target=self.shortcuts[key_string], daemon=True).start()
                return True
                
            # Check custom shortcuts
            if key_string in self.custom_shortcuts:
                print(f"[Accessibility] Executing custom shortcut: {key_string}")
                # Run in thread to avoid blocking UI
                threading.Thread(target=self.custom_shortcuts[key_string]['callback'], daemon=True).start()
                return True
                
        except Exception as ex:
            print(f"[Accessibility] Error handling key event: {ex}")
            
        return False
        """Get a comprehensive status summary of all accessibility features."""
        status_lines = []
        status_lines.append("🌟 ACCESSIBILITY STATUS SUMMARY")
        status_lines.append("=" * 50)
        
        # Core features
        status_lines.append("🎯 Core Features:")
        status_lines.append(f"  High Contrast: {'✅' if self.high_contrast else '❌'}")
        status_lines.append(f"  Large Text: {'✅' if self.large_text else '❌'}")
        status_lines.append(f"  Screen Reader: {'✅' if self.screen_reader_mode else '❌'}")
        status_lines.append(f"  Audio Feedback: {'✅' if self.audio_feedback else '❌'}")
        status_lines.append(f"  Live Announcements: {'✅' if self.live_announcements else '❌'}")
        
        # Advanced features
        status_lines.append("")
        status_lines.append("🚀 Advanced Features:")
        status_lines.append(f"  Color Blindness Support: {self.color_blind_mode}")
        status_lines.append(f"  Table Navigation: {'✅ Active' if self.table_navigation_mode else '❌ Disabled'}")
        status_lines.append(f"  Focus Management: {'✅' if self.focus_management else '❌'}")
        status_lines.append(f"  Error Prevention: {'✅' if self.error_prevention else '❌'}")
        
        # System status
        status_lines.append("")
        status_lines.append("🔧 System Status:")
        status_lines.append(f"  TTS Engine: {'✅' if self.tts_engine else '❌'}")
        status_lines.append(f"  Windows SAPI: {'✅' if self.sapi_voice else '❌'}")
        status_lines.append(f"  Shortcuts: {len(self.shortcuts)} built-in + {len(self.custom_shortcuts)} custom")
        
        return "\n".join(status_lines)

    def demo_accessibility_features(self):
        """Comprehensive demo of all accessibility features."""
        demo_steps = [
            "🎉 Welcome to the DataScope Accessibility Features Demo!",
            "This demo will showcase all available accessibility enhancements.",
            "",
            "🎯 Core Features Demo:",
            "High contrast mode for better visibility",
            "Large text for improved readability", 
            "Screen reader optimizations with ARIA labels",
            "Audio feedback with customizable voice settings",
            "Live region announcements for real-time updates",
            "",
            "🚀 Advanced Features Demo:",
            "Color blindness support with specialized color schemes",
            "Table navigation mode for detailed data exploration",
            "Focus management with enhanced keyboard navigation",
            "Error prevention with confirmation dialogs",
            "",
            "⌨️ Keyboard Shortcuts Available:",
            "Ctrl+Shift+A: Toggle audio feedback",
            "Ctrl+Shift+C: Toggle high contrast",
            "Ctrl+Shift+L: Toggle large text",
            "Ctrl+Shift+S: Toggle screen reader mode",
            "Ctrl+Shift+F: Focus summary",
            "Ctrl+Shift+N: Table navigation mode",
            "Ctrl+Shift+R: Accessibility audit",
            "Ctrl+Shift+H: Show help",
            "",
            "🔧 Technical Features:",
            "Dual TTS engine support (pyttsx3 + Windows SAPI)",
            "Customizable speech rate and volume",
            "Accessibility settings persistence",
            "Modal dialog accessibility enhancements",
            "Custom shortcut support",
            "",
            "Try these features now! Use Ctrl+Shift+R for a full accessibility audit."
        ]
        
        demo_text = "\n".join(demo_steps)
        
        demo_dialog = ft.AlertDialog(
            title=ft.Text("🌟 Accessibility Features Demo", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Text(demo_text, selectable=True, size=12),
                width=700,
                height=500,
                padding=20
            ),
            actions=[
                ft.TextButton(
                    "Run Accessibility Audit",
                    on_click=lambda e: self._run_accessibility_audit()
                ),
                ft.TextButton(
                    "Test Speech",
                    on_click=lambda e: self._speak_text("DataScope accessibility system is fully operational. All features are ready for use."),
                    disabled=not (self.tts_engine or self.sapi_voice)
                ),
                ft.TextButton(
                    "Close Demo",
                    on_click=lambda e: self._close_dialog(demo_dialog)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        # Enhance the demo dialog accessibility
        self.enhance_modal_accessibility(demo_dialog)
        
        self.page.dialog = demo_dialog
        demo_dialog.open = True
        self.page.update()
        
        self._announce_change("Accessibility features demo opened. Check dialog for comprehensive feature overview.")

    def _focus_tab(self, tab_index: int):
        """Focus a specific tab by index."""
        try:
            # This would need to be connected to the main app's tab system
            print(f"[Accessibility] Focusing tab {tab_index}")
            self._announce_change(f"Switched to tab {tab_index + 1}")
        except Exception as e:
            print(f"[Accessibility] Failed to focus tab {tab_index}: {e}")

    def _show_modal_overlay(self, title: str, content: str, dialog_type: str = "info"):
        """Show a modal overlay instead of AlertDialog."""
        print(f"[Accessibility] Showing modal overlay: {title}")
        
        if not hasattr(self, 'page') or not self.page:
            print("[Accessibility] ERROR: No page reference for modal overlay")
            return
        
        # Store the current page content
        self.original_page_content = self.page.controls.copy()
        
        # Create modal overlay
        modal_content = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=ft.Colors.WHITE,
                                on_click=lambda e: self._close_modal_overlay(),
                                tooltip="Close"
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(color=ft.Colors.WHITE54),
                        ft.Container(
                            content=ft.Text(
                                content,
                                color=ft.Colors.WHITE,
                                size=14,
                                selectable=True
                            ),
                            height=400,
                            padding=10,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=5
                        ),
                        ft.ElevatedButton(
                            "Close",
                            on_click=lambda e: self._close_modal_overlay(),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE,
                                color=ft.Colors.WHITE
                            )
                        )
                    ], spacing=10),
                    padding=30,
                    bgcolor=ft.Colors.BLUE_GREY_800,
                    border_radius=15,
                    width=600,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=15,
                        color=ft.Colors.BLACK54,
                        offset=ft.Offset(0, 4)
                    )
                )
            ], 
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.BLACK54,  # Semi-transparent overlay
            width=self.page.width if hasattr(self.page, 'width') else 1200,
            height=self.page.height if hasattr(self.page, 'height') else 800,
            alignment=ft.alignment.center
        )
        
        # Replace page content with modal
        self.page.controls.clear()
        self.page.add(modal_content)
        self.page.update()
        print(f"[Accessibility] Modal overlay displayed: {title}")

    def _close_modal_overlay(self):
        """Close the modal overlay and restore original content."""
        print("[Accessibility] Closing modal overlay")
        
        if hasattr(self, 'original_page_content') and self.original_page_content:
            self.page.controls.clear()
            self.page.controls.extend(self.original_page_content)
            self.page.update()
            print("[Accessibility] Original page content restored")
        else:
            print("[Accessibility] ERROR: No original content to restore")

    def _show_help_with_debug(self):
        """Show accessibility help dialog with debug logging."""
        print("[Accessibility] Help button clicked - showing accessibility help modal")
        try:
            help_text = """🌟 ACCESSIBILITY FEATURES HELP

🎹 KEYBOARD SHORTCUTS:
• Ctrl+H: Toggle High Contrast
• Ctrl+Shift+L: Toggle Large Text  
• Ctrl+Shift+M: Toggle Reduced Motion
• Ctrl+Shift+S: Toggle Screen Reader Mode
• Alt+1-5: Switch between tabs
• F1: Show this help
• Ctrl+/: Show shortcuts list
• F3: Next search result
• Shift+F3: Previous search result
• Escape: Clear search
• Ctrl+Shift+P: Pause/Resume operations

♿ ACCESSIBILITY SETTINGS:
• High Contrast: Enhanced color contrast
• Large Text: Increased font sizes
• Reduced Motion: Minimized animations
• Screen Reader Mode: Optimized for assistive technology
• Enhanced Focus: Better keyboard navigation indicators

⏸️ PAUSE FEATURE:
• Use Ctrl+Shift+P to pause all data operations
• Useful for stopping long-running analyses
• Press again to resume operations
• Pause state is saved automatically

💡 TIPS:
• All features work with keyboard only
• Settings are saved automatically
• Use Tab/Shift+Tab to navigate
• Press Space/Enter to activate buttons
• Use arrow keys in dropdowns and tables"""
            
            self._show_modal_overlay("♿ Accessibility Help", help_text)
            print("[Accessibility] Help modal displayed successfully")
        except Exception as e:
            print(f"[Accessibility] Error showing help modal: {e}")
            import traceback
            traceback.print_exc()

    def _show_shortcuts_with_debug(self):
        """Show keyboard shortcuts dialog with debug logging."""
        print("[Accessibility] Shortcuts button clicked - showing keyboard shortcuts modal")
        try:
            shortcuts_text = """🎹 KEYBOARD SHORTCUTS:

ACCESSIBILITY:
• Ctrl+H: High Contrast
• Ctrl+Shift+L: Large Text
• Ctrl+Shift+M: Reduced Motion
• Ctrl+Shift+S: Screen Reader Mode

NAVIGATION:
• Alt+1: Console Tab
• Alt+2: Data View Tab
• Alt+3: Data Tools Tab
• Alt+4: Advanced Tab
• Alt+5: Settings Tab

SEARCH:
• F3: Next result
• Shift+F3: Previous result
• Escape: Clear search

OPERATIONS:
• Ctrl+Shift+P: Pause/Resume operations

HELP:
• F1: Accessibility help
• Ctrl+/: This shortcuts list

ADVANCED:
• Ctrl+Shift+O: Toggle shortcuts overlay
• Ctrl+Shift+C: Cycle color blind modes
• Ctrl+Shift+T: Test accessibility features
• Ctrl+Shift+V: Cycle voice gender (TTS)
• Ctrl+Shift+G: Test current voice
• Ctrl+Shift+Up/Down: Adjust TTS speed
• Ctrl+Shift+Left/Right: Adjust TTS volume

MAGNIFICATION:
• Ctrl++ (Plus): Increase magnification
• Ctrl+- (Minus): Decrease magnification  
• Ctrl+0 (Zero): Reset magnification to 100%"""
            
            self._show_modal_overlay("🎹 Keyboard Shortcuts", shortcuts_text)
            print("[Accessibility] Shortcuts modal displayed successfully")
        except Exception as e:
            print(f"[Accessibility] Error showing shortcuts modal: {e}")
            import traceback
            traceback.print_exc()

    def _show_help(self):
        """Show accessibility help dialog."""
        print(f"[Accessibility] _show_help called - page reference: {self.page is not None}")
        
        if not hasattr(self, 'page') or not self.page:
            print("[Accessibility] ERROR: No page reference available for help dialog")
            return
            
        help_text = """🌟 ACCESSIBILITY FEATURES HELP

🎹 KEYBOARD SHORTCUTS:
• Ctrl+H: Toggle High Contrast
• Ctrl+Shift+L: Toggle Large Text  
• Ctrl+Shift+M: Toggle Reduced Motion
• Ctrl+Shift+S: Toggle Screen Reader Mode
• Alt+1-5: Switch between tabs
• F1: Show this help
• Ctrl+/: Show shortcuts list
• F3: Next search result
• Shift+F3: Previous search result
• Escape: Clear search

♿ ACCESSIBILITY SETTINGS:
• High Contrast: Enhanced color contrast
• Large Text: Increased font sizes
• Reduced Motion: Minimized animations
• Screen Reader Mode: Optimized for assistive technology
• Enhanced Focus: Better keyboard navigation indicators

💡 TIPS:
• All features work with keyboard only
• Settings are saved automatically
• Use Tab/Shift+Tab to navigate
• Press Space/Enter to activate buttons
• Use arrow keys in dropdowns and tables"""
        
        dialog = ft.AlertDialog(
            title=ft.Text("♿ Accessibility Help"),
            content=ft.Container(
                content=ft.Text(help_text, selectable=True),
                padding=20,
                width=600,
                height=400,
                bgcolor=ft.Colors.SURFACE,
                border_radius=10
            ),
            actions=[
                ft.TextButton(
                    "Close", 
                    on_click=lambda e: self._close_dialog(dialog),
                    tooltip="Close help dialog"
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=ft.Colors.SURFACE,
            surface_tint_color=ft.Colors.PRIMARY,
        )
        
        print("[Accessibility] Setting dialog on page and opening")
        # Close any existing dialog first
        if hasattr(self.page, 'dialog') and self.page.dialog:
            self.page.dialog.open = False
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        print("[Accessibility] Help dialog should now be visible")

    def _show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        print(f"[Accessibility] _show_shortcuts called - page reference: {self.page is not None}")
        
        if not hasattr(self, 'page') or not self.page:
            print("[Accessibility] ERROR: No page reference available for shortcuts dialog")
            return
            
        shortcuts_text = """🎹 KEYBOARD SHORTCUTS:

ACCESSIBILITY:
• Ctrl+H: High Contrast
• Ctrl+Shift+L: Large Text
• Ctrl+Shift+M: Reduced Motion
• Ctrl+Shift+S: Screen Reader Mode
• Ctrl+Shift+Y: Speech-to-Text Toggle

NAVIGATION:
• Alt+1: Console Tab
• Alt+2: Data View Tab
• Alt+3: Data Tools Tab
• Alt+4: Advanced Tab
• Alt+5: Settings Tab

SEARCH:
• F3: Next result
• Shift+F3: Previous result
• Escape: Clear search

HELP:
• F1: Accessibility help
• Ctrl+/: This shortcuts list

MAGNIFICATION:
• Ctrl++ (Plus): Increase magnification
• Ctrl+- (Minus): Decrease magnification  
• Ctrl+0 (Zero): Reset magnification to 100%"""
        
        dialog = ft.AlertDialog(
            title=ft.Text("🎹 Keyboard Shortcuts"),
            content=ft.Container(
                content=ft.Text(shortcuts_text, selectable=True),
                padding=20,
                width=500,
                height=350,
                bgcolor=ft.Colors.SURFACE,
                border_radius=10
            ),
            actions=[
                ft.TextButton(
                    "Close", 
                    on_click=lambda e: self._close_dialog(dialog),
                    tooltip="Close shortcuts dialog"
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=ft.Colors.SURFACE,
            surface_tint_color=ft.Colors.PRIMARY,
        )
        
        print("[Accessibility] Setting shortcuts dialog on page and opening")
        # Close any existing dialog first
        if hasattr(self.page, 'dialog') and self.page.dialog:
            self.page.dialog.open = False
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        print("[Accessibility] Shortcuts dialog should now be visible")

    def _close_dialog(self, dialog):
        """Close a dialog."""
        dialog.open = False
        self.page.update()

    def _announce_change(self, message: str):
        """Announce changes for screen readers and audio feedback with live region support."""
        print(f"[Accessibility] Announced: {message}")
        
        # Update live region for screen readers
        if self.live_announcements and hasattr(self, 'live_region') and self.live_region:
            try:
                # Check if live region is properly connected to page
                if hasattr(self.live_region, 'page') and self.live_region.page:
                    # Update the live region value
                    self.live_region.value = message
                    self.live_region.update()
                    print(f"[Accessibility] Live region updated: {message}")
                else:
                    print(f"[Accessibility] Live region not connected to page, message: {message}")
            except Exception as e:
                print(f"[Accessibility] Live region update error: {e}")
        
        # Speak the message using TTS
        self._speak_text(message)
        
        # Show visual notification - use proper Flet snack bar method
        if self.screen_reader_mode or self.audio_feedback:
            try:
                snack = ft.SnackBar(
                    content=ft.Text(f"♿ {message}"),
                    duration=3000,  # Longer duration for accessibility
                    bgcolor=ft.Colors.BLUE_GREY_800,
                )
                # Use the proper Flet method for showing snack bars
                self.page.show_snack_bar(snack)
            except AttributeError:
                # Fallback for older Flet versions
                try:
                    self.page.snack_bar = snack
                    snack.open = True
                    self.page.update()
                except Exception as e:
                    print(f"[Accessibility] Could not show snack bar: {e}")
            except Exception as e:
                print(f"[Accessibility] Snack bar error: {e}")

    def _announce_with_debounce(self, message: str, event_type: str = ""):
        """Announce messages with debouncing and batching to keep screen readers in sync."""
        with self._announcement_lock:
            current_time = time.time()
            
            # Check if we should announce immediately or queue for batching
            time_since_last = current_time - self._last_announcement_time
            
            if time_since_last >= self._debounce_delay:
                # Enough time has passed, announce immediately
                if self._announcement_queue:
                    # Include any queued messages
                    queued_messages = " | ".join(self._announcement_queue)
                    combined_message = f"{queued_messages} | {message}"
                    self._announcement_queue.clear()
                    print(f"[Accessibility] Announcing batched messages: {combined_message}")
                    self._announce_change(combined_message)
                else:
                    # Just announce the single message
                    print(f"[Accessibility] Announcing immediate: {message}")
                    self._announce_change(message)
                
                self._last_announcement_time = current_time
            else:
                # Too soon since last announcement, add to queue
                print(f"[Accessibility] Queuing message: {message}")
                self._announcement_queue.append(message)
                
                # Set up a timer to flush the queue if it doesn't get flushed naturally
                def flush_queue():
                    time.sleep(self._batch_timeout)
                    with self._announcement_lock:
                        if self._announcement_queue:
                            queued_messages = " | ".join(self._announcement_queue)
                            self._announcement_queue.clear()
                            print(f"[Accessibility] Flushing queued messages: {queued_messages}")
                            self._announce_change(queued_messages)
                            self._last_announcement_time = time.time()
                
                # Start flush timer in background
                flush_thread = threading.Thread(target=flush_queue, daemon=True)
                flush_thread.start()

    # ADVANCED SCREEN READER METHODS - BETTER THAN NVDA
    
    def smart_announce(self, message: str, event_type: str = "general", priority: str = "normal", context: str = ""):
        """Advanced smart announcement with context awareness and user customization."""
        
        # Check if user wants this type of announcement
        setting_key = f"announce_{event_type}"
        if not self.announcement_settings.get(setting_key, True):
            return
            
        # Apply quiet mode filtering
        if self.quiet_mode and priority not in ["urgent", "critical"]:
            return
            
        # Check for recent duplicates
        if self._is_duplicate_message(message, event_type):
            return
            
        # Apply smart batching
        if self.smart_batching and self._should_batch_message(message, event_type):
            self._add_to_batch(message, event_type, priority, context)
            return
            
        # Apply context awareness
        if self.context_aware:
            message = self._add_context_to_message(message, context)
            
        # Apply user verbosity level
        message = self._adjust_message_verbosity(message, event_type)
        
        # Announce with appropriate method
        if priority in ["urgent", "critical"]:
            self._announce_nvda_style(message, priority="urgent")
        elif priority == "high":
            self._announce_nvda_style(message, priority="high")
        else:
            self._announce_nvda_style(message, priority="normal")
            
        # Track announcement for duplicate detection
        self._track_announcement(message, event_type)

    def _is_duplicate_message(self, message: str, event_type: str) -> bool:
        """Check if this message was recently announced to avoid spam."""
        current_time = time.time()
        
        # Clean old messages (older than 5 seconds)
        self._recent_announcements = [
            (msg, etype, timestamp) for msg, etype, timestamp in self._recent_announcements
            if current_time - timestamp < 5.0
        ]
        
        # Check for exact duplicates in recent announcements
        for recent_msg, recent_type, timestamp in self._recent_announcements:
            if recent_msg == message and recent_type == event_type:
                if current_time - timestamp < 2.0:  # Suppress duplicates within 2 seconds
                    print(f"[Accessibility] Suppressed duplicate: {message}")
                    return True
                    
        return False

    def _should_batch_message(self, message: str, event_type: str) -> bool:
        """Determine if message should be batched with similar messages."""
        filter_config = self._message_filters.get(event_type, {})
        
        if not filter_config.get("batch_similar", False):
            return False
            
        # Check frequency limits
        max_freq = filter_config.get("max_frequency", 1.0)
        current_time = time.time()
        
        # Count recent messages of this type
        recent_count = sum(1 for _, etype, timestamp in self._recent_announcements
                          if etype == event_type and current_time - timestamp < 1.0)
        
        return recent_count >= max_freq

    def _add_to_batch(self, message: str, event_type: str, priority: str, context: str):
        """Add message to batch for later announcement."""
        self._announcement_queue.append({
            "message": message,
            "type": event_type,
            "priority": priority,
            "context": context,
            "timestamp": time.time()
        })
        
        # Process batch if it gets too large
        if len(self._announcement_queue) > 5:
            self._process_announcement_batch()

    def _add_context_to_message(self, message: str, context: str) -> str:
        """Add contextual information to make announcements more informative."""
        if not context:
            return message
            
        # Add context based on current state
        if context == "tab_change":
            return f"Switched to {message}"
        elif context == "data_operation":
            return f"Data: {message}"
        elif context == "search":
            return f"Search: {message}"
        elif context == "error":
            return f"Error: {message}"
        elif context == "success":
            return f"Success: {message}"
        else:
            return f"{context}: {message}"

    def _adjust_message_verbosity(self, message: str, event_type: str) -> str:
        """Adjust message detail based on user verbosity preference."""
        if self.user_verbosity_level == "minimal":
            # Shorten messages for minimal verbosity
            if event_type == "progress":
                return message.split(".")[0]  # Just the main point
            elif event_type == "data_update":
                return "Data updated"
            elif len(message) > 50:
                return message[:47] + "..."
                
        elif self.user_verbosity_level == "verbose":
            # Add extra context for verbose mode
            if event_type == "tab_change":
                return f"{message}. Use Alt+number to switch tabs quickly."
            elif event_type == "data_loaded":
                return f"{message}. Use Ctrl+F to search, or browse with arrow keys."
                
        return message

    def _track_announcement(self, message: str, event_type: str):
        """Track announcement to prevent duplicates and for analytics."""
        self._recent_announcements.append((message, event_type, time.time()))
        
        # Keep only recent announcements (last 10)
        if len(self._recent_announcements) > 10:
            self._recent_announcements = self._recent_announcements[-10:]

    def _process_announcement_batch(self):
        """Process queued announcements intelligently."""
        if not self._announcement_queue:
            return
            
        # Group by type and priority
        urgent_messages = [msg for msg in self._announcement_queue if msg["priority"] in ["urgent", "critical"]]
        other_messages = [msg for msg in self._announcement_queue if msg["priority"] not in ["urgent", "critical"]]
        
        # Announce urgent messages immediately
        for msg_data in urgent_messages:
            self._announce_nvda_style(msg_data["message"], priority="urgent")
            
        # Batch similar non-urgent messages
        if other_messages:
            # Take the most recent message of each type
            latest_by_type = {}
            for msg_data in other_messages:
                msg_type = msg_data["type"]
                if msg_type not in latest_by_type or msg_data["timestamp"] > latest_by_type[msg_type]["timestamp"]:
                    latest_by_type[msg_type] = msg_data
                    
            # Announce the latest of each type
            for msg_data in latest_by_type.values():
                context_msg = self._add_context_to_message(msg_data["message"], msg_data["context"])
                self._announce_nvda_style(context_msg, priority="normal")
        
        # Clear the queue
        self._announcement_queue.clear()

    def set_verbosity_level(self, level: str):
        """Set user verbosity preference: 'minimal', 'normal', or 'verbose'."""
        if level in ["minimal", "normal", "verbose"]:
            self.user_verbosity_level = level
            self.smart_announce(f"Verbosity set to {level}", "setting_change", "normal")
            print(f"[Accessibility] Verbosity level set to: {level}")

    def toggle_quiet_mode(self):
        """Toggle quiet mode to suppress non-critical announcements."""
        self.quiet_mode = not self.quiet_mode
        status = "enabled" if self.quiet_mode else "disabled"
        self.smart_announce(f"Quiet mode {status}", "setting_change", "high")
        print(f"[Accessibility] Quiet mode: {status}")

    def configure_announcements(self, **settings):
        """Allow users to customize which types of announcements they want."""
        for key, value in settings.items():
            if key in self.announcement_settings:
                self.announcement_settings[key] = value
                print(f"[Accessibility] {key} set to {value}")
        
        self.smart_announce("Announcement preferences updated", "setting_change", "normal")

    def announce_with_prosody(self, message: str, emotion: str = "neutral"):
        """Announce with emotional prosody for better user experience."""
        if not self.enhanced_speech.get("use_prosody", False):
            self._speak_text_immediately(message)
            return
            
        try:
            if hasattr(self, 'tts_engine') and self.tts_engine:
                # Adjust speech properties based on emotion
                if emotion == "error" and self.enhanced_speech.get("emphasize_errors", True):
                    self.tts_engine.setProperty('rate', 200)  # Slower for errors
                    self.tts_engine.setProperty('pitch', 60)   # Higher pitch
                elif emotion == "success":
                    self.tts_engine.setProperty('rate', 280)  # Faster for success
                    self.tts_engine.setProperty('pitch', 40)   # Normal pitch
                elif emotion == "progress" and self.enhanced_speech.get("softer_progress", True):
                    self.tts_engine.setProperty('volume', 0.7)  # Softer volume
                elif emotion == "confirmation" and self.enhanced_speech.get("quick_confirmations", True):
                    self.tts_engine.setProperty('rate', 300)  # Very fast for confirmations
                
                self.tts_engine.stop()  # Stop any current speech
                self.tts_engine.say(message)
                self.tts_engine.runAndWait()
                
                # Reset to defaults
                self.tts_engine.setProperty('rate', 250)
                self.tts_engine.setProperty('volume', 0.95)
                
                print(f"[Accessibility] Prosodic speech ({emotion}): {message}")
            else:
                print(f"[Accessibility] TTS not available for prosodic speech: {message}")
        except Exception as e:
            print(f"[Accessibility] Prosodic speech error: {e}")
            # Fallback to regular speech
            self._speak_text_immediately(message)

    def _detect_nvda_screen_reader(self):
        """Detect if NVDA screen reader is running and optimize accordingly."""
        try:
            import psutil
            nvda_detected = False
            
            # Check for NVDA processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'nvda' in proc.info['name'].lower():
                        nvda_detected = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if nvda_detected:
                print("[Accessibility] NVDA detected - optimizing for NVDA timing")
                self._debounce_delay = 0.1  # Even faster for NVDA
                self._batch_timeout = 0.2   # Quicker batching with NVDA
                self.instant_speech = True
                self.interrupt_speech = True
            else:
                print("[Accessibility] No NVDA detected - using standard NVDA-like timing")
                
        except ImportError:
            print("[Accessibility] psutil not available - using default NVDA-like settings")
        except Exception as e:
            print(f"[Accessibility] NVDA detection error: {e}")

    def _speak_text_immediately(self, text: str):
        """Speak text immediately like NVDA - no delays, interrupts previous speech."""
        try:
            if hasattr(self, 'tts_engine') and self.tts_engine:
                # Stop any current speech immediately (NVDA behavior)
                self.tts_engine.stop()
                
                # Set NVDA-like speech properties
                self.tts_engine.setProperty('rate', 250)  # Faster speech like NVDA default
                self.tts_engine.setProperty('volume', 0.95)  # High volume
                
                # Speak immediately without queuing
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                print(f"[Accessibility] NVDA-like speech: {text}")
            else:
                print(f"[Accessibility] TTS not available: {text}")
        except Exception as e:
            print(f"[Accessibility] Immediate speech error: {e}")

    def _announce_nvda_style(self, message: str, priority: str = "normal"):
        """Announce message with NVDA-style priority and timing."""
        if priority == "urgent":
            # Urgent messages interrupt everything (like NVDA)
            self._speak_text_immediately(message)
        elif priority == "high":
            # High priority with minimal delay
            time.sleep(0.05)  # 50ms delay
            self._speak_text_immediately(message)
        else:
            # Normal priority with NVDA-like fast timing
            if self._nvda_mode:
                time.sleep(0.1)  # 100ms delay
                self._speak_text_immediately(message)
            else:
                self._announce_change(message)

    def cycle_color_blind_mode(self):
        """Cycle through color blindness support modes."""
        modes = ["none", "deuteranopia", "protanopia", "tritanopia"]
        current_index = modes.index(self.color_blind_mode)
        next_index = (current_index + 1) % len(modes)
        old_mode = self.color_blind_mode
        self.color_blind_mode = modes[next_index]
        
        print(f"[Accessibility] Cycling color blind mode: {old_mode} → {self.color_blind_mode}")
        
        self.apply_color_filter()
        self._save_preferences()
        
        # Update the dropdown if it exists
        try:
            if hasattr(self, 'page') and self.page:
                # Find and update the color blindness dropdown
                def update_dropdown(control):
                    if (hasattr(control, 'key') and 
                        control.key == "color_blindness_dropdown" and 
                        hasattr(control, 'value')):
                        control.value = str(next_index)
                        control.update()
                        print(f"[Accessibility] Updated dropdown to index {next_index}")
                        return True
                    return False
                
                # Search through page controls
                self._find_and_update_control(self.page, update_dropdown)
        except Exception as e:
            print(f"[Accessibility] Error updating dropdown: {e}")
        
        mode_names = {
            "none": "Normal Vision",
            "deuteranopia": "Deuteranopia (Red-Green)",
            "protanopia": "Protanopia (Red-Green)",
            "tritanopia": "Tritanopia (Blue-Yellow)"
        }
        
        self._announce_change(f"Color blindness mode: {mode_names[self.color_blind_mode]}")

    def _find_and_update_control(self, parent, update_func):
        """Recursively search for and update controls."""
        try:
            if update_func(parent):
                return True
                
            if hasattr(parent, 'controls'):
                for control in parent.controls:
                    if self._find_and_update_control(control, update_func):
                        return True
            elif hasattr(parent, 'content'):
                if self._find_and_update_control(parent.content, update_func):
                    return True
        except Exception as e:
            print(f"[Accessibility] Error in control search: {e}")
        return False

    def apply_color_filter(self):
        """Apply color blindness filters to the UI."""
        if not hasattr(self, 'page') or not self.page:
            print("[Accessibility] No page reference for color filter")
            return
            
        try:
            print(f"[Accessibility] Applying color filter: {self.color_blind_mode}")
            
            if self.color_blind_mode == "none":
                # Reset to normal colors - use default theme
                if self.high_contrast:
                    self.page.theme_mode = ft.ThemeMode.DARK
                else:
                    self.page.theme_mode = ft.ThemeMode.LIGHT
                self.page.theme = None  # Reset to default theme
                print("[Accessibility] Reset to normal color scheme")
            else:
                # Apply color blind friendly theme with more distinct colors
                color_schemes = {
                    "deuteranopia": {
                        # Safe colors for red-green color blindness
                        "primary": ft.Colors.BLUE_700,
                        "secondary": ft.Colors.ORANGE_700,
                        "error": ft.Colors.PURPLE_600,
                        "surface": ft.Colors.BLUE_GREY_50,
                        "background": ft.Colors.BLUE_GREY_100,
                    },
                    "protanopia": {
                        # Safe colors for another type of red-green color blindness
                        "primary": ft.Colors.INDIGO_700,
                        "secondary": ft.Colors.AMBER_700,
                        "error": ft.Colors.DEEP_PURPLE_600,
                        "surface": ft.Colors.INDIGO_50,
                        "background": ft.Colors.INDIGO_100,
                    },
                    "tritanopia": {
                        # Safe colors for blue-yellow color blindness
                        "primary": ft.Colors.RED_700,
                        "secondary": ft.Colors.GREEN_700,
                        "error": ft.Colors.PINK_700,
                        "surface": ft.Colors.RED_50,
                        "background": ft.Colors.RED_100,
                    }
                }
                
                scheme = color_schemes.get(self.color_blind_mode, {})
                if scheme:
                    # Create custom theme with color blind safe colors
                    custom_theme = ft.Theme(
                        color_scheme_seed=scheme.get("primary", ft.Colors.BLUE),
                        color_scheme=ft.ColorScheme(
                            primary=scheme.get("primary"),
                            secondary=scheme.get("secondary"),
                            error=scheme.get("error"),
                            surface=scheme.get("surface"),
                            background=scheme.get("background"),
                        )
                    )
                    self.page.theme = custom_theme
                    print(f"[Accessibility] Applied {self.color_blind_mode} color scheme")
                    
            # Update the entire page
            self.page.update()
            print(f"[Accessibility] Color filter applied successfully: {self.color_blind_mode}")
            
        except Exception as e:
            print(f"[Accessibility] Error applying color filter: {e}")
            import traceback
            traceback.print_exc()

    def get_color_safe_palette(self):
        """Get a color palette safe for all types of color blindness."""
        return {
            "safe_blue": "#0173B2",      # Safe blue
            "safe_orange": "#DE8F05",    # Safe orange  
            "safe_green": "#029E73",     # Safe green
            "safe_red": "#CC78BC",       # Safe pink (red substitute)
            "safe_yellow": "#ECE133",    # Safe yellow
            "safe_purple": "#56B4E9",    # Safe light blue (purple substitute)
            "safe_brown": "#D55E00",     # Safe vermillion
            "safe_gray": "#999999"       # Safe gray
        }

    def show_keyboard_shortcuts_overlay(self):
        """Show an overlay with all available keyboard shortcuts."""
        if not hasattr(self, 'page') or not self.page:
            return
            
        shortcuts_text = """
DATASCOPE KEYBOARD SHORTCUTS

Navigation:
• Tab / Shift+Tab - Navigate between controls
• Enter / Space - Activate buttons and controls
• Escape - Close dialogs and overlays

File Operations:
• Ctrl+O - Open file
• Ctrl+S - Save current view
• Ctrl+R - Refresh data

Accessibility:
• Ctrl+Shift+A - Toggle audio feedback
• Ctrl+Shift+H - Toggle high contrast
• Ctrl+Shift+S - Toggle screen reader mode
• Ctrl+Shift+T - Test accessibility features
• Ctrl+Shift+C - Cycle color blind modes
• Ctrl+Shift+O - Show this shortcuts overlay
• Ctrl+Shift+Y - Toggle speech-to-text

View Controls:
• Ctrl+1 to Ctrl+4 - Switch between tabs

Magnification Controls:
• Ctrl++ (Plus) - Increase magnification by 25%
• Ctrl+- (Minus) - Decrease magnification by 25%
• Ctrl+0 (Zero) - Reset magnification to 100%

TTS Controls:
• Ctrl+Shift+Up/Down - Adjust TTS speed
• Ctrl+Shift+Left/Right - Adjust TTS volume
• Ctrl+Shift+V - Cycle voice gender (female/male/any)
• Ctrl+Shift+G - Test current voice
        """
        
        overlay_dialog = ft.AlertDialog(
            title=ft.Text("Keyboard Shortcuts", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Text(
                    shortcuts_text,
                    size=14,
                    selectable=True
                ),
                width=500,
                height=400,
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Close",
                    on_click=lambda e: self._close_dialog(overlay_dialog)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = overlay_dialog
        overlay_dialog.open = True
        self.page.update()
        
        self._announce_change("Keyboard shortcuts overlay opened")

    def create_settings_controls(self) -> list:
        """Create accessibility settings controls for the Settings tab."""
        
        def on_high_contrast_change(e):
            self.high_contrast = e.control.value
            self.apply_high_contrast()
            self._save_preferences()
            self.page.update()
            
        def on_large_text_change(e):
            self.large_text = e.control.value
            self.apply_large_text()
            self._save_preferences()
            self.page.update()
            
        def on_reduce_motion_change(e):
            self.reduce_motion = e.control.value
            self._save_preferences()
            
        def on_screen_reader_change(e):
            self.screen_reader_mode = e.control.value
            self._save_preferences()
            # Test screen reader when enabled
            if self.screen_reader_mode:
                self._speak_text("Screen reader mode enabled")
                if self.sapi_voice:
                    self._speak_text("Windows SAPI integration is active")
            else:
                print("[Accessibility] Screen reader mode disabled")
            
        def on_audio_feedback_change(e):
            self.audio_feedback = e.control.value
            self._save_preferences()
            # Test audio feedback when enabled
            if self.audio_feedback:
                self._speak_text("Audio feedback enabled")
            else:
                print("[Accessibility] Audio feedback disabled")

        def on_live_announcements_change(e):
            self.live_announcements = e.control.value
            self._save_preferences()
            if self.live_announcements:
                self._announce_change("Live announcements enabled")
            else:
                print("[Accessibility] Live announcements disabled")

        def on_tts_speed_change(e):
            self.tts_speed = int(e.control.value)
            self._save_preferences()
            self._update_tts_settings()
            self._speak_text(f"Speech speed set to {self.tts_speed}")

        def on_tts_volume_change(e):
            self.tts_volume = e.control.value
            self._save_preferences()
            self._update_tts_settings()
            self._speak_text(f"Speech volume set to {int(self.tts_volume * 100)} percent")

        def on_tts_voice_change(e):
            selected_voice_id = e.control.value
            print(f"[Accessibility] Voice selection changed to: {selected_voice_id}")
            
            # Find the voice info for debugging
            selected_voice = self.get_voice_by_id(selected_voice_id)
            if selected_voice:
                print(f"[Accessibility] Selected voice: {selected_voice['name']} ({selected_voice['gender']})")
            
            # Use the set_voice method for proper voice setting
            if self.set_voice(selected_voice_id):
                print(f"[Accessibility] Voice successfully changed")
                # Test the new voice
                if selected_voice:
                    self._speak_text(f"Voice changed to {selected_voice['name']}, a {selected_voice['gender']} voice.")
                else:
                    self._speak_text("Voice changed.")
            else:
                print(f"[Accessibility] Failed to change voice")
                self._speak_text("Failed to change voice.")

        def on_tts_gender_change(e):
            self.tts_voice_gender = e.control.value
            print(f"[Accessibility] Gender preference changed to: {self.tts_voice_gender}")
            self._set_optimal_voice()
            self._save_preferences()
            current_voice = self.get_voice_by_id(self.tts_voice_id)
            voice_name = current_voice['name'] if current_voice else "Unknown"
            self._speak_text(f"{self.tts_voice_gender.capitalize()} voice selected. Now using {voice_name}")

        def on_color_blind_mode_change(e):
            """Handle color blind mode dropdown changes."""
            try:
                modes = ["none", "deuteranopia", "protanopia", "tritanopia"]
                selected_index = int(e.control.value)
                old_mode = self.color_blind_mode
                self.color_blind_mode = modes[selected_index]
                
                print(f"[Accessibility] Color blind mode changed: {old_mode} → {self.color_blind_mode}")
                
                self.apply_color_filter()
                self._save_preferences()
                
                mode_names = {
                    "none": "Normal Vision",
                    "deuteranopia": "Deuteranopia (Red-Green)",
                    "protanopia": "Protanopia (Red-Green)",
                    "tritanopia": "Tritanopia (Blue-Yellow)"
                }
                self._announce_change(f"Color mode: {mode_names[self.color_blind_mode]}")
                
            except Exception as ex:
                print(f"[Accessibility] Error changing color blind mode: {ex}")
                # Reset to safe mode
                self.color_blind_mode = "none"
                self.apply_color_filter()
                self._save_preferences()

        def on_focus_management_change(e):
            self.focus_management = e.control.value
            self._save_preferences()
            if self.focus_management:
                self._announce_change("Enhanced focus management enabled")
            else:
                print("[Accessibility] Enhanced focus management disabled")

        def on_error_prevention_change(e):
            self.error_prevention = e.control.value
            self._save_preferences()
            if self.error_prevention:
                self._announce_change("Error prevention enabled")
            else:
                print("[Accessibility] Error prevention disabled")

        controls = [
            ft.Text("♿ Accessibility", weight=ft.FontWeight.BOLD, style=ft.TextThemeStyle.TITLE_SMALL),
            
            ft.Switch(
                label="High Contrast Mode",
                value=self.high_contrast,
                on_change=on_high_contrast_change,
                tooltip="🎨 Enable high contrast colors for better visibility\n• Improves readability for low vision users\n• Uses bright, contrasting colors\n• Shortcut: Ctrl+H"
            ),
            
            ft.Switch(
                label="Large Text",
                value=self.large_text,
                on_change=on_large_text_change,
                tooltip="🔍 Increase text size for better readability\n• Makes all text larger\n• Helpful for vision impairments\n• Shortcut: Ctrl+Shift+L"
            ),
            
            ft.Switch(
                label="Reduce Motion",
                value=self.reduce_motion,
                on_change=on_reduce_motion_change,
                tooltip="🌊 Minimize animations and transitions\n• Reduces motion for motion sensitivity\n• Helps with vestibular disorders\n• Shortcut: Ctrl+Shift+M"
            ),
            
            ft.Switch(
                label="Screen Reader Mode",
                value=self.screen_reader_mode,
                on_change=on_screen_reader_change,
                tooltip="🔊 Optimize for screen readers\n• Enhanced compatibility with assistive technology\n• Improved ARIA labels and descriptions\n• Uses Windows SAPI when available\n• Shortcut: Ctrl+Shift+S"
            ),
            
            ft.Switch(
                label="Audio Feedback",
                value=self.audio_feedback,
                on_change=on_audio_feedback_change,
                tooltip="🔔 Enable audio notifications\n• Provides spoken feedback for actions\n• Uses text-to-speech for announcements\n• Helpful for visual impairments"
            ),
            
            ft.Switch(
                label="Live Announcements",
                value=self.live_announcements,
                on_change=on_live_announcements_change,
                tooltip="📢 Enable live region announcements\n• Screen reader real-time updates\n• Announces data changes immediately\n• ARIA live region support"
            ),
            
            ft.Switch(
                label="Enhanced Focus Management",
                value=self.focus_management,
                on_change=on_focus_management_change,
                tooltip="🎯 Improved keyboard navigation\n• Better focus indicators\n• Enhanced tab order\n• Focus trapping in dialogs"
            ),
            
            ft.Switch(
                label="Error Prevention",
                value=self.error_prevention,
                on_change=on_error_prevention_change,
                tooltip="⚠️ Prevent common user errors\n• Confirmation dialogs\n• Input validation\n• Warning messages"
            ),
            
            # Enhanced TTS Controls
            ft.Container(
                content=ft.Column([
                    ft.Text("🎛️ Text-to-Speech Settings:", weight=ft.FontWeight.BOLD, size=12),
                    
                    # Voice selection row
                    ft.Row([
                        ft.Text("Voice:", size=11),
                        ft.Dropdown(
                            label="Select Voice",
                            value=self.tts_voice_id if self.tts_voice_id else (self.tts_available_voices[0]["id"] if self.tts_available_voices else ""),
                            options=[
                                ft.dropdown.Option(v["id"], v["name"])
                                for v in self.tts_available_voices
                            ] if self.tts_available_voices else [ft.dropdown.Option("", "No voices available")],
                            on_change=on_tts_voice_change,
                            tooltip="Choose a specific voice for text-to-speech",
                            width=200,
                            disabled=not self.tts_available_voices
                        ),
                        ft.Dropdown(
                            label="Gender",
                            value=self.tts_voice_gender,
                            options=[
                                ft.dropdown.Option("female", "Female"),
                                ft.dropdown.Option("male", "Male"),
                                ft.dropdown.Option("any", "Any"),
                            ],
                            on_change=on_tts_gender_change,
                            tooltip="Choose preferred voice gender (Shortcut: Ctrl+Shift+V)",
                            width=120
                        ),
                    ], spacing=10),
                    
                    # Speed control row
                    ft.Row([
                        ft.Text("Speed:", size=11),
                        ft.Slider(
                            min=50,
                            max=300,
                            divisions=25,
                            value=self.tts_speed,
                            label=f"{self.tts_speed} WPM",
                            on_change=on_tts_speed_change,
                            tooltip="Adjust speech speed (50-300 words per minute)\nShortcuts: Ctrl+Shift+Up/Down"
                        ),
                    ]),
                    
                    # Volume control row
                    ft.Row([
                        ft.Text("Volume:", size=11),
                        ft.Slider(
                            min=0.1,
                            max=1.0,
                            divisions=9,
                            value=self.tts_volume,
                            label=f"{int(self.tts_volume * 100)}%",
                            on_change=on_tts_volume_change,
                            tooltip="Adjust speech volume (10-100%)\nShortcuts: Ctrl+Shift+Left/Right"
                        ),
                    ]),
                    
                    # Test voice button
                    ft.Row([
                        ft.ElevatedButton(
                            "🔊 Test Voice",
                            icon=ft.Icons.PLAY_ARROW,
                            on_click=lambda e: self.test_current_voice(),
                            tooltip="Test the current voice settings (Shortcut: Ctrl+Shift+G)"
                        ),
                        ft.Text(
                            f"Current: {self.get_voice_by_id(self.tts_voice_id)['name'] if self.tts_voice_id and self.get_voice_by_id(self.tts_voice_id) else 'Default'}", 
                            size=10, 
                            italic=True
                        ),
                    ], spacing=10),
                ]),
                padding=10,
                border_radius=5,
                margin=ft.margin.symmetric(vertical=5),
                visible=True,  # Always show TTS settings for debugging
                key="tts_settings_container"
            ),
            
            # Color Blindness Support
            ft.Container(
                content=ft.Column([
                    ft.Text("🌈 Color Blindness Support:", weight=ft.FontWeight.BOLD, size=12),
                    ft.Dropdown(
                        label="Color Vision Mode",
                        value=str(["none", "deuteranopia", "protanopia", "tritanopia"].index(self.color_blind_mode)),
                        options=[
                            ft.dropdown.Option("0", "Normal Vision"),
                            ft.dropdown.Option("1", "Deuteranopia (Red-Green)"),
                            ft.dropdown.Option("2", "Protanopia (Red-Green)"),
                            ft.dropdown.Option("3", "Tritanopia (Blue-Yellow)"),
                        ],
                        on_change=on_color_blind_mode_change,
                        tooltip="Select color vision type for optimized display\n• Adjusts color schemes for accessibility\n• Shortcut: Ctrl+Shift+C to cycle",
                        key="color_blindness_dropdown"
                    ),
                ]),
                padding=10,
                border_radius=5,
                margin=ft.margin.symmetric(vertical=5),
                key="color_blindness_container"
            ),
            
            # TTS Status Display
            ft.Container(
                content=ft.Column([
                    ft.Text("🔊 Audio System Status:", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text(
                        f"• pyttsx3 TTS: {'✅ Available' if self.tts_engine else '❌ Not available'}",
                        size=11,
                        color=ft.Colors.GREEN if self.tts_engine else ft.Colors.RED
                    ),
                    ft.Text(
                        f"• Windows SAPI: {'✅ Available' if self.sapi_voice else '❌ Not available'}",
                        size=11,
                        color=ft.Colors.GREEN if self.sapi_voice else ft.Colors.RED
                    ),
                    ft.ElevatedButton(
                        "Test Audio Feedback",
                        icon=ft.Icons.VOLUME_UP,
                        on_click=lambda e: self._test_audio_feedback(),
                        tooltip="Test the text-to-speech system",
                        disabled=not (self.tts_engine or self.sapi_voice)
                    ) if (self.tts_engine or self.sapi_voice) else ft.Text(
                        "⚠️ Install pyttsx3 or pywin32 for audio feedback",
                        size=11,
                        color=ft.Colors.ORANGE
                    ),
                ]),
                padding=10,
                border_radius=5,
                margin=ft.margin.symmetric(vertical=5),
                key="audio_status_container"
            ),
            
            ft.Row([
                ft.ElevatedButton(
                    "Show Keyboard Shortcuts",
                    icon=ft.Icons.KEYBOARD,
                    on_click=lambda e: self._show_shortcuts_with_debug(),
                    tooltip="View all available keyboard shortcuts"
                ),
                ft.ElevatedButton(
                    "Accessibility Help",
                    icon=ft.Icons.HELP,
                    on_click=lambda e: self._show_help_with_debug(),
                    tooltip="Get help with accessibility features"
                ),
            ], spacing=10),
            
            ft.Text(
                "💡 All accessibility settings are saved automatically and apply immediately. "
                "Use keyboard shortcuts for quick toggling during work sessions.",
                size=11,
                italic=True,
            ),
        ]
        
        return controls

    def _test_audio_feedback(self):
        """Test the audio feedback system."""
        test_message = "Audio feedback is working correctly. This is a test of the text-to-speech system."
        self._speak_text(test_message)
        print(f"[Accessibility] Audio test: {test_message}")

    def get_accessible_label(self, base_text: str, additional_info: str = "") -> str:
        """Generate accessible labels for screen readers."""
        if self.screen_reader_mode and additional_info:
            return f"{base_text}. {additional_info}"
        return base_text

    def apply_all_settings(self):
        """Apply all current accessibility settings."""
        if self.high_contrast:
            self.apply_high_contrast()
        if self.large_text:
            self.apply_large_text()
        if self.focus_indicators:
            self.apply_focus_indicators()
        
        print(f"[Accessibility] Applied all settings - HC:{self.high_contrast}, LT:{self.large_text}, RM:{self.reduce_motion}")

    def enhance_control_accessibility(self, control, label: str = "", description: str = "", role: str = ""):
        """Enhance a control with accessibility features."""
        if self.screen_reader_mode:
            if label and hasattr(control, 'tooltip'):
                if control.tooltip:
                    control.tooltip = f"{label}. {control.tooltip}"
                else:
                    control.tooltip = label
                    
            if description and hasattr(control, 'tooltip'):
                if control.tooltip:
                    control.tooltip = f"{control.tooltip}. {description}"
                else:
                    control.tooltip = description
        
        # Add focus indicators if enabled
        if self.focus_indicators and hasattr(control, 'focus_color'):
            control.focus_color = ft.Colors.AMBER_400
            
        return control

    def announce_data_event(self, event_type: str, details: str = ""):
        """Announce data-related events for screen readers with debouncing and batching."""
        messages = {
            "data_loaded": f"Dataset loaded successfully. {details}",
            "data_cleared": "Dataset cleared",
            "analysis_complete": f"Analysis completed. {details}",
            "search_complete": f"Search completed. {details}",
            "export_complete": f"Export completed. {details}",
            "export_started": f"Export started. {details}",
            "error": f"Error occurred. {details}",
        }
        
        message = messages.get(event_type, f"{event_type}. {details}")
        
        if self.screen_reader_mode or self.audio_feedback:
            self._announce_with_debounce(message, event_type)

    def announce_ui_change(self, change_type: str, details: str = ""):
        """Announce UI changes for screen readers."""
        if self.screen_reader_mode:
            message = f"{change_type}. {details}".strip()
            self._speak_text(message, priority="low")

    def configure_announcement_timing(self, debounce_delay: float = 0.5, batch_timeout: float = 1.0):
        """Configure timing for announcement debouncing and batching.
        
        Args:
            debounce_delay: Minimum time (seconds) between announcements
            batch_timeout: Maximum time (seconds) to wait before flushing queued messages
        """
        self._debounce_delay = max(0.1, min(2.0, debounce_delay))  # Clamp between 0.1 and 2.0 seconds
        self._batch_timeout = max(0.5, min(5.0, batch_timeout))    # Clamp between 0.5 and 5.0 seconds
        print(f"[Accessibility] Timing configured: debounce={self._debounce_delay}s, batch_timeout={self._batch_timeout}s")

    def connect_tab_system(self, tabs_control):
        """Connect accessibility shortcuts to the main tab system."""
        self.tabs_control = tabs_control
        
        # Update the tab focusing function
        def _focus_tab_connected(tab_index: int):
            if hasattr(self, 'tabs_control') and self.tabs_control:
                try:
                    if 0 <= tab_index < len(self.tabs_control.tabs):
                        self.tabs_control.selected_index = tab_index
                        self.page.update()
                        tab_names = ["Console", "Data View", "Data Tools", "Advanced", "Settings"]
                        tab_name = tab_names[tab_index] if tab_index < len(tab_names) else f"Tab {tab_index + 1}"
                        self._announce_change(f"Switched to {tab_name}")
                except Exception as e:
                    print(f"[Accessibility] Failed to focus tab {tab_index}: {e}")
        
        # Update shortcuts with connected function
        for i in range(5):
            self.shortcuts[f"alt+{i+1}"] = lambda idx=i: _focus_tab_connected(idx)

    def update_accessibility_theme_colors(self, theme_colors: dict):
        """Update theme colors for accessibility setting containers."""
        if not hasattr(self, 'page') or not self.page:
            return
            
        try:
            # Find and update accessibility containers by their keys
            def find_and_update_container(control, target_key, bg_color, border_color=None):
                """Recursively find containers by key and update their colors."""
                if hasattr(control, 'key') and control.key == target_key:
                    control.bgcolor = bg_color
                    if border_color and hasattr(control, 'border'):
                        control.border = ft.border.all(1, border_color)
                    return True
                
                if hasattr(control, 'content'):
                    if hasattr(control.content, 'controls'):
                        for child in control.content.controls:
                            if find_and_update_container(child, target_key, bg_color, border_color):
                                return True
                    else:
                        return find_and_update_container(control.content, target_key, bg_color, border_color)
                
                if hasattr(control, 'controls'):
                    for child in control.controls:
                        if find_and_update_container(child, target_key, bg_color, border_color):
                            return True
                
                return False
            
            # Update each accessibility container with theme-appropriate colors
            container_bg = theme_colors.get('surface_variant', ft.Colors.SURFACE_VARIANT)
            border_color = theme_colors.get('outline', ft.Colors.OUTLINE)
            
            # Update TTS settings container
            find_and_update_container(self.page, "tts_settings_container", container_bg, border_color)
            
            # Update color blindness container  
            find_and_update_container(self.page, "color_blindness_container", container_bg, border_color)
            
            # Update audio status container
            find_and_update_container(self.page, "audio_status_container", container_bg, border_color)
            
            # Also update the dropdown background
            def find_and_update_dropdown(control, target_key, bg_color):
                """Find dropdown by key and update its background."""
                if hasattr(control, 'key') and control.key == target_key:
                    if hasattr(control, 'bgcolor'):
                        control.bgcolor = bg_color
                    return True
                
                if hasattr(control, 'content'):
                    if hasattr(control.content, 'controls'):
                        for child in control.content.controls:
                            if find_and_update_dropdown(child, target_key, bg_color):
                                return True
                    else:
                        return find_and_update_dropdown(control.content, target_key, bg_color)
                
                if hasattr(control, 'controls'):
                    for child in control.controls:
                        if find_and_update_dropdown(child, target_key, bg_color):
                            return True
                
                return False
            
            # Update color blindness dropdown
            dropdown_bg = theme_colors.get('surface', ft.Colors.SURFACE)
            find_and_update_dropdown(self.page, "color_blindness_dropdown", dropdown_bg)
            
            print("[Accessibility] Updated theme colors for accessibility containers")
            
        except Exception as e:
            print(f"[Accessibility] Error updating theme colors: {e}")
