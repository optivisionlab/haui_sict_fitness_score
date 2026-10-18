---
name: docker-production
description: Production-grade Docker build optimization and container security skill. Use when creating, reviewing, or hardening Dockerfiles, Docker Compose services, CI/CD image pipelines, or container runtime settings.
version: 1.0
scope:
  - Dockerfile
  - Docker BuildKit / buildx
  - Docker Compose
  - container runtime hardening
  - image supply-chain security
  - CI/CD container security
sources:
  - Docker Docs: Building best practices
  - Docker Docs: Cache optimization
  - Docker Docs: Build secrets and build checks
  - Docker Docs: Engine security, rootless, AppArmor
  - Docker Docs: Compose services and deploy resources
  - Docker Scout: CVE, SBOM, provenance
  - CIS Docker Benchmark
  - OWASP Docker Security Cheat Sheet
---

# Docker Production Skill

## 0. Goal

Build Docker images and containers that are:

1. Small enough for fast build/pull/start.
2. Reproducible and deterministic.
3. Free of unnecessary build/runtime dependencies.
4. Resistant to privilege escalation and container breakout.
5. Free of baked-in secrets.
6. Continuously scanned for known vulnerabilities.
7. Traceable through SBOM and build provenance.
8. Constrained for CPU, memory, process count, filesystem, Linux capabilities, and kernel security policies.
9. Easy to maintain and patch.

Do not optimize for image size alone. Optimize the combination:

`size + reproducibility + security + operability + maintainability`

---

# 1. Core principles

## 1.1 Build only what runtime needs

Prefer:

```dockerfile
FROM python:3.11-slim AS builder
# compile/install dependencies

FROM python:3.11-slim AS runtime
# copy only runtime artifacts
```

Avoid putting compilers, headers, package managers, test tools, and source build artifacts into the final image.

Primary technique:

- Multi-stage builds.

Expected result:

- Smaller final image.
- Smaller attack surface.
- Fewer packages to patch.
- Cleaner separation between build and runtime.

---

## 1.2 Prefer a minimal base image

Typical progression:

```text
full distro image
    ->
slim/minimal image
    ->
hardened or distroless image (when compatible)
```

Start with `slim` when operational compatibility is more important than the last few MB.

Do not choose Alpine/distroless blindly. Validate:

- libc compatibility
- native Python wheels
- debugging requirements
- TLS/certificate behavior
- shell/debug tooling requirements
- runtime libraries

Rule:

> Use the smallest base image that remains reliable and supportable for the application.

---

## 1.3 Pin dependency versions

Bad:

```text
fastapi
uvicorn
pymongo
```

Better:

```text
fastapi==<version>
uvicorn==<version>
pymongo==<version>
```

Best for larger projects:

- lock dependencies
- review dependency changes
- regenerate lockfiles intentionally
- scan dependencies for CVEs/licensing issues

Goal:

```text
same source + same lock/base digest
    ->
same dependency graph
```

---

# 2. Base image reproducibility

## 2.1 Pin by digest for production

Instead of:

```dockerfile
FROM python:3.11-slim
```

production can use:

```dockerfile
FROM python:3.11-slim@sha256:<DIGEST>
```

Use digest pinning when:

- reproducibility is important
- regulated deployment requires immutable artifacts
- supply-chain control matters
- releases must be repeatable

Operational rule:

- Review digest updates deliberately.
- Do not pin forever; stale images still require security updates.

---

# 3. Build context minimization

## 3.1 Always create `.dockerignore`

Recommended starting point:

```dockerignore
.git
.gitignore
.env
.env.*
*.pem
*.key
*.crt
*.log

__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache

.venv
venv
node_modules

dist
build
coverage
htmlcov

tests
docs
README.md
```

Adjust the list to the project.

Important:

- Never rely only on `.dockerignore` for secret protection.
- Review what the build actually sends into the context.
- Do not use `COPY . .` unless the context is intentionally controlled.

Why:

- smaller build context
- faster builds
- fewer accidental files
- lower chance of leaking local secrets/artifacts

---

# 4. Docker layer and cache optimization

## 4.1 Put stable inputs before volatile source

Good:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY utils/ ./utils/
```

Bad:

```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

Reason:

Changing application source should not invalidate expensive dependency installation when dependencies did not change.

---

## 4.2 Combine apt update/install/cleanup

Good:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

Avoid:

```dockerfile
RUN apt-get update
RUN apt-get install -y ...
RUN apt-get clean
```

Reason:

- apt indexes should not remain in later layers
- cleanup belongs in the same layer as installation

---

## 4.3 Use `--no-install-recommends`

Prefer:

```dockerfile
apt-get install -y --no-install-recommends package1 package2
```

Reason:

- avoids unnecessary recommended packages
- lowers image size
- lowers package count
- lowers vulnerability surface

---

## 4.4 Use BuildKit cache mounts

Python example:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

Apt example:

```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev
```

Important:

- build cache is not runtime application data
- cache mounts improve build speed
- cache mounts should never be used as a substitute for dependency pinning

---

## 4.5 Use external cache in CI

With Buildx:

```bash
docker buildx build \
  --cache-from type=registry,ref=org/app:buildcache \
  --cache-to type=registry,ref=org/app:buildcache,mode=max \
  -t org/app:${GIT_SHA} \
  --push .
```

Benefits:

- faster CI builds
- useful across ephemeral runners
- avoids rebuilding identical dependency layers

---

# 5. Python-specific image optimization

## 5.1 Disable bytecode

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
```

Prevents unnecessary `.pyc` generation during runtime.

## 5.2 Unbuffer Python output

```dockerfile
ENV PYTHONUNBUFFERED=1
```

Makes logs appear promptly through container stdout/stderr.

## 5.3 Avoid pip cache in final layers

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

## 5.4 Install only runtime Python dependencies

Separate:

- build-only dependencies
- runtime dependencies

Example:

```text
builder:
  gcc
  headers
  compiler toolchain

runtime:
  Python
  runtime libraries
  application
```

---

# 6. Filesystem ownership

Prefer:

```dockerfile
COPY --chown=agent:agent app/ ./app/
```

over:

```dockerfile
COPY app/ ./app/
RUN chown -R agent:agent /app
```

This avoids an unnecessary ownership-fixing step.

For fixed identities:

```dockerfile
RUN groupadd --system --gid 10001 agent \
    && useradd --system \
        --uid 10001 \
        --gid 10001 \
        --no-create-home \
        agent

USER 10001:10001
```

---

# 7. Non-root runtime

## 7.1 Never run the application as root unless there is a documented reason

Use:

```dockerfile
USER 10001:10001
```

or:

```dockerfile
USER agent
```

Security principle:

> Least privilege.

A compromised application should have the minimum filesystem and process permissions required to work.

---

# 8. Read-only root filesystem

For production, prefer:

```yaml
read_only: true
```

Then explicitly provide writable locations only when needed.

Example:

```yaml
tmpfs:
  - /tmp:size=64m
```

Typical model:

```text
/app       read-only
/usr       read-only
/etc       read-only
/tmp       tmpfs
/data      named volume when persistent write is required
```

Benefits:

- makes file modification harder after compromise
- limits persistence inside the container
- reduces damage from malware or runtime exploitation

Test the application first. Some frameworks require writable `/tmp`, log directories, sockets, caches, or model directories.

---

# 9. Linux capabilities

Containers should not keep capabilities they do not need.

Strong default for application containers:

```yaml
cap_drop:
  - ALL
```

Only add back a specific capability when there is a proven requirement.

Avoid:

```yaml
cap_add:
  - ALL
```

Do not use:

```yaml
privileged: true
```

unless there is an exceptional, documented, reviewed need.

For a normal FastAPI server on port `8000`, `NET_BIND_SERVICE` is usually unnecessary because the port is above 1024.

---

# 10. Prevent privilege escalation

Use:

```yaml
security_opt:
  - no-new-privileges:true
```

Purpose:

- prevents gaining additional privileges through supported privilege-escalation mechanisms
- adds defense in depth to non-root execution

Preferred runtime baseline:

```yaml
user: "10001:10001"

read_only: true

cap_drop:
  - ALL

security_opt:
  - no-new-privileges:true
```

---

# 11. User namespaces and rootless Docker

## 11.1 User namespace mapping

Goal:

```text
container UID 0
    ->
non-root host UID
```

This reduces the impact of a container breakout.

## 11.2 Rootless Docker

Rootless mode runs the Docker daemon and containers without requiring root privileges.

Use it when the environment and operational requirements support it.

Important:

- rootless Docker is different from simply using `USER agent`
- both can be complementary layers
- rootless has compatibility/performance/feature considerations that must be tested

---

# 12. Kernel security profiles

## 12.1 Seccomp

Use a restrictive seccomp profile where practical.

Goal:

- block unnecessary syscalls
- reduce kernel attack surface

Do not blindly deploy an extremely restrictive custom profile before testing.

Start from Docker's default seccomp protection, then tighten based on observed requirements.

## 12.2 AppArmor

On supported Linux systems, use AppArmor profiles.

Docker normally uses the `docker-default` AppArmor profile unless overridden.

For higher-assurance deployments:

- define a custom profile
- explicitly allow only required operations
- test thoroughly

## 12.3 SELinux

On SELinux-enabled hosts, use appropriate container labeling and policies.

Rule:

> Container security is not only a Dockerfile problem; the host kernel and security modules matter.

---

# 13. Resource isolation

Protect the host from runaway containers.

Compose example:

```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: 512M
      pids: 256
    reservations:
      cpus: "0.25"
      memory: 128M
```

Depending on deployment/runtime, direct service settings may also be used:

```yaml
cpus: "1.0"
mem_limit: 512m
```

Useful protections:

- CPU limit
- memory limit
- PID limit
- file descriptor/ulimit limits where needed

Reason:

- reduce accidental resource exhaustion
- reduce denial-of-service blast radius
- improve multi-service isolation

---

# 14. PID limits

An application can create too many processes/threads.

Use an appropriate PID limit, for example:

```yaml
deploy:
  resources:
    limits:
      pids: 256
```

Choose a value based on the application's real workload.

Do not copy a random number into production without measuring.

---

# 15. Network isolation

Avoid unnecessary:

```yaml
network_mode: host
```

unless there is a documented reason.

Prefer dedicated Docker networks:

```yaml
networks:
  backend:

services:
  api:
    networks:
      - backend

  mongodb:
    networks:
      - backend
```

Principles:

- expose only required ports
- do not publish databases to the host unless necessary
- let internal services communicate over private Docker networks
- separate frontend/backend/database networks when appropriate

Example:

```text
Internet
   |
 API :8000
   |
 private backend network
   +---- MongoDB
   +---- Redis
```

---

# 16. Secrets

## 16.1 Never bake secrets into the image

Never do:

```dockerfile
ENV MONGO_PASSWORD=secret
```

Never do:

```dockerfile
ARG AWS_SECRET_ACCESS_KEY=...
```

Never copy:

```dockerfile
COPY .env .
```

## 16.2 Build-time secrets

Use BuildKit:

```dockerfile
RUN --mount=type=secret,id=pypi_token \
    TOKEN="$(cat /run/secrets/pypi_token)" && \
    <build command using TOKEN>
```

Build with:

```bash
docker buildx build \
  --secret id=pypi_token,src=./pypi_token.txt \
  .
```

## 16.3 Runtime secrets

Prefer the platform's secret mechanism when available.

Compose example:

```yaml
services:
  api:
    secrets:
      - mongo_password

secrets:
  mongo_password:
    file: ./secrets/mongo_password.txt
```

Application reads the secret from the mounted file rather than baking it into an image layer.

---

# 17. Build checks

Run:

```bash
docker build --check .
```

Use BuildKit build checks to catch issues such as:

- secrets used in ARG/ENV
- undefined variables
- bad stage names
- unsafe command forms
- problematic platform declarations
- relative WORKDIR issues

Treat build-check warnings as engineering feedback, not noise.

---

# 18. Health and lifecycle

## 18.1 Healthcheck

Example:

```dockerfile
HEALTHCHECK \
  --interval=30s \
  --timeout=10s \
  --start-period=15s \
  --retries=3 \
  CMD python -c \
  "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
  || exit 1
```

## 18.2 Prefer liveness/readiness separation in orchestrated systems

Concept:

```text
/liveness
    process is alive

/readiness
    process is ready to receive traffic
```

Do not necessarily make liveness depend on every external dependency.

A temporary MongoDB outage should not always make the process "dead".

---

# 19. Logging

Prefer structured logs to stdout/stderr.

Example:

```json
{
  "timestamp": "2026-10-06T12:00:00Z",
  "level": "INFO",
  "event": "request_completed",
  "status_code": 200
}
```

Avoid:

- writing application logs inside the image filesystem
- secrets in logs
- tokens/passwords in exception messages

Container logging should integrate with the runtime/platform log collector.

---

# 20. Image vulnerability scanning

At minimum, scan every release image.

Example with Docker Scout:

```bash
docker scout cves myorg/myapp:${TAG}
```

Example with Trivy:

```bash
trivy image myorg/myapp:${TAG}
```

Recommended CI policy:

```text
scan
  |
  +-- CRITICAL -> fail
  |
  +-- HIGH     -> fail or security exception
  |
  +-- MEDIUM   -> track
  |
  +-- LOW      -> track
```

Do not blindly fail on every CVE.

Evaluate:

- severity
- exploitability
- whether vulnerable code path is reachable
- whether a fixed package exists
- whether a VEX statement applies
- whether the package is in build-only or runtime stage

---

# 21. SBOM

Generate a Software Bill of Materials.

Build example:

```bash
docker buildx build \
  --sbom=true \
  -t myorg/myapp:${TAG} \
  --push .
```

SBOM should make it possible to answer:

```text
Which packages are inside this image?
Which versions?
Which licenses?
Which transitive dependencies?
```

SBOM is useful for:

- vulnerability management
- incident response
- compliance
- dependency inventory
- supply-chain visibility

---

# 22. Build provenance

Generate provenance:

```bash
docker buildx build \
  --provenance=mode=max \
  --sbom=true \
  -t myorg/myapp:${TAG} \
  --push .
```

Provenance should help answer:

```text
Which source was built?
Which builder built it?
Which base image was used?
How was the image produced?
```

---

# 23. Image signing

Use a signing system such as Cosign for release images.

Concept:

```text
build
  ->
scan
  ->
SBOM/provenance
  ->
sign
  ->
registry
  ->
verify before deployment
```

Production environments can enforce:

> Only deploy signed images from approved repositories.

---

# 24. VEX and false-positive management

Not every CVE reported against an image means the application is exploitable.

Use VEX/OpenVEX where appropriate to describe:

- not affected
- not exploitable
- fixed in another component
- vulnerable package not reachable

Never suppress a CVE just to make CI green.

Every exception should have:

- reason
- owner
- expiry/review date
- evidence

---

# 25. Reproducible release strategy

Use immutable image tags:

```text
myorg/app:git-<commit-sha>
```

and/or digests:

```text
myorg/app@sha256:<IMAGE_DIGEST>
```

Do not make `latest` your production deployment identity.

Recommended:

```text
commit
  ->
build
  ->
scan
  ->
attest
  ->
sign
  ->
push immutable tag
  ->
deploy exact digest
```

---

# 26. CI/CD security gate

Recommended pipeline:

```text
                  Git push
                     |
                     v
              Dockerfile lint
                     |
                     v
               docker build --check
                     |
                     v
              BuildKit build
                     |
            +--------+---------+
            |                  |
           SBOM            provenance
            |                  |
            +--------+---------+
                     |
                     v
                CVE scan
                     |
              +------+------+
              |             |
             FAIL          PASS
              |             |
              x             v
                       image signing
                            |
                            v
                         registry
                            |
                            v
                    deploy exact digest
```

---

# 27. Production Compose baseline

Example:

```yaml
services:
  api:
    image: myorg/fitness-api:${IMAGE_TAG}

    user: "10001:10001"

    read_only: true

    cap_drop:
      - ALL

    security_opt:
      - no-new-privileges:true

    tmpfs:
      - /tmp:size=64m,mode=1777

    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
          pids: 256
        reservations:
          cpus: "0.25"
          memory: 128M

    restart: unless-stopped

    ports:
      - "8000:8000"

    networks:
      - backend

    secrets:
      - mongo_password

networks:
  backend:

secrets:
  mongo_password:
    file: ./secrets/mongo_password.txt
```

Adapt every setting to the actual application.

---

# 28. Production Dockerfile template

```dockerfile
# syntax=docker/dockerfile:1

# ==========================================
# Builder
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
        --no-cache-dir \
        --user \
        -r requirements.txt


# ==========================================
# Runtime
# ==========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN groupadd --system --gid 10001 agent \
    && useradd \
        --system \
        --uid 10001 \
        --gid 10001 \
        --no-create-home \
        agent

COPY --from=builder \
    /root/.local \
    /home/agent/.local

COPY --chown=agent:agent app/ ./app/
COPY --chown=agent:agent utils/ ./utils/

ENV PATH="/home/agent/.local/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=10s \
    --start-period=15s \
    --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Notes:

1. Pin `FROM ...@sha256:<DIGEST>` for environments requiring immutable bases.
2. Add build secrets only when the build actually needs private credentials.
3. Do not copy `.env`, credentials, SSH keys, cloud credentials, certificates with private keys, or local caches into the image.
4. Verify compatibility before switching from `python:3.11-slim` to Alpine/distroless/hardened variants.

---

# 29. Anti-patterns

## Bad: root runtime

```dockerfile
USER root
```

Use a non-root application user.

## Bad: privileged container

```yaml
privileged: true
```

Use narrowly scoped capabilities only if required.

## Bad: all capabilities

```yaml
cap_add:
  - ALL
```

Prefer:

```yaml
cap_drop:
  - ALL
```

## Bad: secrets in Dockerfile

```dockerfile
ENV AWS_SECRET_ACCESS_KEY=...
ARG NPM_TOKEN=...
```

Use BuildKit secrets or the runtime secret mechanism.

## Bad: copy entire project blindly

```dockerfile
COPY . .
```

unless `.dockerignore` and context are deliberately controlled.

## Bad: database exposed unnecessarily

```yaml
ports:
  - "27017:27017"
```

Keep MongoDB private unless host/external access is explicitly required.

## Bad: production deployment by `latest`

```text
myorg/app:latest
```

Prefer immutable tags/digests.

## Bad: ignoring CVEs because the scanner is noisy

Use package upgrades, VEX, documented exceptions, and review dates.

---

# 30. Review checklist

## Build

- [ ] Multi-stage build used where useful.
- [ ] Minimal compatible base image selected.
- [ ] Base image update process defined.
- [ ] Production base can be pinned by digest.
- [ ] Dependency versions are pinned/locked.
- [ ] `.dockerignore` is present and reviewed.
- [ ] Stable files are copied before volatile source.
- [ ] apt uses `--no-install-recommends`.
- [ ] apt cache/indexes are removed in the same layer.
- [ ] pip cache is not baked into runtime image.
- [ ] BuildKit cache mounts are used where beneficial.
- [ ] Build cache is configured in CI where beneficial.
- [ ] `docker build --check` is clean.

## Secrets

- [ ] No secrets in `ARG`.
- [ ] No secrets in `ENV` inside Dockerfile.
- [ ] No `.env` copied into image.
- [ ] BuildKit secrets used for private build credentials.
- [ ] Runtime secrets use secret management.
- [ ] Logs do not print credentials.

## Runtime

- [ ] Non-root user.
- [ ] Fixed UID/GID where useful.
- [ ] Read-only root filesystem tested and enabled where feasible.
- [ ] `/tmp` uses tmpfs if necessary.
- [ ] `cap_drop: ALL`.
- [ ] No unnecessary `cap_add`.
- [ ] `no-new-privileges`.
- [ ] No `privileged: true`.
- [ ] Default seccomp remains enabled or a reviewed profile is used.
- [ ] AppArmor/SELinux considered where supported.
- [ ] CPU limit.
- [ ] Memory limit.
- [ ] PID limit.
- [ ] No host networking unless required.
- [ ] No unnecessary host bind mounts.
- [ ] Database services are not unnecessarily published.

## Supply chain

- [ ] Image vulnerability scanning.
- [ ] SBOM generated.
- [ ] Provenance generated.
- [ ] Release images signed.
- [ ] Image digest recorded.
- [ ] CVE exceptions are documented and time-bounded.
- [ ] CI blocks unacceptable security findings.

## Operations

- [ ] Healthcheck.
- [ ] Liveness/readiness model where orchestrator needs it.
- [ ] Structured logs.
- [ ] Graceful shutdown.
- [ ] Restart policy.
- [ ] Metrics/observability.
- [ ] Host Docker Engine and kernel are patched.

---

# 31. Recommended maturity levels

## Level 1 — Good developer Docker

```text
slim
+ multi-stage
+ .dockerignore
+ pinned Python deps
+ non-root
```

## Level 2 — Production container

```text
Level 1
+ read_only
+ cap_drop ALL
+ no-new-privileges
+ resource limits
+ private networks
+ healthchecks
```

## Level 3 — Production DevSecOps

```text
Level 2
+ base image digest
+ BuildKit secrets
+ CVE scan
+ SBOM
+ provenance
+ immutable image tags
+ CI security gates
```

## Level 4 — High-assurance supply chain

```text
Level 3
+ image signing
+ signature verification
+ VEX
+ rootless/user namespaces where suitable
+ custom seccomp/AppArmor/SELinux policies
+ policy-as-code
+ controlled registry
+ deployment by exact digest
```

---

# 32. Priority for a FastAPI + MongoDB + Redis project

Recommended order:

1. Multi-stage build.
2. `.dockerignore`.
3. Non-root fixed UID.
4. Dependency pinning/lock.
5. Private Docker networks.
6. Never bake secrets into images.
7. `read_only`.
8. `cap_drop: ALL`.
9. `no-new-privileges`.
10. CPU/memory/PID limits.
11. Health/readiness endpoints.
12. CVE scanning.
13. SBOM.
14. Provenance.
15. Immutable image tags/digests.
16. Image signing.
17. Rootless Docker/user namespaces.
18. Custom seccomp/AppArmor/SELinux where justified.

Do not enable every hardening feature blindly. Each restriction must be tested against the application's actual system calls, filesystem writes, networking, startup behavior, and observability.

---

# 33. Reference authority

Primary sources to consult first:

- Docker Build best practices:
  https://docs.docker.com/build/building/best-practices/

- Docker cache optimization:
  https://docs.docker.com/build/cache/optimize/

- Docker build secrets:
  https://docs.docker.com/build/building/secrets/

- Docker build checks:
  https://docs.docker.com/reference/build-checks/

- Docker Engine security:
  https://docs.docker.com/engine/security/

- Docker AppArmor:
  https://docs.docker.com/engine/security/apparmor/

- Docker Compose service security/runtime options:
  https://docs.docker.com/reference/compose-file/services/

- Docker Scout / supply-chain security:
  https://docs.docker.com/guides/docker-scout/

- CIS Docker Benchmark:
  https://www.cisecurity.org/benchmark/docker

- OWASP Docker Security Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

Authority model:

1. Docker official documentation for Docker behavior and configuration.
2. CIS Docker Benchmark for secure configuration controls.
3. OWASP Docker Security Cheat Sheet for application/container security guidance.
4. Project-specific operational testing before enforcing restrictive policies.

---

# 34. One-line mental model

```text
Docker production =
minimal image
+ reproducible build
+ no embedded secrets
+ non-root
+ least privilege
+ read-only filesystem
+ restricted capabilities
+ resource limits
+ private networking
+ vulnerability scanning
+ SBOM
+ provenance
+ signed immutable artifacts
+ hardened host
```
