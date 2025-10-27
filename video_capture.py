#!/home/pi/FishCam/.venv/bin/python
"""
Fish Tank Video Recorder
Simple menu-based program to capture video from the fish camera
"""

import cv2
import os
import time
from datetime import datetime

# Import camera settings
from config import (
    FISH_CAMERA_WIDTH,
    FISH_CAMERA_HEIGHT,
    FISH_CAMERA_FRAME_RATE,
)


def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def show_menu():
    """Display the main menu."""
    clear_screen()
    print("=" * 50)
    print("    FISH TANK VIDEO RECORDER")
    print("=" * 50)
    print()
    print("1. Record 30 second video")
    print("2. Record 1 minute video")
    print("3. Record 5 minute video")
    print("4. Record custom duration")
    print("5. View recording settings")
    print("6. Exit")
    print()
    print("=" * 50)


def record_video(duration_seconds):
    """
    Record video from fish camera for specified duration.
    
    Args:
        duration_seconds: How long to record in seconds
    """
    print(f"\nPreparing to record {duration_seconds} seconds of video...")
    
    # Open camera
    print("Opening fish camera (Camera 0)...")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        return False
    
    print("✓ Camera opened successfully")
    
    # Configure camera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FISH_CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FISH_CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FISH_CAMERA_FRAME_RATE)
    
    # Get actual settings
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Resolution: {width}x{height} @ {fps} FPS")
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs('videos', exist_ok=True)
    output_file = f"videos/fish_{timestamp}.mp4"
    
    print(f"Output file: {output_file}")
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print("ERROR: Could not create video file!")
        cap.release()
        return False
    
    print("\n🔴 RECORDING...")
    print("Press Ctrl+C to stop early\n")
    
    start_time = time.time()
    frame_count = 0
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            # Check if done
            if elapsed >= duration_seconds:
                break
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                print("Warning: Failed to read frame")
                continue
            
            # Write frame
            out.write(frame)
            frame_count += 1
            
            # Show progress every second
            if frame_count % int(fps) == 0:
                remaining = duration_seconds - elapsed
                print(f"  Time remaining: {int(remaining)} seconds ({frame_count} frames)", end='\r')
        
        print()  # New line after progress
        
    except KeyboardInterrupt:
        print("\n\nRecording stopped by user")
    
    finally:
        # Cleanup
        elapsed = time.time() - start_time
        out.release()
        cap.release()
        
        print(f"\n✓ Recording complete!")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Frames: {frame_count}")
        print(f"  File: {output_file}")
        
        # Check file size
        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"  Size: {size_mb:.1f} MB")
    
    return True


def show_settings():
    """Display current recording settings."""
    clear_screen()
    print("=" * 50)
    print("    CURRENT SETTINGS")
    print("=" * 50)
    print()
    print(f"Camera: Fish Tank (Camera 0)")
    print(f"Resolution: {FISH_CAMERA_WIDTH}x{FISH_CAMERA_HEIGHT}")
    print(f"Frame Rate: {FISH_CAMERA_FRAME_RATE} FPS")
    print(f"Output Format: MP4")
    print(f"Output Directory: ./videos/")
    print()
    print("=" * 50)
    input("\nPress Enter to continue...")


def main():
    """Main program loop."""
    while True:
        show_menu()
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            record_video(30)
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            record_video(60)
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            record_video(300)
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            try:
                duration = int(input("\nEnter duration in seconds: "))
                if duration > 0:
                    record_video(duration)
                else:
                    print("Duration must be positive!")
            except ValueError:
                print("Invalid input! Please enter a number.")
            input("\nPress Enter to continue...")
            
        elif choice == '5':
            show_settings()
            
        elif choice == '6':
            clear_screen()
            print("\nGoodbye!\n")
            break
            
        else:
            print("\nInvalid choice! Please enter 1-6.")
            time.sleep(1)


if __name__ == "__main__":
    main()
