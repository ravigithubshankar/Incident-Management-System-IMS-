# Incident Management System Architecture

## System Overview

The Incident Management System (IMS) is a production-grade, real-time incident processing platform built with event-driven architecture, state machine validation, and comprehensive observability.

## Core Architecture

### 1. Signal Ingestion Layer
```
┌─────────────────┐
│  Rate Limiter   │  ← Token Bucket (10,000 tokens/sec)
├─────────────────┤
│   FastAPI        │  ← Async web framework
├─────────────────┤
│   Signal Queue   │  ← asyncio.Queue (max 50,000)
└─────────────────┘
```

**Flow**: Client → Rate Limiter → Signal Queue → Workers

### 2. Processing Layer
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Debounce Engine │    │  Queue Workers  │    │  Alert Service  │
│  (Redis TTL)    │    │  (20 tasks)    │    │  (Strategy)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                   │
         └───────────────────────┼───────────────────┘
                                 │
                    ┌─────────────────┐
                    │  WebSocket Hub  │
                    └─────────────────┘
```

**Debounce Logic**: 10-second window per component, prevents duplicate work items
**Worker Pool**: 20 concurrent tasks, batch processing (up to 500 signals)
**Alert Strategies**: P0→Slack, P1→Slack, P2→Slack, P3→Log only

### 3. Storage Layer
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL     │    │  MongoDB         │    │  Redis          │
│  (TimescaleDB)  │    │  (Signals)      │    │  (Cache/PubSub) │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Work Items  │ │    │ │ Signal Data  │ │    │ │ Dashboard   │ │
│ │ RCA Records │ │    │ │ TTL 30 days │ │    │ │ Debounce   │ │
│ │ API Keys    │ │    │ │ Indexes     │ │    │ │ Rate Limit  │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Database Schema**:
- **Work Items**: State machine validated, signal counts, RCA relationships
- **Signals**: Raw signal storage with component/time indexes
- **Metrics**: TimescaleDB hypertables for time-series aggregation

### 4. Frontend Layer
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  React App     │    │  React Query    │    │  WebSocket      │
│  (TypeScript)   │    │  (Data Layer)   │    │  (Real-time)    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│  Dashboard     │    │  Detail View    │    │  RCA Form       │
│  Component     │    │  Component     │    │  Component     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                   │
         └───────────────────────┼───────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Health Widget  │
                    └─────────────────┘
```

## Design Patterns Implementation

### 1. Strategy Pattern (Alerting)
```python
class AlertStrategy(ABC):
    @abstractmethod
    async def alert(self, incident: WorkItem) -> None: ...

STRATEGY_MAP = {
    ("RDBMS", "P0"): P0RDBMSStrategy(),
    ("API", "P1"): P1APIStrategy(),
    # ... extensible mapping
}
```

### 2. State Machine (Work Item Lifecycle)
```python
# Legal transitions only:
OPEN → INVESTIGATING → RESOLVED → CLOSED (with RCA)

class ResolvedState(WorkItemState):
    def transition(self, item, new_status):
        if new_status == "CLOSED":
            if not item.rca or not item.rca.is_complete():
                raise RCARequiredError("RCA must be complete")
            item._state = ClosedState()
```

### 3. Repository Pattern (Data Access)
```python
class PostgresWorkItemRepository(WorkItemRepository):
    @with_retry(max_attempts=3)
    async def create(self, signal: Signal) -> WorkItem:
        # Transactional database operations
        
class MongoSignalRepository(SignalRepository):
    async def save_batch(self, signals: List[Signal]) -> List[str]:
        # Bulk MongoDB operations with indexes
```

## Key Technical Decisions

### 1. Queue Management
- **Bounded Queue**: 50,000 signal limit prevents memory exhaustion
- **Non-blocking**: `put_nowait()` ensures HTTP handlers never block
- **Batch Processing**: Workers drain up to 500 signals for efficiency

### 2. Debouncing Strategy
- **Component-based**: Each component gets 10-second debounce window
- **Redis TTL**: Automatic cleanup prevents memory leaks
- **First Signal Wins**: Creates work item, subsequent signals link to it

### 3. Rate Limiting
- **Token Bucket**: 10,000 tokens refill at 10,000/sec
- **Thread-safe**: asyncio.Lock prevents race conditions
- **HTTP 429**: Clear backpressure signal to clients

### 4. State Management
- **Immutable States**: State objects enforce valid transitions
- **Business Rules**: RCA required before closing, no backward transitions
- **Audit Trail**: All state changes logged with timestamps

### 5. Data Modeling
- **RCA Validation**: Minimum 50 characters, completeness checks
- **MTTR Calculation**: Automatic computation from start/end times
- **Signal Linking**: Many-to-one relationship with work items

## Performance Characteristics

### Throughput Targets
- **Signal Ingestion**: 10,000 signals/second sustained
- **Queue Processing**: 500 signals/batch, 20 workers
- **Database Writes**: Batch operations for efficiency
- **WebSocket Updates**: Real-time dashboard pushes

### Scalability Factors
- **Horizontal Scaling**: Add more workers to increase throughput
- **Database Scaling**: TimescaleDB for time-series data
- **Cache Layer**: Redis for session state and rate limiting
- **Load Balancing**: Nginx distributes frontend requests

## Observability Stack

### 1. Health Monitoring
```python
GET /health → {
    "status": "ok|degraded",
    "postgres": "ok|error",
    "mongo": "ok|error", 
    "redis": "ok|error"
}
```

### 2. Metrics Collection
```python
GET /metrics → {
    "signals_per_sec": 1250.5,
    "queue_depth": 150,
    "active_incidents": 12,
    "worker_utilisation": "18/20"
}
```

### 3. Structured Logging
```json
{
    "timestamp": "2024-01-01T10:00:00Z",
    "level": "INFO",
    "event": "THROUGHPUT_METRICS",
    "signals_per_sec": 1250.5,
    "queue_depth": 150
}
```

## Security Architecture

### 1. Authentication
- **API Keys**: Hashed storage in PostgreSQL
- **Header Validation**: X-API-Key required for all endpoints
- **Rate Limiting**: Per-client token bucket enforcement

### 2. Data Protection
- **Input Validation**: Pydantic v2 strict mode
- **SQL Injection**: SQLAlchemy parameterized queries
- **XSS Protection**: React escaping and CSP headers

### 3. Network Security
- **TLS Termination**: Nginx handles HTTPS in production
- **CORS**: Restricted to frontend domain only
- **WebSocket Security**: Origin validation and protocol enforcement

## Deployment Architecture

### Container Orchestration
```yaml
services:
  postgres:    # TimescaleDB (time-series optimized)
  mongo:        # MongoDB (document storage)
  redis:        # Redis (caching + pub/sub)
  backend:      # FastAPI (async processing)
  frontend:     # React SPA (nginx served)
```

### Infrastructure Requirements
- **Memory**: 4GB+ recommended for high-throughput processing
- **CPU**: Multi-core for concurrent worker processing
- **Storage**: SSD for database performance
- **Network**: Gigabit for signal ingestion throughput

This architecture ensures the system can handle production workloads while maintaining data consistency, performance, and observability requirements.
