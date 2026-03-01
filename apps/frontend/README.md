# Enterprise AIOps Frontend

## Run locally

```bash
npm install
npm run dev
```

Configure the backend base URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:9001/api/v1
```

Optional demo mode:

```bash
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_DEMO_USERNAME=demo
NEXT_PUBLIC_DEMO_PASSWORD=demo123
```

## Features

- LDAP-based sign in flow
- Command-center style navigation
- Independent modules:
  - incidents
  - alerts
  - health dashboards
  - logs insights
  - topology explorer
  - async RCA jobs

