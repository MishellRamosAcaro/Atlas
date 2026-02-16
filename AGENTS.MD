# AGENTS.md — Atlas FastAPI Service

## 1. Scope

This document defines **global engineering, security, quality, and operational rules** for the Atlas FastAPI service.  
It applies to the **entire repository**, independent of specific features or business logic.


---

## 2. Project Contexts

- **Type:** Internal API  
- **Runtime:** Python 3.14  
- **Environment:**
  - Development → Local Linux (docker-compose)
  - Production → Google Cloud Run (Docker image)
- **Repository model:** Single repository  
- **Configuration management:** Pydantic Settings v2  
- **Environment separation:** `dev`, `prod`
- **Data Sensitivity:** No personal data (PII) or secrets / credentials / tokens are processed

---

### 3.2 Secrets Management

- **Development:** environment variables via `.env`
- **Production:** Google Cloud Secret Manager
- `.env` files **must never be committed**
- Provide `.env.example` when needed

---

### 3.3 Dependencies & Supply Chain

- **Dependency manager:** `pip` + `requirements.txt`
- **Locking:**  
  - Dependencies must be frozen using  
    ```bash
    pip freeze > requirements.txt
    ```
- **Updates:** manual or Dependabot
- **Security scanning:** Snyk and Dependabot alerts
- **Licenses:** only permissive licenses allowed

---

### 3.4 Application Hardening

- **CORS**
  - Open in `dev`
  - Restricted in `prod`
- **Security headers** must be enabled in production:
  - HSTS
  - X-Content-Type-Options
  - X-Frame-Options
  - Referrer-Policy
- **Error handling**
  - No stack traces in production responses
  - Standardized error messages
- **TLS**
  - Mandatory in all non-local environments

---

## 4. Repository Structure & Architecture

- **Layout:** root package (`app/...`)
- **Architecture:**  
  Layered design prepared for future **hexagonal evolution**:
  ```
  routers → services → repositories → infrastructure
  ```
- **Naming conventions:** follow Python PEP standards
- **Imports:** prefer **absolute imports**

---

## 5. Formatting, Linting, and Typing

- **Formatter:** Black  
- **Linter:** Ruff  
- **Import ordering:** Ruff  
- **Type checking:** none enforced (gradual typing allowed)  
- **Typing strictness:** medium / warning-level  
- **Docstrings style:** NumPy  

### Pre-commit hooks

Minimum required:

- Ruff lint
- Black format

---

## 6. Testing & Quality

- **Framework:** pytest  
- **Test types required:**
  - Unit
  - Integration
  - End-to-end
- **Coverage minimum:** **80%**
- **External resources:** mocked
- **Snapshots / golden files:** not used

---

## 7. Local Execution & Configuration

### Virtual environment (mandatory in development)

**In local development only**, always use the Python virtual environment when executing any Python-related command (pytest, uvicorn, ruff, black, etc.). In production the application runs inside Docker.

Examples:
```bash
# Activate venv first, then run
source .venv/bin/activate
pytest tests/ -v
uvicorn app.main:app --reload

# Or invoke via venv binary directly
.venv/bin/python -m pytest tests/ -v
.venv/bin/uvicorn app.main:app --reload
```

### Run locally

```bash
uvicorn app.main:app --reload
```

### Environment variables

- `.env` used only in local development
- Production configuration injected via Cloud Run + Secret Manager

---

## 8. Observability

- **Logging format:** structured JSON
- **Mandatory log fields:**
  - `request_id`
  - `trace_id`
  - `service`
  - `env`
  - `version`

Future auditability and tracing may be introduced after MVP.

---

## 9. API Standards

- Endpoints should follow:
  - **Plural resource naming**
  - **Versioned base path** (`/v1`)
- **OpenAPI requirements:**
  - Mandatory tags
  - Minimum descriptions
- **Error handling:**
  - Use `HTTPException`
  - Provide a **standard error response schema**

---

## 10. CI/CD (Future Enforcement)

- **CI platform:** GitHub Actions  
- **Required pipeline stages:**
  - Lint
  - Type checks (future)
  - Tests
  - Docker build
  - Security scan

### Pull Requests

- **Commit style:** Conventional Commits  
- **Branching model:**  
  - `main`
  - `feature/*`
  - `release/*`

---

## 11. Containers & Deployment

- **Docker:** mandatory  
- **Base image:** `python:alpine`  
- **Security:** container must run as **non-root user**  
- **Platform:** Google Cloud Run  
- **Kubernetes:** not used

---

## 12. Code Security & Repository Hygiene

- **SAST:** Bandit required  
- **Generated files** must be ignored:
  - `__pycache__/`
  - `.pytest_cache/`
  - `.mypy_cache/`
  - `.venv/`
- **EditorConfig:** recommended for consistent line endings

---

## 13. Compliance

- **Regulation considered:** GDPR / LOPDGDD  
- **Audit logging:** not required at MVP stage  
- **Encryption in transit:** mandatory outside local development

---

## 14. Definition of Done (Global)

A change is considered complete when:

- Code is formatted and lint-clean
- Tests pass with ≥80% coverage
- No secrets are committed
- Docker image builds successfully
- Security scans report no critical vulnerabilities
- OpenAPI documentation is updated

---

**Service:** Atlas  
**Document scope:** Global engineering governance for the FastAPI project.