# Security Guidelines

## 1. Secrets & Credentials Management
- **Zero Hardcoded Secrets**: Never commit API keys, Kaggle `kaggle.json` tokens, AWS access keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), database passwords, or bearer tokens in source files, YAML configs, Dockerfiles, or documentation.
- Use environment variables or AWS IAM roles (in Phase 14 ECS/EC2 deployments) for runtime secrets.
- Verify `.gitignore` excludes `.env`, `*.pem`, `*.key`, and local credential files before committing.

## 2. API & Input Validation (Phase 11+)
- Validate all incoming request fields using strict Pydantic v2 types, explicit min/max bounds (e.g., `area > 0`, `bhk >= 1`, `bathroom >= 1`), and bounded batch sizes on `/predict/batch` to prevent memory exhaustion DoS.
- Configure explicit CORS origins in `config/production.yaml` instead of leaving unrestricted defaults in production.
- Never return raw internal stack traces or filesystem paths in HTTP 500 responses.

## 3. Model Serialization & Container Security
- Only load trusted locally generated `joblib` / MLflow artifacts inside `models/` or the configured registry; never deserialize untrusted user-uploaded pickle/joblib files.
- Run Docker containers as a **non-root user** (`USER appuser`) in `Dockerfile` (Phase 13).
- Pin or constrain dependencies in `requirements.txt` and avoid unnecessary OS packages in production images.
