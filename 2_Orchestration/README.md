# Flight Radar Check-in Simulator

Local reference implementation for the Kubernetes retake. It intentionally has three runtime components: a static web app, a FastAPI service, and Redis. Redis is temporary state; restarting it resets the flight simulation.

## Run locally

```bash
docker compose up --build
```

Open http://localhost:8080. The API is available at http://localhost:8000/health.

The local API processes one automatic check-in every minute. The two manifests contain 60 passengers each, so automatic activity lasts at least two hours. Kubernetes will disable this in-process timer and use a CronJob instead.
