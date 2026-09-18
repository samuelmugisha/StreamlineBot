# Contributing

## Setup

See [README.md](README.md) for full setup instructions. For development
tooling:

```bash
# Backend
pip install -r requirements-dev.txt

# Frontend
cd frontend && npm install
```

## Workflow

1. Branch off `main`: `git checkout -b feature/short-description`
2. Make your change, with tests
3. Run the checks below locally
4. Open a Pull Request — CI must pass before merge

## Before opening a PR

**Backend:**
```bash
ruff check backend Tests        # lint
ruff format backend Tests       # format
pytest                          # tests + coverage
```

**Frontend:**
```bash
cd frontend
npm run lint
npm run format
npm run test
npm run build
```

## Commit messages

Keep them short and focused on *why*, not just *what*. No strict convention
is enforced, but a clear one-line summary is expected.

## Code review

Every PR needs review before merging to `main`. See `.github/CODEOWNERS`
for default reviewers. Address review comments with new commits rather than
force-pushing over history mid-review, unless asked to squash.

## Reporting bugs / requesting features

Use the GitHub issue templates (`.github/ISSUE_TEMPLATE/`).

## Security issues

Do **not** open a public issue for a security vulnerability — see
[SECURITY.md](SECURITY.md).
