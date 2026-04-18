# Contributing

Thanks for considering a contribution! This project is a small, opinionated status
page for Uptime Kuma — the goal is to stay focused and simple.

## Reporting issues

Before opening an issue please search existing ones. For bugs, include:

- What you expected
- What actually happened
- Steps to reproduce
- Version (commit hash), browser, and `docker compose logs` output if relevant

## Proposing features

Open a discussion or an issue first — larger features may not fit the project's
scope and it's a waste of your time to implement something that won't be merged.

## Pull requests

1. Fork the repo and create a topic branch from `main`.
2. Keep changes focused — one PR per concern.
3. Match the existing code style. No linters/formatters enforced, but try to
   leave the code at least as clean as you found it.
4. Update `CHANGELOG.md` under the `[Unreleased]` section.
5. Bump the `?v=N` static asset version in the templates if you changed CSS/JS.

## Local development

```bash
cp .env.example .env
cp oauth2-proxy.env.example oauth2-proxy.env
# fill in secrets
docker compose up -d
```

The admin runs at the container on port 80 behind oauth2-proxy; the public page
is on the `uptime-status-public` service.

## Commit messages

Short imperative subject line. Reference the "why" when it isn't obvious.

## License

By contributing, you agree that your contributions will be licensed under the
project's MIT license.
