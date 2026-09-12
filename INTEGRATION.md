# AdminIE Chatbot — Integration Guide

This document is for the technical team embedding the AdminIE AI Support Assistant into an existing web application.

---

## What You Are Embedding

A floating chat widget (bottom-right corner) that:
- Answers user questions about your system's modules using verified documentation
- Remembers conversation history per user session
- Lets users submit support tickets via a built-in form ("Get Help" button)
- Automatically escalates frustrated users to human support

The widget is a pre-built React bundle. You do not need to build anything — just drop a script tag into your HTML.

---

## Live URLs

| | URL |
|---|---|
| **Widget (frontend)** | `https://coral-app-cwkpt.ondigitalocean.app` |
| **API (backend)** | `https://coral-app-cwkpt.ondigitalocean.app/api` |
| **API docs (interactive)** | `https://coral-app-cwkpt.ondigitalocean.app/api/docs` |

---

## Step 1 — Tell Us Your Domain

Before the widget will load on your site, your domain must be added to our allowed origins list.

Send us your production URL (e.g. `https://app.streamlinehealthtech.com`) and we will add it. The widget will not work until this is done.

---

## Step 2 — Embed the Widget

Add the following snippet to your application's HTML, just before `</body>`. Replace the placeholder values with the real ones provided by the AdminIE team.

```html
<!-- AdminIE widget config — must come BEFORE the script below -->
<script>
  window.ADMINIE_SESSION_ID = "{{ current_user.id }}";   // the logged-in user's unique ID
  window.ADMINIE_API_URL    = "https://coral-app-cwkpt.ondigitalocean.app/api";
  window.ADMINIE_API_KEY    = "YOUR_API_KEY";            // provided by AdminIE team
</script>

<!-- Widget bundle -->
<script type="module" src="https://coral-app-cwkpt.ondigitalocean.app/assets/index.js"></script>
<link rel="stylesheet" href="https://coral-app-cwkpt.ondigitalocean.app/assets/index.css">
```

**`window.ADMINIE_SESSION_ID`** — this should be your logged-in user's unique ID (UUID or string). It ties conversation history to a specific user so each person picks up where they left off. Do not generate a random ID on each page load.

---

## Step 3 — Secure the API Key (Recommended)

The API key in the snippet above is visible in the browser's DevTools to any user. For production, we recommend proxying chat requests through your own backend so the key never reaches the browser:

```
User's Browser → Your Backend → AdminIE API
```

**Example proxy (Node/Express):**

```js
app.post('/adminie/chat', requireAuth, async (req, res) => {
  const { message, session_id } = req.body
  const response = await fetch('https://coral-app-cwkpt.ondigitalocean.app/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': process.env.ADMINIE_API_KEY,   // stored in your backend env vars
    },
    body: JSON.stringify({ message, session_id }),
  })
  res.json(await response.json())
})
```

Then point the widget at your proxy by setting `window.ADMINIE_API_URL` to your backend URL instead.

---

## API Reference

All endpoints (except `/health`) require the header:
```
X-API-Key: YOUR_API_KEY
```

### POST `/chat`
Send a user message and receive a response.

```json
// Request
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "How do I generate a finance report?"
}

// Response
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "To generate a finance report, navigate to the Finance module...",
  "escalated": false,
  "tutorial": {
    "module": "Finance",
    "page": 5,
    "image_url": "https://<supabase>.co/storage/v1/object/public/tutorials/Finance/page-5.png"
  }
}
```

- `escalated` — `true` when the bot has automatically routed the conversation to human support
- `tutorial` — a screenshot of the PDF page the answer came from; `null` if not applicable

---

### POST `/ticket`
Submit a support ticket from the "Get Help" form.

```json
// Request
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Jane Doe",
  "email": "jane@company.com",
  "module": "Finance",
  "subject": "Cannot export finance report",
  "description": "The export button is greyed out after selecting the date range...",
  "priority": "Urgent"
}

// Response
{
  "status": "ok",
  "ticket_id": "b3f1c2d4-..."
}
```

`priority` must be one of: `Low`, `Medium`, `Urgent`.

---

### GET `/history/{session_id}`
Retrieve the conversation history for a session.

```json
// Response
{
  "session_id": "550e8400-...",
  "messages": [
    { "role": "human", "content": "How do I generate a finance report?" },
    { "role": "ai", "content": "To generate a finance report, navigate to the Finance module..." }
  ]
}
```

---

### POST `/escalate`
Manually escalate a conversation to human support (triggers an email to the AdminIE support team).

```json
// Request
{ "session_id": "550e8400-e29b-41d4-a716-446655440000" }

// Response
{ "status": "ok", "detail": "Our support team has been notified." }
```

---

### GET `/health`
No auth required. Returns `{ "status": "ok" }`. Use for uptime checks.

---

## Rate Limits

| Endpoint | Limit |
|---|---|
| `/chat` | 8 requests / minute / IP |
| `/ticket`, `/escalate`, `/feedback` | 20 requests / minute / IP |

Exceeding the limit returns HTTP `429`. Build in a short retry delay or surface a friendly message to the user.

---

## Integration Checklist

- [ ] Send us your production domain to whitelist
- [ ] Receive your `API_KEY` from the AdminIE team
- [ ] Add the embed snippet to your HTML with the correct `session_id`, `api_url`, and `api_key`
- [ ] Verify the widget appears (bottom-right floating button)
- [ ] Test "Get Help" — submit a ticket and confirm it goes through without errors
- [ ] (Recommended) Move the API key to your backend proxy

---

## Contact

For any integration questions, reach out to the AdminIE team:
- success@adminie.com
- founders@adminie.com
