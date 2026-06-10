# Security Policy

## Supported versions

Security fixes are applied to the latest release on the default branch.

## Reporting a vulnerability

Please **do not** open public GitHub issues for security vulnerabilities.

Report privately via GitHub Security Advisories (preferred) or email **security@aicery.dev**.

Include: description, reproduction steps, impact, and affected components.

## Production defaults

- Change `API_KEY` from `dev` before any internet-facing deployment.
- Set `JWT_SECRET` to a strong random value when `JWT_ENABLED=true`.
- Do not commit `.env` files or API keys.
- The default Docker Compose stack is for **local development** only.

## Scope

In scope: runtime API, CLI, SDKs, tool sandbox boundaries, gateway service.

Out of scope: example application business logic under `examples/`.
