---
paths:
  - "Dockerfile"
  - "docker-compose*.yml"
  - "infra/**/*"
---

# Docker Rules

- Use multi-stage builds: builder stage for dependencies, runtime stage for the app
- Final image must be based on python:3.12-slim, not python:3.12 or ubuntu
- Never copy .env, .git, or __pycache__ into the image — use .dockerignore
- Pin all base image versions with SHA or specific tag, never use :latest
- Run the app as a non-root user (create a dedicated user in Dockerfile)
- Use COPY --from=builder for dependency artifacts only
- docker-compose.yml must work with a single `docker compose up` — no manual setup steps
- Health checks must be defined in docker-compose for every service
- Environment variables in compose use ${VAR:-default} syntax with defaults
- Grafana and Prometheus must auto-provision via mounted config files, no manual UI setup
- Expose only necessary ports: app (8000), Grafana (3000), Prometheus (9090)
- Redis must not expose ports to host in production compose override
