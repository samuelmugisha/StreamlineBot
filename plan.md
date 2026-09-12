PROJECT PLAN
AdminIEBot
AI-Powered Customer Support & Success Assistant
AdminIE Impact Technology Systems
Version 1.0  |  June 2026  |  Duration: 12–16 Weeks

Field	Details
Project Name	AdminIEBot – AI-Powered Customer Success & Support Assistant
Project Sponsor	AdminIE Impact Technology Systems
Project Type	Artificial Intelligence / Customer Support Automation
Prepared By	Unity Busingye
Date	June 2026
Version	1.0
Duration	12–16 Weeks


1. Project Overview
AdminIE software is used by multiple users across different parts of the world. Supporting a large and globally distributed user base over time is resource-intensive and increasingly difficult to scale with human agents alone.

AdminIEBot is a Retrieval-Augmented Generation (RAG) chatbot that connects a generative AI model to AdminIE's proprietary data including knowledge bases, product manuals, and ticket histories. It dynamically retrieves the right information to answer user questions, delivering accurate, contextual, and hallucination-free support at scale.

The solution will transform AdminIE's customer support model from reactive issue resolution to proactive customer success management, reducing churn and decreasing overall support ticket volume without proportional increases in staffing.

2. Business Problem
As AdminIE expands globally, customer support demands increase significantly. Supporting users across multiple time zones and product modules creates the following challenges:

•	High support ticket volumes that are difficult to manage at scale
•	Repetitive Level 1 support requests are consuming Customer Success Manager time
•	Delayed response times across different time zones
•	Knowledge management complexity across multiple product modules
•	Increased customer churn risk due to unresolved support issues
•	Difficulty scaling customer success operations without adding headcount

AdminIEBot will address these challenges through intelligent automation, AI-driven customer assistance, and proactive account monitoring.

3. Project Goals
3.1 Primary Goals
•	Reduce support ticket volume by 40–60%
•	Provide 24/7 customer support with no agent dependency
•	Improve customer onboarding experience through guided walkthroughs
•	Deliver accurate responses grounded in verified AdminIE documentation
•	Reduce response times from hours to under 3 seconds

3.2 Secondary Goals
•	Improve customer retention and reduce churn rate
•	Enhance customer satisfaction scores (CSAT)
•	Provide actionable support, analytics, and knowledge gap insights
•	Assist Customer Success Managers with account monitoring and escalation

4. Project Scope
4.1 In Scope
Knowledge Retrieval
•	Product documentation, user manuals, and FAQs
•	Help center articles and API documentation
•	Internal knowledge base and previous support tickets

AI Features
•	Conversational AI with context-aware, multi-turn memory
•	Semantic search and source citation in every response
•	Follow-up question handling and personalised responses
•	Continuous knowledge base updates as new documents are pushed

Integrations
•	AdminIE CRM and helpdesk ticketing system
•	Website chat widget and mobile application
•	Microsoft Teams and Slack

Analytics
•	Usage metrics and ticket deflection reporting
•	Sentiment analysis and real-time escalation triggers
•	Knowledge gap identification

4.2 Out of Scope — Phase 1
•	Voice and video support
•	Autonomous account changes or financial transactions
•	Multi-language support beyond English
•	Admin dashboard for knowledge base management

5. Functional Requirements

Ref	Requirement	Deliverables
FR1	Knowledge Base Management — Ingest PDFs, web pages, and Confluence pages; process structured and unstructured content; auto-update knowledge repositories	Document ingestion pipeline, knowledge sync service, data validation
FR2	RAG Pipeline — Retrieve relevant information via vector search; generate grounded responses with source citations; support multi-step reasoning	Vector database, embedding pipeline, retrieval engine, LLM integration
FR3	Conversational Memory — Maintain session context; understand follow-up questions; persist history across conversation turns	Conversation state management, session memory layer
FR4	Automated Ticket Deflection — Resolve Level 1 requests; answer FAQs; guide users through troubleshooting steps	FAQ response system, troubleshooting workflows
FR5	Smart Agent Handoff — Detect unresolved issues; escalate to human support with full conversation history and troubleshooting summary	Escalation workflow, ticket creation integration, transcript generation
FR6	Onboarding Assistant — Guide new users through onboarding; recommend tutorials; deliver role-specific guidance per software tier	Onboarding workflow engine, user segmentation module
FR7	Sentiment Analysis — Detect customer frustration; monitor conversation sentiment; trigger escalation automatically	Sentiment analysis service, escalation rules engine
FR8	Role-Based Access Control — Verify user permissions; restrict unauthorised content; serve role-specific information	Authentication integration, authorisation engine

6. Non-Functional Requirements

Requirement	Target
Response Time	< 3 seconds
Availability	99.9%
Scalability	10,000+ concurrent users
Security	GDPR-compliant
Response Accuracy	> 90%
Hallucination Rate	< 5%
Uptime	24/7

7. System Architecture

Layer	Components
Frontend Layer	Web Chat Widget, Mobile Chat Interface, Microsoft Teams Integration, Slack Integration
API Layer	Authentication Service (FastAPI), Chat Service (FastAPI), Analytics Service
AI Layer	Claude Sonnet 4 (LLM), RAG Pipeline (LangChain), Embedding Service (OpenAI), Sentiment Analysis Engine
Data Layer	Supabase pgvector (Vector DB), Knowledge Repository, CRM Data, Ticket Database
Monitoring Layer	Logging, Analytics Dashboard, Performance Monitoring, Error Tracking

8. Technology Stack

Layer	Technology	Purpose
LLM	OpenAI	Core language model for all responses
Embeddings	text-embedding-3-small(openai)	Document and query vectorisation
Vector Store	Supabase pgvector	Similarity search for RAG retrieval
Memory	Supabase + PostgresChatMessageHistory (LangChain)	Persistent conversation history per session
Orchestration	LangChain/LangGraph	Chain, memory, and prompt management
Backend	FastAPI (Python)	REST API with async and streaming support
Task Queue	Celery	Background jobs ingestion, sync, notifications
Frontend	React + Vite + Tailwind CSS	Chat UI for testing and multi-channel embedding
Database	Supabase (PostgreSQL)	All persistent data  vectors, chat history, CRM
Deployment	Docker +digital ocean	Containerised cloud hosting
Monitoring	Grafana + Prometheus + OpenTelemetry	Logging, metrics, and performance tracking

9. Project Phases & Timeline

Phase	Weeks	Activities	Deliverables
Phase 1: Discovery & Requirements	1–2	Stakeholder interviews, documentation review, integration assessment, and architecture design	Requirements document, system architecture, project roadmap
Phase 2: Knowledge Base Development	3–4	Document collection, data cleaning, chunking strategy, and embedding generation	Knowledge repository, Supabase pgvector database
Phase 3: Core RAG Development	5–7	Retrieval engine, prompt engineering, source citation, conversation memory	Functional RAG chatbot, testing environment
Phase 4: Customer Success Features	8–10	Ticket deflection workflows, onboarding assistant, sentiment analysis, and agent handoff	Customer success automation features
Phase 5: Integrations	11–12	CRM integration, ticketing integration, Slack integration, Teams integration	Connected ecosystem
Phase 6: Testing & Optimisation	13–14	Performance testing, security testing, accuracy evaluation, and user acceptance testing	Test reports, optimised system
Phase 7: Deployment & Training	15–16	Production deployment, user training, monitoring setup, documentation	Production-ready AdminIEBot

10. Detailed Task Breakdown
Phase 1 — Discovery & Requirements (Weeks 1–2)
•	Conduct stakeholder interviews with Customer Success and Product teams
•	Review all available AdminIE documentation and knowledge base content
•	Assess existing CRM, ticketing system, and API landscape for integration points
•	Design system architecture and confirm technology stack
•	Define user personas and support use cases for RAG testing
•	Finalise and sign off on requirements document

Phase 2 — Knowledge Base Development (Weeks 3–4)
•	Collect all AdminIE documents: PDFs, help articles, API docs, support tickets
•	Clean and preprocess documents, remove duplicates, fix formatting issues
•	Implement RecursiveCharacterTextSplitter with optimal chunk size and overlap
•	Generate embeddings using text-embedding-3-small and store in Supabase pgvector
•	Create the documents table and chat_history table in Supabase with all required indexes
•	Test ingestion pipeline end-to-end with sample AdminIE documents

Phase 3 — Core RAG Development (Weeks 5–7)
•	Set up Supabase vector store retriever in LangChain
•	Build RAG chain: query → vector retrieval → context injection → Claude response
•	Implement source citation in every response that references the document it used
•	Integrate ConversationBufferWindowMemory (k=10 turns in prompt context)
•	Set up PostgresChatMessageHistory to persist full history to Supabase by session_id
•	Build FastAPI backend with /chat, /history, and /ingest endpoints
•	Write Pydantic schemas for all request and response models
•	Test full RAG + memory flow end-to-end via Postman

Phase 4 — Customer Success Features (Weeks 8–10)
•	Build Level 1 ticket deflection workflows, login resets, billing, and feature walkthroughs
•	Implement smart agent handoff, detect low-confidence responses, and escalate
•	Generate and transfer a full conversation transcript to a human CSM on escalation
•	Build onboarding assistant with role-specific guidance per AdminIE software tier
•	Integrate sentiment analysis — detect frustration and auto-trigger escalation
•	Test all customer success flows with simulated support scenarios

Phase 5 — Integrations (Weeks 11–12)
•	Integrate with AdminIE CRM to look up account status and ticket history
•	Connect to helpdesk ticketing system to auto-create tickets on escalation
•	Build and deploy Slack bot integration
•	Build and deploy Microsoft Teams integration
•	Test all integration endpoints and data flows

Phase 6 — Testing & Optimisation (Weeks 13–14)
•	Run performance tests to validate response time < 3 seconds under load
•	Run security tests to validate RBAC, auth, and GDPR compliance
•	Evaluate retrieval accuracy against benchmark question set (target > 90%)
•	Conduct user acceptance testing with AdminIE Customer Success team
•	Tune chunk size, similarity threshold, and system prompt based on test results
•	Fix all bugs and edge cases identified during testing

Phase 7 — Deployment & Training (Weeks 15–16)
•	Containerise all services with Docker
•	Deploy FastAPI backend to digital ocean
•	Deploy React frontend to digital ocean
•	Set up Grafana + Prometheus monitoring and alerting
•	Conduct user training sessions with the Customer Success team
•	Finalise README, API documentation, and deployment guide
•	Deliver final demo and hand over to AdminIE team

11. Success Metrics (KPIs)

Category	KPI	Target
Operational	Ticket Deflection Rate	≥ 50%
Operational	Average Response Time	≤ 3 seconds
Operational	First Contact Resolution Rate	≥ 70%
Operational	Escalation Accuracy	≥ 90%
Customer	Customer Satisfaction Score (CSAT)	≥ 90%
Customer	Customer Churn Rate	Reduced vs baseline
Customer	Product Adoption Rate	Increased vs baseline
Technical	Retrieval Accuracy	≥ 90%
Technical	Knowledge Coverage	≥ 95%
Technical	System Uptime	≥ 99.9%
Technical	Hallucination Rate	< 5%

12. Risks & Mitigations

Risk	Likelihood	Impact	Mitigation
Poor documentation quality in the knowledge base	Medium	High	Conduct a knowledge audit and cleanup in Phase 2 before embedding
Hallucinated or inaccurate responses	Medium	High	Strict RAG grounding, source citations, and accuracy benchmarking in Phase 6
Integration delays with CRM or ticketing system	Medium	Medium	Early API assessment in Phase 1; build stubs to unblock development
Security and data privacy concerns	Low	High	Implement RBAC, encryption, and GDPR-compliant data handling from Phase 3
Low user adoption by Customer Success team	Medium	Medium	Involve CSM team in UAT (Phase 6) and provide formal training (Phase 7)
Scope creep from new feature requests	Medium	Medium	Lock Phase 1 scope; log all additions as Phase 2 backlog items
API token costs exceeding budget	Low	Medium	Cap context using BufferWindowMemory (k=10) and monitor usage in Grafana

13. Final Deliverables

#	Deliverable	Phase
1	Requirements document and system architecture	Phase 1
2	Document ingestion pipeline supporting PDFs, URLs, and Confluence	Phase 2
3	Functional RAG chatbot with source citation and conversation memory	Phase 3
4	Customer success features — ticket deflection, handoff, onboarding, sentiment	Phase 4
5	CRM, ticketing, Slack, and Teams integrations	Phase 5
6	Test reports and an optimised, production-ready system	Phase 6
7	Cloud-deployed backend and frontend with monitoring dashboards	Phase 7
8	Full documentation — README, API docs, deployment guide	Phase 7

			

