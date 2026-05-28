# Frontend

Vue 3 + Vite mobile-first frontend for the Study Efficiency MVP.

This milestone implements only the core phone flow:

1. simple-login with nickname, optional grade and major
2. home page with current user and learning status
3. study timer after starting a session
4. end-session self-report form
5. history list from the backend
6. optional DeviceMotionEvent aggregation and motion feature upload
7. mobile collection safeguards: in-app back navigation, browser back handling, foreground/background reminders, and optional Screen Wake Lock

It does not implement model training/prediction pages, ECharts dashboards, JWT auth, or admin features. DeviceMotionEvent is implemented only as an optional auxiliary feature and never blocks the main study record flow.

Users choose their own nickname and should try to reuse the same nickname for every real collection session; optional grade and major do not create a separate user when the nickname is unchanged.

## Configuration

Create a local `.env` from `.env.example` if needed. Do not commit real environment files.

```bash
cp .env.example .env
```

Default development configuration:

```text
VITE_API_BASE_URL=/api
VITE_PROXY_TARGET=http://127.0.0.1:8000
```

`VITE_API_BASE_URL=/api` lets the Vite dev server proxy API calls to FastAPI and avoids browser CORS changes in the backend for this milestone. If the frontend is served separately from the backend in another environment, use a same-origin reverse proxy or set an API URL that the browser can access.

Production deployment for the current remote server uses:

```text
base=/study/
VITE_API_BASE_URL=/study-api
```

The public phone URL is:

```text
http://106.55.60.243/study/
```

## Install

Install dependencies locally under `frontend/node_modules`:

```bash
cd frontend
npm install
```

## Run

Start the backend first, then run:

```bash
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://127.0.0.1:5173`.

## Build

```bash
cd frontend
npm run build
```

The build script is configured for the remote `/study/` path and same-origin `/study-api` proxy.

## Backend API Used

- `POST /api/users/simple-login`
- `POST /api/sessions/start`
- `POST /api/sessions/end`
- `POST /api/sessions/{id}/abandon`
- `GET /api/sessions/list`
- `GET /api/sessions/{id}`
- `POST /api/motion/upload`

## Active Session Recovery

The frontend does not trust `localStorage` alone for an unfinished study session. On startup, when returning to the foreground, before continuing a study view, and before submitting the end-session form, it checks the saved active session through `GET /api/sessions/{id}`.

- If the backend returns an unfinished session, the timer resumes from the backend `start_time`.
- If the backend returns `404`, `completed`, or `abandoned`, the local active-session state and motion state are cleared.
- The study page uses "放弃本次学习" to call the backend abandon API before clearing local active-session state. A smaller local-cache repair entry remains for abnormal browser state only.


## Motion Detection

The study page attempts to use `DeviceMotionEvent` after a study session starts.

Browser behavior varies:

- Some mobile browsers support motion events directly after the page is opened in a secure context.
- iOS Safari-style browsers may require `DeviceMotionEvent.requestPermission()` from a user click. In that case the page shows an explicit authorization button.
- Browsers without motion support, insecure contexts, denied permission, or sessions with no valid motion samples show: `运动检测不可用，本次仍可正常记录学习。` or a no-data message.
- The page attempts to use `navigator.wakeLock` during an active study session to reduce accidental screen locking. Browser support varies, and unsupported or failed Wake Lock does not block the main flow.
- When the page is hidden or the phone locks, browser sensor events may pause. The frontend records foreground/background pause count and duration for display only; these values are not uploaded in the current P0 API.

The frontend only keeps aggregated values in memory for the current session. It does not store raw sensor events in `localStorage`.

Aggregated fields uploaded after a successful session end:

- `move_count`
- `shake_count`
- `still_ratio`
- `avg_acceleration`
- `max_acceleration`

Motion upload happens after `POST /api/sessions/end` succeeds. If `POST /api/motion/upload` fails, the study record remains saved and the user only receives a warning.

For local development, use `http://127.0.0.1:5173` or another secure-context-compatible setup where the browser permits motion APIs. Real mobile sensor testing usually requires opening the page on a phone browser.

## Mobile Navigation

The frontend is still a single `App.vue` state-driven application, not a router-based SPA. It uses `history.pushState` and `popstate` to make the phone browser back button return to the previous in-app view first.

Rules:

- History returns to home.
- Studying returns to home without ending the active session.
- End-session form returns to studying; if the form has draft content, the user is asked to confirm.
- Browser exit is blocked while a study session is active where supported by the browser.
