#!/usr/bin/env python3
# This line tells the operating system to use Python 3 to run this script
"""Student-friendly pH sensor module.

This module reads pH from a DFRobot Gravity pH probe connected through
a Grove Base Hat (I2C ADC) on a Raspberry Pi. It contains two layers:
 - PHSensorReader: low-level I2C reader that communicates with the ADC
 - PHSensor: high-level wrapper that exposes convenient read functions

The code converts raw 12-bit ADC readings into voltages and then into pH
using a simple linear calibration (slope and offset). Students can read
the code to learn about I2C, ADC decoding, signal conversion, and basic
defensive programming (error handling, averaging, trimming outliers).

Dependencies (on Raspberry Pi):
pip install smbus2
"""

# Import the 'time' module - allows us to add delays and get timestamps
import time
# Import the 'logging' module - helps us record what the program is doing
import logging
# Import the 'os' module - lets us work with files and folders
import os
# Import the 'sys' module - gives us access to system-specific functions
import sys
# Import TimedRotatingFileHandler - creates log files that automatically rotate daily
from logging.handlers import TimedRotatingFileHandler

# Import the 'statistics' module - provides mathematical functions like mean (average)
import statistics
# Import type hints - helps document what type of data functions expect and return
from typing import List, Optional
# Import the 'json' module - lets us read and write JSON configuration files
import json

# Configuration constants (values that don't change during program execution)
# SENSOR_CHANNEL: tells us which pin on the Grove Base Hat the pH sensor is connected to (0 = A0)
SENSOR_CHANNEL = 0  # Which input pin on Grove Base Hat (A0, A1, A2, etc.)
# SAMPLING_INTERVAL: how long to wait between sensor readings (0.02 seconds = 20 milliseconds)
SAMPLING_INTERVAL = (
    0.02  # How often to read sensor (0.02 seconds = 20 milliseconds)
)
# ARRAY_LENGTH: how many individual readings to collect before calculating an average
ARRAY_LENGTH = 40  # How many readings to average together for stability

# Calibration and ADC constants (defaults)
# These defaults are used if no configuration file is present.
# DEFAULT_PH_SLOPE: how much the pH changes for each millivolt of sensor voltage change
DEFAULT_PH_SLOPE = -0.0169  # pH per mV (fallback default)
# DEFAULT_PH_OFFSET: the pH value when the voltage difference is zero (neutral point)
DEFAULT_PH_OFFSET = 7.0  # pH offset at 0 mV (fallback default)
# DEFAULT_CENTER_VOLTAGE: the voltage we measured when the sensor is in pH 7 (neutral) solution
DEFAULT_CENTER_VOLTAGE = (
    0.306  # V, empirical neutral point used in this project
)
# ADC_MAX: the maximum value the Analog-to-Digital Converter can read (12-bit = 4095)
ADC_MAX = 4095.0
# V_REF: the reference voltage used by the ADC (3.3 volts on Raspberry Pi)
V_REF = 3.3

# LAST_CALIB_PATH: stores the path to the calibration file we loaded (None means not loaded yet)
LAST_CALIB_PATH: str | None = None
# Print a message showing where this module file is located (helpful for debugging)
print(f"[PH] Module loaded from: {os.path.abspath(__file__)}")  # always prints

def load_calibration(config_path: str | None = None):
    """Load calibration values from JSON file and calculate slope/offset."""
    # The 'global' keyword lets us modify variables that exist outside this function
    global PH_SLOPE, PH_OFFSET, CENTER_VOLTAGE, V_REF, ADC_MAX, LAST_CALIB_PATH
    # Get a logger object for this module (helps us record messages about what's happening)
    _log = logging.getLogger(__name__)

    # Start by setting our calibration values to the defaults (in case file loading fails)
    PH_SLOPE = DEFAULT_PH_SLOPE  # How pH changes with voltage
    PH_OFFSET = DEFAULT_PH_OFFSET  # pH value at neutral point
    CENTER_VOLTAGE = DEFAULT_CENTER_VOLTAGE  # Voltage at pH 7

    # If no config file path was provided, try to find one
    if config_path is None:
        # First, check if there's an environment variable telling us where the calibration file is
        env_path = os.environ.get("PH_CALIB_PATH")
        # If the environment variable exists AND the file actually exists at that location
        if env_path and os.path.exists(env_path):
            config_path = env_path  # Use that path
        else:
            # Otherwise, look for the calibration file in the same folder as this script
            script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's folder
            config_path = os.path.join(script_dir, "ph_calibration.json")  # Build the file path

    # The 'try' block attempts to run code that might fail (like opening a file)
    try:
        # Remember which calibration file we're using
        LAST_CALIB_PATH = config_path
        # Print the full path to the calibration file we're loading
        print(f"[PH] Using calibration file: {os.path.abspath(config_path)}")  # always prints
        # Also log this information to the log file
        _log.info(f"Loading calibration from: {config_path}")
        # Open the JSON file in read mode ("r") with UTF-8 encoding
        with open(config_path, "r", encoding="utf-8") as f:
            # Read the JSON file and convert it to a Python dictionary
            data = json.load(f)

        # If the JSON file has old PH_SLOPE/PH_OFFSET values, warn that we'll ignore them
        # We recalculate these from the voltage measurements instead
        if "PH_SLOPE" in data or "PH_OFFSET" in data:
            _log.warning("Ignoring PH_SLOPE/PH_OFFSET in JSON; recomputing from voltages.")

        # Load V_REF and ADC_MAX from the file if they exist, otherwise keep the defaults
        # The .get() method returns the value if the key exists, or the default (2nd argument) if not
        V_REF = float(data.get("V_REF", V_REF))  # Reference voltage for the ADC
        ADC_MAX = float(data.get("ADC_MAX", ADC_MAX))  # Maximum ADC value

        # Try to get the voltage measurements for each calibration buffer solution
        ph_4_voltage = data.get("PH_4_VOLTAGE")  # Voltage when sensor was in pH 4 buffer
        ph_7_voltage = data.get("PH_7_VOLTAGE")  # Voltage when sensor was in pH 7 buffer
        ph_10_voltage = data.get("PH_10_VOLTAGE")  # Voltage when sensor was in pH 10 buffer

        # If all three calibration voltages are present (not None), calculate the calibration
        if ph_4_voltage is not None and ph_7_voltage is not None and ph_10_voltage is not None:
            # Convert the voltages from whatever type they are to floating-point numbers
            v4 = float(ph_4_voltage)  # Voltage at pH 4
            v7 = float(ph_7_voltage)  # Voltage at pH 7
            v10 = float(ph_10_voltage)  # Voltage at pH 10

            # Use pH 7 as our center point (where voltage difference = 0)
            CENTER_VOLTAGE = v7  # ΔV at pH7 = 0 mV

            # Calculate the slope (how pH changes with voltage) in pH per millivolt
            eps = 1e-12  # A tiny number to prevent division by zero
            # Calculate slope from pH 4 to pH 7: change in pH / change in voltage in mV
            s1_mV = (7.0 - 4.0) / ((v7 - v4 + eps) * 1000.0)   # pH/mV
            # Calculate slope from pH 7 to pH 10: change in pH / change in voltage in mV
            s2_mV = (10.0 - 7.0) / ((v10 - v7 + eps) * 1000.0) # pH/mV
            # Average the two slopes to get our final calibration slope
            PH_SLOPE = (s1_mV + s2_mV) / 2.0                   # pH/mV

            # Since we centered at pH 7, the offset is exactly 7.0
            PH_OFFSET = 7.0

            # Safety check: if the slope value is unrealistically large, it might be in wrong units
            # abs() returns the absolute value (removes negative sign for comparison)
            if abs(PH_SLOPE) > 0.5:  # Slope should be small (around 0.01-0.02 pH/mV)
                # Warn that the slope is wrong and try to fix it by dividing by 1000
                _log.warning(f"PH_SLOPE={PH_SLOPE:.6f} pH/mV unrealistic; scaling /1000 as if pH/V")
                PH_SLOPE = PH_SLOPE / 1000.0  # Convert from pH/V to pH/mV
            # Check again after correction - if still too large, use defaults
            if abs(PH_SLOPE) > 0.5:
                _log.warning("PH_SLOPE still unrealistic; reverting to default.")
                # Go back to the safe default values
                PH_SLOPE = DEFAULT_PH_SLOPE
                PH_OFFSET = DEFAULT_PH_OFFSET
                CENTER_VOLTAGE = DEFAULT_CENTER_VOLTAGE

            # Calculate what pH values we should get at each calibration voltage (for verification)
            # This helps us check if our calibration makes sense
            ph_at_v4 = PH_SLOPE * ((v4 - v7) * 1000.0) + PH_OFFSET  # Expected pH at 4 buffer voltage
            ph_at_v7 = PH_SLOPE * 0.0 + PH_OFFSET  # Expected pH at 7 buffer voltage (should be 7.0)
            ph_at_v10 = PH_SLOPE * ((v10 - v7) * 1000.0) + PH_OFFSET  # Expected pH at 10 buffer voltage

            # Log the calibration values we calculated
            _log.info(
                f"Calibration: slope={PH_SLOPE:.6f} pH/mV, offset={PH_OFFSET:.3f}, center={CENTER_VOLTAGE:.4f} V"
            )
            # Also print to console for immediate feedback
            print(f"[PH] Calibrated slope={PH_SLOPE:.6f} pH/mV, offset={PH_OFFSET:.3f}, center={CENTER_VOLTAGE:.4f} V")
            # Log what pH we predict at each calibration point
            _log.info(
                f"Predicted pH @ v4={v4:.4f}V -> {ph_at_v4:.3f}, v7={v7:.4f}V -> {ph_at_v7:.3f}, v10={v10:.4f}V -> {ph_at_v10:.3f}"
            )
        else:
            # If we're missing any of the calibration voltages, use the defaults
            _log.info("Calibration points missing; using defaults.")
            print("[PH] Calibration points missing; using defaults.")
    # Catch specific error if the file doesn't exist
    except FileNotFoundError:
        _log.warning(f"Calibration file not found at {config_path}; using defaults.")
        print(f"[PH] Calibration file not found at {config_path}; using defaults.")
    # Catch any other error that might occur while loading the file
    except Exception as e:
        _log.warning(f"Failed to load calibration file {config_path}: {e}; using defaults")
        print(f"[PH] Failed to load calibration file {config_path}: {e}; using defaults")


def _resolve_calib_path(config_path: str | None = None) -> str:
    """Resolve the calibration file path using env var or module folder."""
    if config_path and os.path.exists(config_path):
        return config_path
    env_path = os.environ.get("PH_CALIB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "ph_calibration.json")

def calibrate_voltage_for_ph(target_ph: float, samples: int = 20, channel: int = SENSOR_CHANNEL, config_path: str | None = None) -> dict:
    """Average 'samples' readings and store the voltage for the given buffer pH.
    Returns basic stats so the caller can display them."""
    cfg_path = _resolve_calib_path(config_path)
    key = None
    if abs(target_ph - 4.0) <= 0.5:
        key = "PH_4_VOLTAGE"
    elif abs(target_ph - 7.0) <= 0.5:
        key = "PH_7_VOLTAGE"
    elif abs(target_ph - 10.0) <= 0.5:
        key = "PH_10_VOLTAGE"
    else:
        raise ValueError("target_ph must be one of 4, 7, or 10")

    reader = PHSensorReader()
    volts: list[float] = []
    phs: list[float] = []
    for _ in range(max(1, int(samples))):
        reading = reader.read_raw(channel)
        volts.append(float(reading["voltage_v"]))
        phs.append(float(reading["ph"]))
        time.sleep(SAMPLING_INTERVAL)

    avg_v = sum(volts) / len(volts)
    avg_ph = sum(phs) / len(phs) if phs else float("nan")
    # Load, update, save JSON
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except Exception:
        data = {}
    data[key] = round(avg_v, 6)

    # Keep these fields if already present
    if "V_REF" not in data:
        data["V_REF"] = V_REF
    if "ADC_MAX" not in data:
        data["ADC_MAX"] = ADC_MAX

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"[PH] Calibrated {key} = {avg_v:.6f} V using {len(volts)} samples "
          f"(avg pH during sampling: {avg_ph:.3f}) -> {cfg_path}")

    # Reload calibration to recompute slope/offset and show predictions
    load_calibration(cfg_path)

    return {
        "avg_voltage_v": float(avg_v),
        "avg_ph": float(avg_ph),
        "samples": int(len(volts)),
    }

# Load calibration at module import time (will fall back to defaults)
load_calibration()

# Get logger for this module (no handlers configured here)
logger = logging.getLogger(__name__)


class PHSensorReader:
    """Reader that uses smbus2 i2c_rdwr to query the Grove Base Hat ADC."""
    # __init__ is a special method that runs when we create a new PHSensorReader object
    def __init__(
        self,
        addr: int = 0x08,  # I2C address of the ADC (0x08 is the default for Grove Base Hat)
        busnum: int = 1,  # Which I2C bus to use (1 is the default on Raspberry Pi)
        center_voltage: float | None = None,  # Optional: override the center voltage
    ):
        # Store the I2C address in the object so we can use it later
        self.addr = addr
        # Store the I2C bus number in the object
        self.busnum = busnum
        # Store the center voltage (use global if not provided, otherwise use the one passed in)
        self.center_voltage = float(CENTER_VOLTAGE if center_voltage is None else center_voltage)

    def _read_raw_bytes(self, channel: int = 0) -> List[int]:
        # Try to import the smbus2 library (needed for I2C communication)
        try:
            from smbus2 import i2c_msg, SMBus
        # If the import fails, show a helpful error message
        except Exception as e:
            raise RuntimeError(
                "smbus2 is required; install with 'pip install smbus2' and run on the Pi"
            ) from e

        # Optional validation commented out - could check if channel is between 0 and 3
        # if not (0 <= channel <= 3):
        #     raise ValueError("channel must be 0..3")

        # Open a connection to the I2C bus (the 'with' ensures it closes automatically)
        with SMBus(self.busnum) as bus:
            # Create a write message to tell the ADC which channel we want to read
            # [0x30, channel, 0x00, 0x00] is the command format for Grove Base Hat
            write = i2c_msg.write(self.addr, [0x30, channel, 0x00, 0x00])
            # Send the write message to the device
            bus.i2c_rdwr(write)
            # Create a read message to get 4 bytes of data back from the ADC
            read = i2c_msg.read(self.addr, 4)
            # Execute the read operation
            bus.i2c_rdwr(read)
            # Convert the received data to a Python list of integers
            data = list(read)
            # Print what we received (helpful for debugging)
            print("i2c_rdwr read:", data)

        # Return the list of bytes we read
        return data

    def read_raw(self, channel: int = 0) -> dict:
        # Read the raw bytes from the ADC
        data = self._read_raw_bytes(channel)

        # Try different ways to interpret the bytes (different ADC chips send data differently)
        candidates = []  # List to store possible interpretations
        # If we have at least 2 bytes of data
        if len(data) >= 2:
            # Try interpreting with low byte first: combine data[0] and data[1]
            # | is bitwise OR, << 8 means shift left 8 bits, & 0xFFFF keeps only 16 bits
            v0 = (data[0] | (data[1] << 8)) & 0xFFFF
            candidates.append(("low_first", v0))  # Add this interpretation to our list
        # If we have all 4 bytes
        if len(data) >= 4:
            # Try middle pair of bytes
            v1 = (data[2] | (data[3] << 8)) & 0xFFFF
            candidates.append(("mid_pair", v1))
            # Try high byte first
            v2 = (data[0] << 8) | data[1]
            candidates.append(("high_first", v2))

        # Find which interpretation gives us a valid ADC reading
        raw = None  # Will store the final raw ADC value
        chosen_method = None  # Will remember which method worked
        # Loop through each interpretation we tried
        for name, val in candidates:
            # Check if this value is within the valid range for our ADC
            if 0 <= val <= ADC_MAX:
                raw = int(val)  # Use this value
                chosen_method = name  # Remember which method worked
                break  # Stop looking - we found a good value

        # If none of the methods gave a valid reading, use a fallback
        if raw is None:
            # Mask to 12 bits (0x0FFF = 4095) as a last resort
            raw = ((data[0] | (data[1] << 8)) & 0x0FFF) if len(data) >= 2 else 0
            chosen_method = "fallback_mask12"

        # Convert the raw ADC number (0-4095) to voltage (0-3.3V)
        voltage_v = (raw / ADC_MAX) * V_REF
        # Calculate voltage difference from the center point, in millivolts
        voltage_mV = (voltage_v - self.center_voltage) * 1000.0

        # Safety check: make sure we're using the slope in the right units (pH per mV)
        slope_used = PH_SLOPE  # Start with the global slope value
        # If the slope is too large, it's probably in wrong units (pH/V instead of pH/mV)
        if abs(slope_used) > 0.5:
            logger.warning(f"PH_SLOPE seems per-Volt ({slope_used:.6f}); scaling /1000")
            slope_used = slope_used / 1000.0  # Convert to pH/mV

        # Calculate pH using the formula: pH = (slope × voltage_difference) + offset
        ph_unclamped = slope_used * voltage_mV + PH_OFFSET
        # Clamp pH to valid range (0-14) using min() and max()
        # max(0.0, ph) ensures pH is at least 0, then min(14.0, ...) ensures it's at most 14
        ph = min(14.0, max(0.0, ph_unclamped))

        # Log all the values we calculated (helpful for troubleshooting)
        logger.info(
            f"[DEBUG] Raw ADC: {raw}, V: {voltage_v:.4f}, Center: {self.center_voltage:.4f}, mV: {voltage_mV:.2f}, "
            f"slope_used(pH/mV): {slope_used:.6f}, offset: {PH_OFFSET:.3f}"
        )
        logger.info(f"[DEBUG] Calculated pH (clamped): {ph:.3f}")

        # Return all the information as a dictionary
        return {"raw": raw, "voltage_v": voltage_v, "voltage_mV": voltage_mV, "ph": ph, "raw_bytes": data, "chosen_method": chosen_method}

    def read_ph(self, channel: int = 0) -> float:
        # Get all the raw sensor data (including pH)
        r = self.read_raw(channel)
        # Extract just the pH value and return it as a float
        return float(r["ph"])

    def read_average(
        self,
        channel: int = 0,  # Which ADC channel to read from
        samples: int = 40,  # How many readings to take
        delay: float = 0.05,  # How long to wait between readings (seconds)
        trim: bool = True,  # Whether to remove outliers (highest and lowest values)
    ) -> Optional[float]:
        # Create an empty list to store pH readings
        vals: List[float] = []
        # Take 'samples' number of readings
        for _ in range(samples):  # _ means we don't need the loop counter value
            try:
                # Try to read pH and add it to our list
                vals.append(self.read_ph(channel))
            except Exception:
                # If reading fails, just skip it (pass = do nothing)
                pass
            # Wait before taking the next reading (sensor needs time to stabilize)
            time.sleep(delay)

        # If we didn't get any valid readings, raise an error
        if not vals:
            raise RuntimeError("no valid readings collected")

        # If trim is True and we have enough readings (5+), remove outliers
        if trim and len(vals) >= 5:
            vals_sorted = sorted(vals)  # Sort readings from lowest to highest
            vals = vals_sorted[1:-1]  # Keep everything except first (lowest) and last (highest)

        # Calculate and return the average (mean) of all the readings
        return float(statistics.mean(vals))


class PHSensor:
    """
    pH sensor wrapper class using the SMBus  reader.
    Public API is unchanged: `read_ph_sensor()` and `read_ph_averaged()`.
    """

    # __init__ runs when we create a new PHSensor object
    def __init__(self, channel: int = SENSOR_CHANNEL):
        """Initialize the pH sensor reader."""
        # Store which channel the sensor is connected to
        self.channel = channel
        # Keep track of the most recent pH reading (start with neutral pH 7.0)
        self.current_ph = 7.0
        # Remember the last time we sampled the sensor
        self.last_sampling_time = time.time()

        # Try to create the low-level sensor reader object
        try:
            # Create a PHSensorReader instance that does the actual I2C communication
            self.sensor = PHSensorReader()
            # Log that initialization was successful
            logger.info("pH sensor initialized successfully")
        # If something goes wrong during initialization, catch the error
        except Exception as e:
            # Log the error message
            logger.error(f"Failed to initialize pH sensor: {e}")
            # Re-raise the exception so the calling code knows initialization failed
            raise

    def read_ph_sensor(self) -> Optional[float]:
        """Return a single pH reading (float) or None on error."""
        # Try to read the pH value
        try:
            # Get pH reading from the sensor (using the stored channel number)
            ph = self.sensor.read_ph(channel=self.channel)
            # Make sure pH is in valid range (0-14)
            if ph is None:  # If sensor returned no value
                return None
            if ph < 0:  # If pH is negative, set it to 0
                ph = 0.0
            elif ph > 14:  # If pH is greater than 14, set it to 14
                ph = 14.0

            # Log the reading at DEBUG level (lower priority than INFO)
            logger.debug(f"pH sensor reading: {ph:.2f}")
            # Store this reading as our current pH
            self.current_ph = ph
            # Return the pH value
            return ph
        # If anything goes wrong (sensor disconnected, I2C error, etc.)
        except Exception as e:
            # Log the error so we know what went wrong
            logger.error(f"Error reading pH sensor: {e}")
            # Return None to indicate the reading failed
            return None

    def read_ph_averaged(
        self, samples: int = ARRAY_LENGTH,  # How many readings to average (default: 40)
        delay: float = SAMPLING_INTERVAL  # Delay between readings (default: 0.02 seconds)
    ) -> Optional[float]:
        """Return averaged pH value using the fallback averaging function."""
        # Try to read multiple pH values and average them
        try:
            # Call the sensor's read_average method which takes multiple readings
            ph = self.sensor.read_average(
                channel=self.channel, samples=samples, delay=delay
            )
            # Make sure pH is in valid range (0-14)
            if ph is None:  # If sensor returned no value
                return None
            if ph < 0:  # If pH is negative, set it to 0
                ph = 0.0
            elif ph > 14:  # If pH is greater than 14, set it to 14
                ph = 14.0

            # Store this averaged reading as our current pH
            self.current_ph = ph
            # Return the averaged pH value
            return ph
        # If anything goes wrong during averaging
        except Exception as e:
            # Log what went wrong
            logger.error(f"Error reading averaged pH: {e}")
            # Return None to indicate failure
            return None

    # Backwards-compatible internal helper left in place in case other code calls it
    def _read_sensor_voltage(self) -> Optional[float]:
        """Return sensor voltage in millivolts (float) or None on error."""
        try:
            raw = self.sensor.read_raw(channel=self.channel)
            vm = raw.get("voltage_mV")
            if vm is None:
                return None
            return float(vm)
        except Exception as e:
            logger.error(f"Error reading sensor voltage: {e}")
            return None


# Convenience function for backwards compatibility
def read_ph():
    """
    Convenience function to read pH sensor data.
    Creates a temporary sensor instance and returns pH reading.

    Returns:
        float: pH value (0-14 scale), or None if error
    """
    # Try to read a single pH value
    try:
        # Create a new PHSensor object
        sensor = PHSensor()
        # Read and return one pH value
        return sensor.read_ph_sensor()
    # If something goes wrong (sensor not connected, I2C error, etc.)
    except Exception as e:
        # Log what went wrong
        logger.error(f"Failed to read pH sensor: {e}")
        # Return None to show it failed
        return None


def read_ph_averaged():
    """
    Convenience function to read averaged pH sensor data.
    Creates a temporary sensor instance and returns averaged pH reading.

    Returns:
        float: Averaged pH value (0-14 scale), or None if error
    """
    # Try to read an averaged pH value
    try:
        # Create a new PHSensor object
        sensor = PHSensor()
        # Take several readings and average them
        val = sensor.read_ph_averaged()
        # Return the averaged value
        return val
    # If something goes wrong
    except Exception as e:
        # Log the error
        logger.error(f"Failed to read averaged pH sensor: {e}")
        # Return None to show it failed
        return None


# Diagnostic function to test all ADC channels
def test_all_channels():
    """Test all ADC channels to find where the sensor signal is connected."""
    print("Testing all ADC channels to find the pH sensor signal...")
    print("Looking for a channel that reads approximately 1.81V\n")
    
    try:
        reader = PHSensorReader()
        
        for channel in range(8):  # Test channels 0-7
            try:
                raw_data = reader.read_raw(channel)
                voltage = raw_data['voltage_v']
                raw_adc = raw_data['raw']
                print(f"Channel {channel}: Raw ADC = {raw_adc:4d}, Voltage = {voltage:.3f}V")
                
                # Check if this might be our pH sensor (around 1.8V)
                if 1.5 < voltage < 2.2:
                    print(f"  *** Channel {channel} might be your pH sensor! ***")
                    
            except Exception as e:
                print(f"Channel {channel}: Error - {e}")
                
    except Exception as e:
        print(f"Error initializing ADC reader: {e}")
    
    print("\nIf you found a channel with ~1.81V, update SENSOR_CHANNEL in the code.")

# Test function for standalone execution
def main():
    """Test function to verify pH sensor functionality."""
    # Print messages to tell the user what's happening
    print("Testing pH sensor...")
    print("Reading pH values every second...")
    print("Press Ctrl+C to exit\n")

    # Try to run the main sensor reading loop
    try:
        # Create a new PHSensor object (this initializes the sensor)
        sensor = PHSensor()

        # Keep reading forever (until user presses Ctrl+C)
        while True:
            # Read one pH value from the sensor
            ph_value = sensor.read_ph_sensor()

            # Check if we got a valid reading
            if ph_value is not None:
                # Print the pH value with 2 decimal places (.2f means 2 decimals)
                print(f"pH: {ph_value:.2f}")
            else:
                # If reading failed, print an error message
                print("Failed to read pH sensor")

            # Wait 1 second before reading again
            time.sleep(1)

    # This catches when user presses Ctrl+C to stop the program
    except KeyboardInterrupt:
        print("\nProgram stopped")
    # This catches any other error that might occur
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Configure file and console logging only when run directly
    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    # Create logs directory relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # File handler with daily rotation, keep 7 days
    log_file_path = os.path.join(logs_dir, "ph_sensor_ts.log")
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",
        interval=1,
        backupCount=7,
    )
    file_handler.setFormatter(log_formatter)
    # Add date to rotated log files
    file_handler.suffix = "%Y-%m-%d"

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # Configure logging with our handlers
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    logger.info(f"Running module: {os.path.abspath(__file__)}")
    load_calibration()

    import argparse
    parser = argparse.ArgumentParser(description="pH sensor reader")
    parser.add_argument(
        "--show-calib",
        action="store_true",
        help="Print the currently loaded calibration and exit",
    )
    parser.add_argument(
        "--test-channels",
        action="store_true", 
        help="Test all ADC channels to find the pH sensor signal",
    )
    parser.add_argument("--calibrate", type=float, choices=[4.0, 7.0, 10.0],
                        help="Average readings and store voltage for the given buffer (4, 7, or 10).")
    parser.add_argument("--samples", type=int, default=40,
                        help="Number of readings to average during calibration (default: 40).")
    parser.add_argument("--channel", type=int, default=SENSOR_CHANNEL,
                        help="ADC channel to use (default: SENSOR_CHANNEL).")
    parser.add_argument("--calib-path", type=str, default=None,
                        help="Override path to ph_calibration.json.")
    args = parser.parse_args()

    if args.calibrate is not None:
        result = calibrate_voltage_for_ph(args.calibrate, samples=args.samples, channel=args.channel, config_path=args.calib_path)
        # Exit after calibration
        print("Loaded calibration values:")
        print(f"  MODULE FILE      = {os.path.abspath(__file__)}")
        print(f"  CALIBRATION FILE = {_resolve_calib_path(args.calib_path)}")
        print(f"  PH_SLOPE         = {PH_SLOPE}")
        print(f"  PH_OFFSET        = {PH_OFFSET}")
        print(f"  CENTER_VOLTAGE   = {CENTER_VOLTAGE}")
        print(f"  AVG PH (CAL)     = {result.get('avg_ph', float('nan')):.3f} over {result.get('samples', 0)} samples")
        raise SystemExit(0)

    if args.show_calib:
        print("Loaded calibration values:")
        print(f"  MODULE FILE      = {os.path.abspath(__file__)}")
        print(f"  CALIBRATION FILE = {LAST_CALIB_PATH}")
        print(f"  PH_SLOPE         = {PH_SLOPE}")
        print(f"  PH_OFFSET        = {PH_OFFSET}")
        print(f"  CENTER_VOLTAGE   = {CENTER_VOLTAGE}")
        sys.exit(0)
        
    if args.test_channels:
        test_all_channels()
        sys.exit(0)

    # Temporarily run channel test first, then normal operation
    print("=== RUNNING CHANNEL TEST FIRST ===")
    test_all_channels()
    print("\n=== NOW RUNNING NORMAL PH SENSOR TEST ===\n")
    main()
