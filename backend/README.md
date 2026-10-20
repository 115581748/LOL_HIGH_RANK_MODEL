# RiftScale web API

This service keeps the Riot API key on the server and exposes only bounded
player-analysis jobs. It never accepts an API key from the browser and never
returns PUUIDs.

## Local development

```powershell
python -m pip install -r backend/requirements.txt
$env:RIOT_API_KEY = "development-key-for-private-testing-only"
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8080
```

Do not use a development key for a public alpha or beta. Apply for a Riot
production key before enabling the public GitHub Pages frontend.

## API

- `GET /health`
- `POST /v1/analyses` with `{ "riotId": "Name#TAG", "platform": "oc1", "matchCount": 10 }`
- `GET /v1/analyses/{jobId}` until `status` is `completed` or `failed`

The first Cloud Run version intentionally uses one process and one analysis
worker to protect the Riot quota. Configure one always-on instance with CPU
available outside requests. Move the unchanged HTTP contract to Cloud Tasks and
Firestore before increasing beyond one instance.

## Cloud Run deployment outline

1. Create a Secret Manager secret named `riftscale-riot-api-key`.
2. Build this repository root with `backend/Dockerfile`.
3. Deploy with HTTPS, one instance, concurrency 20, a 512 MiB or larger memory
   limit, and `RIOT_API_KEY` sourced from the secret.
4. Set `RIFTSCALE_ALLOWED_ORIGIN=https://115581748.github.io`.
5. Keep `min-instances=1`, `max-instances=1`, and CPU always allocated while
   this in-process queue implementation is in use.
6. Set a billing budget alert before public testing.

Example commands after installing and authenticating `gcloud` and creating an
Artifact Registry repository named `riftscale`:

```powershell
gcloud builds submit `
  --config backend/cloudbuild.yaml `
  --region australia-southeast1 `
  .

gcloud run deploy riftscale-api `
  --image australia-southeast1-docker.pkg.dev/PROJECT_ID/riftscale/riftscale-api:latest `
  --region australia-southeast1 `
  --allow-unauthenticated `
  --set-secrets RIOT_API_KEY=riftscale-riot-api-key:latest `
  --set-env-vars RIFTSCALE_ALLOWED_ORIGIN=https://115581748.github.io `
  --min-instances 1 --max-instances 1 --no-cpu-throttling `
  --concurrency 20 --memory 1Gi --timeout 300
```

The public endpoint is intentionally anonymous for the MVP, so CORS is not an
authentication mechanism. The application-level limits are a first guardrail;
add Cloud Armor/reCAPTCHA before sharing it broadly.
