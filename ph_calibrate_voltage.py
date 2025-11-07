#!/usr/bin/env python3
"""
Quick utility to read the current pH sensor voltage and perform calibration.

- Reads from the Grove Base Hat ADC via PHSensorReader (I2C)
- Prints absolute voltage (V), delta from center (mV), and raw ADC value
- Menu options to average samples, change channel/delay, and calibrate for pH 4/7/10

Run on the Raspberry Pi with the Grove Base Hat attached.
"""

import sys
import time

try:
    # Import reader and defaults from the existing module
    from ph_sensor_ts import (
        PHSensorReader,
        SENSOR_CHANNEL,
        SAMPLING_INTERVAL,
        load_calibration,
        calibrate_voltage_for_ph,
    )

    # Also import the module itself to access live calibration values at runtime
    import ph_sensor_ts as ph
except Exception as e:
    print(
        "Error: Unable to import ph_sensor_ts. Run this from the FishCam folder and ensure dependencies are installed."
    )
    print(f"Details: {e}")
    sys.exit(1)


def read_voltage(
    channel: int, samples: int, delay: float, show_each: bool
) -> int:
    """Read voltage one or more times and print results. Returns process exit code."""
    # Load calibration so reference values (V_REF/ADC_MAX/center) are correct
    load_calibration()

    reader = PHSensorReader()

    sum_v = 0.0
    sum_mv = 0.0
    last_raw = None

    for i in range(samples):
        try:
            r = reader.read_raw(channel)
        except RuntimeError as re:
            # Likely smbus2 missing or not running on Pi
            print(f"I2C error: {re}")
            return 2
        except Exception as e:
            print(f"Read error: {e}")
            return 3

        v = float(r["voltage_v"])  # absolute voltage in Volts
        mv = float(r["voltage_mV"])  # delta from CENTER_VOLTAGE in millivolts
        raw = int(r["raw"])  # raw ADC code (0..4095)
        last_raw = raw

        sum_v += v
        sum_mv += mv

        if show_each and samples > 1:
            print(f"Sample {i+1:02d}: {v:.4f} V | Δ {mv:+7.2f} mV | raw {raw}")

        if i + 1 < samples:
            time.sleep(max(0.0, delay))

    avg_v = sum_v / max(1, samples)
    avg_mv = sum_mv / max(1, samples)

    if samples > 1:
        print(f"Averaged over {samples} samples:")

    print(f"Voltage: {avg_v:.4f} V")
    print(f"Delta from center: {avg_mv:+.2f} mV")
    if last_raw is not None:
        print(f"Raw ADC: {last_raw}")

    return 0


def perform_calibration(target_ph: float, samples: int, channel: int) -> None:
    """Guide the user and perform calibration for a target pH buffer."""
    print("\n=== Calibration Wizard ===")
    print(f"Target buffer pH: {target_ph}")
    print(f"Channel: {channel} | Samples: {samples}")
    print(
        "1) Rinse the probe with distilled water and gently blot dry (don't rub)"
    )
    print(
        f"2) Place the probe into the pH {target_ph:.0f} calibration solution"
    )
    print("3) Gently swirl, then let it stabilize (no bubbles, no movement)")
    input("Press Enter to start sampling...")

    try:
        # This will save the averaged voltage for the given buffer in the calibration file
        result = calibrate_voltage_for_ph(
            target_ph, samples=samples, channel=channel
        )
    except Exception as e:
        print(f"Calibration failed: {e}")
        return

    # Show summary
    avg_v = result.get("avg_voltage_v")
    avg_ph = result.get("avg_ph")
    print("\nCalibration sample summary:")
    if avg_v is not None:
        print(f"  Avg Voltage (V): {avg_v:.6f}")
    if avg_ph is not None:
        print(f"  Avg pH during sampling: {avg_ph:.3f}")

    # Display current calibration values loaded in the module
    try:
        # load_calibration already called inside calibrate_voltage_for_ph, but we call again for safety
        load_calibration(getattr(ph, "LAST_CALIB_PATH", None))
        print("\nUpdated calibration:")
        print(
            f"  Calibration file: {getattr(ph, 'LAST_CALIB_PATH', 'unknown')}"
        )
        print(f"  V_REF         : {getattr(ph, 'V_REF', 'n/a')}")
        print(f"  ADC_MAX       : {getattr(ph, 'ADC_MAX', 'n/a')}")
        print(f"  CENTER_VOLTAGE: {getattr(ph, 'CENTER_VOLTAGE', 'n/a')}")
        print(f"  PH_SLOPE      : {getattr(ph, 'PH_SLOPE', 'n/a')}")
        print(f"  PH_OFFSET     : {getattr(ph, 'PH_OFFSET', 'n/a')}")
    except Exception as e:
        print(f"Warning: could not display calibration details: {e}")


def prompt_int(prompt: str, default: int) -> int:
    """Prompt for an integer with a default value."""
    try:
        s = input(f"{prompt} [{default}]: ").strip()
        if s == "":
            return default
        return int(s)
    except Exception:
        print("Invalid input; keeping previous value.")
        return default


def prompt_float(prompt: str, default: float) -> float:
    """Prompt for a float with a default value."""
    try:
        s = input(f"{prompt} [{default}]: ").strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        print("Invalid input; keeping previous value.")
        return default


def main() -> int:
    # Runtime configuration (editable from the menu)
    channel = SENSOR_CHANNEL
    samples = 1
    delay = SAMPLING_INTERVAL
    show_each = False

    while True:
        print("\n=== pH Voltage Reader ===")
        print(f"Channel     : {channel}")
        print(f"Samples     : {samples}")
        print(f"Delay (sec) : {delay}")
        print(f"Show each   : {'ON' if show_each else 'OFF'}")
        print("---------------------------")
        print("1) Read once")
        print("2) Read averaged")
        print("3) Set channel")
        print("4) Set samples")
        print("5) Set delay")
        print("6) Toggle show-each")
        print("7) Calibrate pH 4")
        print("8) Calibrate pH 7")
        print("9) Calibrate pH 10")
        print("10) Show current calibration")
        print("11) Exit")

        choice = input("Select an option (1-11): ").strip()

        if choice == "1":
            # Single sample (force samples=1 regardless of current setting)
            read_voltage(
                channel=channel, samples=1, delay=delay, show_each=False
            )
        elif choice == "2":
            read_voltage(
                channel=channel,
                samples=max(1, samples),
                delay=delay,
                show_each=show_each,
            )
        elif choice == "3":
            channel = prompt_int("Enter ADC channel (e.g., 0 for A0)", channel)
        elif choice == "4":
            samples = max(
                1, prompt_int("Enter number of samples to average", samples)
            )
        elif choice == "5":
            delay = max(
                0.0,
                prompt_float("Enter delay between samples (seconds)", delay),
            )
        elif choice == "6":
            show_each = not show_each
        elif choice == "7":
            perform_calibration(4.0, samples=max(1, samples), channel=channel)
        elif choice == "8":
            perform_calibration(7.0, samples=max(1, samples), channel=channel)
        elif choice == "9":
            perform_calibration(10.0, samples=max(1, samples), channel=channel)
        elif choice == "10":
            try:
                load_calibration(getattr(ph, "LAST_CALIB_PATH", None))
                print("\nCurrent calibration:")
                print(
                    f"  Calibration file: {getattr(ph, 'LAST_CALIB_PATH', 'unknown')}"
                )
                print(f"  V_REF         : {getattr(ph, 'V_REF', 'n/a')}")
                print(f"  ADC_MAX       : {getattr(ph, 'ADC_MAX', 'n/a')}")
                print(
                    f"  CENTER_VOLTAGE: {getattr(ph, 'CENTER_VOLTAGE', 'n/a')}"
                )
                print(f"  PH_SLOPE      : {getattr(ph, 'PH_SLOPE', 'n/a')}")
                print(f"  PH_OFFSET     : {getattr(ph, 'PH_OFFSET', 'n/a')}")
            except Exception as e:
                print(f"Warning: could not display calibration details: {e}")
        elif choice == "11":
            print("Goodbye!")
            return 0
        else:
            print("Invalid choice. Please pick 1-11.")


if __name__ == "__main__":
    sys.exit(main())
