"""
Configuration file for the Aquaponics Monitoring System
Centralizes all configurable parameters for easy maintenance
"""

# Sensor Reading Configuration
SENSOR_READ_INTERVAL = 30  # seconds between sensor readings
THINGSPEAK_INTERVAL = 600  # seconds between ThingSpeak updates (10 minutes)

# Calculated values based on intervals
READINGS_PER_CYCLE = THINGSPEAK_INTERVAL // SENSOR_READ_INTERVAL  # 20 readings

# Email Configuration
ENABLE_SCHEDULED_EMAILS = True
DAILY_EMAIL_TIME = "06:00,18:00"  # HH:MM format for daily status email

# Email SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # TLS port for Gmail
EMAIL_TIMEOUT = 30  # Connection timeout in seconds

# Default email settings (can be overridden)
DEFAULT_SENDER_EMAIL = "wnccrobotics@gmail.com"
DEFAULT_SENDER_PASSWORD = (
    "loyqlzkxisojeqsr"  # Use App Password, not regular password
)

# Multiple recipients - add more email addresses here
DEFAULT_RECIPIENT_EMAILS = [
    "williamaloring@gmail.com",
    "williamloring@hotmail.com",
    "sarah.trook31@gmail.com",
    "zakwest85@gmail.com",
    "blackwelljakob22@gmail.com",
    "arood2016@icloud.com,",
]

# Email template constants
SUBJECT_PREFIX = "Aquaponics "
DEFAULT_SUBJECT = f"{SUBJECT_PREFIX} System Notification"

# Data Processing Configuration
TRIM_PERCENT = 0.1  # Percentage to trim from each end for outlier removal (10%)

# Sensor Thresholds for Alerts
WATER_TEMP_MIN = 65.0  # Fahrenheit
WATER_TEMP_MAX = 85.0  # Fahrenheit
HUMIDITY_MIN = 40.0  # Percentage
HUMIDITY_MAX = 80.0  # Percentage

# System Configuration
LOG_BACKUP_COUNT = 7  # Number of log files to keep
LOG_ROTATION = "midnight"  # When to rotate logs

# Network Configuration
THINGSPEAK_TIMEOUT = 30  # seconds
RETRY_DELAY = 5  # seconds to wait before retrying failed operations
RESTART_DELAY = (
    600  # seconds to wait before system restart after critical error
)

# Default pH Value (when sensor not available)
DEFAULT_PH = 7.0

# HTML Template File Paths
HTML_TEMPLATE_DIR = "html_templates"
ALERT_EMAIL_TEMPLATE = "alert_email.html"
STATUS_REPORT_TEMPLATE = "status_report.html"

# Camera Overlay Configuration
ENABLE_LABEL_OVERLAY = True  # Set to False to completely disable label feature
LABEL_TEXT = (
    "WNCC STEM Club Meeting Thursday at 4 PM in C1"  # Text to display on video
)
LABEL_CYCLE_MINUTES = 10  # Show label every X minutes
LABEL_DURATION_SECONDS = 30  # Show label for X seconds each cycle
LABEL_FONT_SCALE = 0.8  # Size of the label text
LABEL_TRANSPARENCY = (
    0.7  # Background transparency (0.0 = transparent, 1.0 = opaque)
)
TEXT_TRANSPARENCY = 0.9  # Text transparency for overlays (0.0 = fully transparent, 1.0 = fully opaque)
TEXT_COLOR = (0, 85, 204)  # Text color for overlays (BGR format - burnt orange)

# ------------------------ WEBSTREAM CONFIGURATION ------------------------- #
# These constants (values that don't change) control how the camera behaves.
# You can change these to adjust the video quality and frame rate.

# Fish Tank Camera (Camera 0) Frame Rate Settings
FISH_CAMERA_FRAME_RATE = (
    10.0  # How many pictures per second we want the fish camera to take
)
FISH_CAMERA_MAX_STREAM_FPS = (
    10.0  # Maximum FPS to send to clients for fish camera
)

# Plant Bed Camera (Camera 2) Frame Rate Settings
PLANT_CAMERA_FRAME_RATE = (
    5.0  # How many pictures per second we want the plant camera to take
)
PLANT_CAMERA_MAX_STREAM_FPS = (
    5.0  # Maximum FPS to send to clients for plant camera
)

# Note: Some cameras may ignore frame rate settings and use their own preferred rate.
# This is normal hardware behavior - the camera will tell us what it's actually using.

# Fish Tank Camera (Camera 0) Resolution
FISH_CAMERA_WIDTH = 1280
FISH_CAMERA_HEIGHT = 720

# Plant Bed Camera (Camera 2) Resolution
PLANT_CAMERA_WIDTH = 640
PLANT_CAMERA_HEIGHT = 480

# JPEG compression quality (0-100, higher = better quality but more bandwidth)
JPEG_QUALITY = 85  # Good balance between quality and bandwidth

# Skip camera detection if you know your camera index (faster startup)
# Set to 0, 1, 2, etc. if you know your camera index, or None to auto-detect
KNOWN_CAMERA_INDEX = 0

# Note: Overlay configuration is now imported from aquaponics_config.py
