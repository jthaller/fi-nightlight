# Architecture

## How fi-nightlight works end-to-end

### The infrastructure

```
Cloud Scheduler (cron: */5 * * * *)
        │
        │  HTTPS GET every 5 min, 24/7
        │  (authenticated via OIDC service account)
        │
        ▼
Cloud Function (fi-nightlight)
        │
        ├── Reads state from Firestore (1 document)
        ├── Calculates sunset locally (astral library)
        ├── If before sunset or after 1am → exits early, does nothing
        ├── If in active window → calls Fi API to check Baguette's zone
        ├── Toggles LED on/off based on zone status
        └── Writes updated state back to Firestore
```

### What each piece does

**Cloud Scheduler** — Google's cron service. It has one job: fire an HTTPS request at your function every 5 minutes, forever. It doesn't know anything about dogs or sunsets. It just pokes the function on a timer.

**Cloud Function** — A single Python function that spins up on each request, runs for 2-4 seconds, then shuts down. It's stateless — it doesn't remember anything between invocations. That's why we need Firestore.

**Firestore** — Holds one document: `{"led_on": false, "last_checked": "..."}`. This is how the function knows whether the LED is currently on. Without it, every invocation would be starting from scratch and might redundantly send on/off commands.

**Fi API (pytryfi)** — The function authenticates with your Fi credentials, asks Fi's servers where Baguette is, and sends LED commands. It never talks to the collar directly — everything goes through Fi's cloud.

### What happens each invocation

1. Scheduler sends GET request → function cold-starts (~2s)
2. Function loads state from Firestore: `{"led_on": false}`
3. Function calculates sunset for today at your coordinates (pure math, no API)
4. **Is it between sunset and 1am?**
   - **No** → save state, return `{"action": "inactive"}`, done (~0.5s)
   - **Yes** → continue to step 5
5. Connect to Fi API, fetch Baguette's `currPlaceName`
6. **Is she outside the safe zone?**
   - Outside + LED off → `turnOnOffLed(True)`, save `{"led_on": true}`
   - Inside + LED on → `turnOnOffLed(False)`, save `{"led_on": false}`
   - Otherwise → no change, save timestamp
7. Function shuts down until next invocation

### Cost breakdown

| Resource | Usage/day | Free tier | Cost |
|----------|-----------|-----------|------|
| Cloud Scheduler | 288 invocations | 3 jobs free | $0 |
| Cloud Function | 288 runs × ~3s each | 2M invocations/mo | $0 |
| Firestore | 288 reads + 288 writes | 50K reads + 20K writes/day | $0 |
| Cloud Logging | ~1 KB/invocation | 50 GB/month | $0 |

~95% of invocations (daytime) exit early in under 500ms and never touch the Fi API. Only the ~30 invocations between sunset and 1am actually do anything.
