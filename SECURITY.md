# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability, **please do not open a public issue**.

Report it privately via [GitHub Security Advisories](https://github.com/wvogel/uptime-kuma-status/security/advisories/new).

You will receive an acknowledgement within a few days. Once the issue is
confirmed, a fix is released before the advisory goes public.

## Scope

In scope:

- The uptime-status admin and public FastAPI applications
- The Docker images built from this repository
- SQLite schema and data handling (API key encryption, SQL injection, etc.)
- The oauth2-proxy integration as configured in this repo

Out of scope:

- Vulnerabilities in Uptime Kuma itself — report those to
  [louislam/uptime-kuma](https://github.com/louislam/uptime-kuma)
- The [uptime-kuma-api](https://github.com/wvogel/uptime-kuma-api) sidecar —
  report there directly
- Third-party images (Valkey, oauth2-proxy, Nginx Proxy Manager, etc.)

## Supported versions

Only the `main` branch is supported. Security fixes are released as new commits
on `main`; there are no backports to earlier tags.
