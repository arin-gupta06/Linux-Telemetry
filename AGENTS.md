# AlgoFight Architecture and Setup

This document serves as the core knowledge base for the AI agent to understand the architecture, tech stack, and structural conventions of the AlgoFight project.

## Monorepo Structure
The project is a **pnpm workspace-based monorepo** managed with **Turborepo**. 

### Applications (pps/)
- pi: The main REST API server (includes centralized Zod validation for DTOs).
- worker: Dedicated worker application. Consumes queued submissions via BullMQ and delegates execution to the application layer.
- scheduler: Background jobs runner. Handles recovery of stale submissions and auto-finalizes expired battles.
- websocket: Standalone WebSocket server with real-time room/user event handling, ConnectionManager, and dynamic ELO matchmaking.

### Packages (packages/)
- database: Prisma ORM with PostgreSQL. Contains domain entities and repository implementations (e.g., PrismaSubmissionRepository).
- queue: Redis-backed queue infrastructure using BullMQ.
- pplication: Service layer, execution orchestration (ExecutionService), and advanced judging system (VerdictEngine, Comparator).
- events: Event bus and domain events (e.g., SubmissionCreatedEvent, ExecutionStartedEvent).
- state-machine: Enforces modular state transitions for submissions (CREATED, QUEUED, PROCESSING, COMPLETED, FAILED, RETRYING, STALE).
- error-handling: Centralized error handling providing AppError, ErrorCode, and ErrorLayer.
- logger: Centralized structured logging.

## Core Architectural Workflows
- **Submission Lifecycle**: API -> BullMQ Queue -> Worker -> ExecutionService -> CodeExecutor (currently MockExecutor, preparing for Docker Sandbox) -> SubmissionResult -> PrismaSubmissionRepository.
- **Judging System**: Evaluates code against multiple test cases, yielding verdicts based on rules (e.g., time/memory limits, compilation errors). It tracks pass/fail counts and aggregates them via JudgeResultProcessor.
- **Recovery System**: The scheduler utilizes RecoveryService to detect submissions stuck in PROCESSING, applying exponential backoff retry policies and eventually queuing or marking them as failed.
- **Dependency Injection**: Dependencies are provided via constructor injection (e.g., ExecutionService depends on the SubmissionRepository abstraction rather than PrismaSubmissionRepository directly) for better testability.
- **Event-Driven Design**: The system is decoupled through events handled by subscribers like LoggingHandler, MetricsHandler, and AuditHandler.

## Getting Started / Execution
- **Package Manager**: Use pnpm for installing dependencies.
- **Database**: Run Prisma migrations or starts using Docker.
- **Run Apps**: Development is typically started via 
pm run dev or pnpm dev depending on the Turborepo setup. For example, the backend/websocket can be run from pps/websocket.
