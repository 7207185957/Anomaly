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

