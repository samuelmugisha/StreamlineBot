# StreamlineBot for Customer Success of Streamline EMR

Streamline EMR is used by more than 7,000 users in different parts of the world. Supporting many users over a large period of time can be hectic.
This project creates a RAG chatbot for Streamline EMR System.
A Retrieval-Augmented Generation (RAG) chatbot connects a generative AI to your company's proprietary data (like knowledge bases, manuals, and ticket histories). It dynamically retrieves the right information to answer user questions, ensuring accurate, highly contextual, and hallucination-free support.

**Core RAG Capabilities**
- Dynamic Knowledge Retrieval: Accesses and parses unstructured data (PDFs, URLs, Confluence pages) in real-time to answer complex, multi-step customer inquiries instantly.
- Factual, Grounded Responses: Reduces AI hallucinations by anchoring every answer in your verified product documentation, citing the exact source documents it used.
- Context-Aware Conversations: Maintains memory of the current conversation, allowing customers to ask follow-up questions without needing to restate their issue.
- Continuous Self-Correction: Automatically updates its knowledge base as you push new product releases, API documentation, or feature updates.

**Customer Success-Specific Features**
- Proactive Account Management: Triggers automated check-ins or tips based on user behavior (e.g., when a user frequently navigates to a complex feature but never successfully completes an action).
- Automated Ticket Deflection: Resolves common Level 1 support issues (like login resets, basic billing questions, or simple feature walkthroughs) 24/7 without human agent intervention.
- Smart Agent Handoff: Collects initial troubleshooting data and seamlessly transfers the context and chat transcript to a human Customer Success Manager (CSM) or support agent when an issue escalates.
- Onboarding Guidance: Delivers personalized onboarding walkthroughs, tutorials, and step-by-step guides based on the specific software tier or module the customer purchased.

**Integration & Enterprise Features**
- Software Tooling Integrations: Integrates natively with Stre@mline CRM and helpdesk ticketing systems to look up past ticket history and client account statuses.
- Sentiment Analysis & Analytics: Tracks user frustration levels in real-time, escalating negative sentiment to human managers and providing analytics on which help articles are most (or least) helpful.
- Role-Based Access Control (RBAC): Ensures the chatbot only retrieves information the customer is authorized to see (e.g., hiding enterprise-level features from basic-tier users).
- Multi-Channel Deployment: Embeds seamlessly across all user touchpoints, including your web app, mobile app, Slack, Microsoft Teams, and email.
- By leveraging a RAG setup, your software company can shift from reactive support to a proactive customer success model, ultimately reducing churn and decreasing your overall support ticket volume.

---

## What's actually implemented today

Not every capability above is live yet — this is the accurate, current
picture. The bot answers questions from ingested Streamline/AdminIE PDF and
Google Doc documentation, remembers conversation history per session,
scores user frustration and detects explicit human requests via keyword
matching, automatically escalates to human support (email + a stored
record) on negative sentiment/repeated failures/low ratings, and lets users
submit support tickets. RBAC, proactive account management, and
multi-channel deployment beyond a single embeddable web widget are not yet
built — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what exists.

## Getting started

| I want to... | Read |
|---|---|
| Run this locally / understand the full API | [SETUP.md](SETUP.md) |
| Embed the widget in another application | [INTEGRATION.md](INTEGRATION.md) |
| Understand how the pieces fit together | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Deploy or roll back a release | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Handle a production incident | [docs/RUNBOOK.md](docs/RUNBOOK.md) |
| Contribute code | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Report a security issue | [SECURITY.md](SECURITY.md) |
| See what changed recently | [CHANGELOG.md](CHANGELOG.md) |

## Quick start

```bash
cp .env.example .env    # fill in real values — see SETUP.md
pip install -r requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000

cd frontend && cp .env.example .env && npm install && npm run dev
```

Run the test suite before pushing:
```bash
pytest                              # backend
cd frontend && npm run test         # frontend
```

## License

Proprietary — see [LICENSE](LICENSE). Not open source.
