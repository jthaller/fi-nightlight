# fi-nightlight

Automatically turn on your dog's Fi collar LED when they leave the safe zone after sunset, and turn it off when they return.

## How it works

1. Calculates sunset time daily for your location (offline, no API needed)
2. After sunset, polls Fi every 5 minutes to check zone status
3. **Dog leaves zone** → LED turns on
4. **Dog returns** → LED turns off
5. At 1am (configurable), ensures LED is off and stops until next sunset

Handles multiple trips — LED toggles reactively on every check.

## Quick Start (Local)

```bash
git clone https://github.com/youruser/fi-nightlight.git
cd fi-nightlight
python -m venv .venv && source .venv/bin/activate
pip install -e ".[local]"
cp .env.example .env   # edit with your Fi login + home coordinates
```

Test your connection first:

```bash
python test_connection.py              # verify credentials + zone status
python test_connection.py --led-on     # turn LED on (check the collar!)
python test_connection.py --led-off    # turn LED off
python test_connection.py --simulate   # 3-minute check cycle
```

Then run the automation:

```bash
python run.py
```

## Docker

```bash
cp .env.example .env   # edit with your config
docker compose -f docker/docker-compose.yml up -d
```

## Google Cloud (Free Tier)

A single Cloud Function runs every 5 minutes and exits early if it's before sunset or after the cutoff hour. Well within free tier (~288 invocations/day).

```bash
# Set env vars, then:
chmod +x gcp/deploy.sh && ./gcp/deploy.sh
```

The function is authenticated (IAM) — not publicly accessible.

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FI_USERNAME` | Yes | — | Fi app email |
| `FI_PASSWORD` | Yes | — | Fi app password |
| `LATITUDE` | Yes | — | Home latitude |
| `LONGITUDE` | Yes | — | Home longitude |
| `TIMEZONE` | No | `America/New_York` | IANA timezone |
| `PET_NAME` | No | First pet | Pet to monitor |
| `CUTOFF_HOUR` | No | `1` | Stop checking at this hour (0-23) |
| `POLL_INTERVAL_MINUTES` | No | `2` | Minutes between checks (when outside) |
| `SLOW_POLL_INTERVAL_MINUTES` | No | `5` | Minutes between checks (when inside) |
| `LED_COLOR` | No | `7` | Fi color code (2=Red 3=Green 4=Blue 5=Purple 6=Yellow 7=Cyan 8=White) |
| `STATE_FILE` | No | `state.json` | Local state file path |

## Battery Impact

- **Polling the API does NOT drain collar battery** — reads from Fi's cloud servers
- **LED on** uses minimal extra battery (designed for walks)
- **Lost Dog Mode is NOT used** — that's what drains battery fast

## Contributing

PRs welcome! Ideas for contributors:

- Multiple pets support
- LED color based on distance from home
- Push notifications (Pushover/Telegram)
- Home Assistant integration

## License

MIT
