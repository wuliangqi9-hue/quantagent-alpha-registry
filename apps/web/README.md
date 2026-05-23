# Web App

Frontend dashboard for QuantAgent Alpha Registry.

## MVP Screens

- asset input;
- factor visualization;
- regime and strategy card;
- risk warnings;
- benchmark chart;
- Mantle proof panel.

## Design Goal

The first screen should be the working dashboard. Avoid a marketing landing
page. Judges should understand the product in 30 seconds and complete the demo
flow in under 3 minutes.

## API Base

By default, the frontend calls `/api/*`. This works for the single-service
deployment where FastAPI serves the built dashboard.

For split frontend/API deployment, set:

```text
VITE_API_URL=https://your-public-api.example.com/api
```

Do not use localhost for the final submitted build.
