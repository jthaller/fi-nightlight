"""Test your Fi connection and collar controls locally.

Usage:
    python test_connection.py              # check connection + zone status
    python test_connection.py --led-on     # turn LED on
    python test_connection.py --led-off    # turn LED off
    python test_connection.py --simulate   # simulate check cycle (ignores sunset)
"""

import argparse
import sys
import time

from dotenv import load_dotenv

from fi_nightlight.check import connect_fi, is_outside_safe_zone
from fi_nightlight.config import Config
from fi_nightlight.sunset import get_sunset_sunrise


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Test Fi collar connection")
    parser.add_argument("--led-on", action="store_true", help="Turn LED on")
    parser.add_argument("--led-off", action="store_true", help="Turn LED off")
    parser.add_argument("--simulate", action="store_true", help="Run simulated check cycle")
    args = parser.parse_args()

    config = Config.from_env()

    print(f"Connecting to Fi as {config.fi_username}...")
    try:
        fi, pet = connect_fi(config)
    except Exception as e:
        print(f"FAILED to connect: {e}")
        sys.exit(1)

    print(f"Connected! Found {len(fi.pets)} pet(s):")
    for p in fi.pets:
        print(f"  - {p.name}")
    print(f"\nUsing pet: {pet.name}")

    # Show location info
    print("\nFetching location...")
    pet.updatePetLocation(fi.session)
    area = getattr(pet, "areaName", "unknown")
    bases = [b.name for b in getattr(pet, "bases", []) if hasattr(b, "name")]
    outside = is_outside_safe_zone(pet)
    print(f"  Current area: {area}")
    print(f"  Known bases: {bases}")
    print(f"  Outside safe zone: {outside}")

    if args.led_on:
        print("\nTurning LED ON...")
        pet.turnOnOffLed(fi.session, True)
        pet.setLedColorCode(fi.session, config.led_color)
        print(f"  Done (color: #{config.led_color})")

    elif args.led_off:
        print("\nTurning LED OFF...")
        pet.turnOnOffLed(fi.session, False)
        print("  Done")

    elif args.simulate:
        print("\n--- Simulating check cycle ---")
        print("Checks every 30s for 3 minutes. Try moving dog in/out of zone.")
        print("Press Ctrl+C to stop.\n")

        led_on = False
        try:
            for i in range(6):
                pet.updatePetLocation(fi.session)
                outside = is_outside_safe_zone(pet)
                area = getattr(pet, "areaName", "unknown")

                if outside is None:
                    print(f"  [{i+1}/6] Zone unknown ({area}) — skipping")
                elif outside and not led_on:
                    print(f"  [{i+1}/6] OUTSIDE ({area}) → LED ON")
                    pet.turnOnOffLed(fi.session, True)
                    led_on = True
                elif not outside and led_on:
                    print(f"  [{i+1}/6] INSIDE ({area}) → LED OFF")
                    pet.turnOnOffLed(fi.session, False)
                    led_on = False
                else:
                    status = "outside" if outside else "inside"
                    led_status = "on" if led_on else "off"
                    print(f"  [{i+1}/6] {status} ({area}), LED {led_status} — no change")

                if i < 5:
                    time.sleep(30)
        except KeyboardInterrupt:
            pass
        finally:
            if led_on:
                print("\nCleaning up: turning LED off...")
                pet.turnOnOffLed(fi.session, False)
        print("Simulation complete.")

    else:
        sunset, sunrise = get_sunset_sunrise(config.latitude, config.longitude, config.timezone)
        print(f"\nSunset tonight:    {sunset.strftime('%I:%M %p')}")
        print(f"Sunrise tomorrow:  {sunrise.strftime('%I:%M %p')}")
        print("\nConnection test passed! Try --led-on, --led-off, or --simulate.")


if __name__ == "__main__":
    main()
