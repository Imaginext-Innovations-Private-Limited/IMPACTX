## Summary

<!-- Describe what this PR changes and why. Reference the issue or track if applicable (e.g., Closes #12). -->

## Module / Track

- [ ] `packages/contracts` (requires schema regeneration + `make verify`)
- [ ] `packages/clinical-engine`
- [ ] `packages/crdt-sync`
- [ ] `services/phc-hub`
- [ ] `services/ml-pipeline` (Track 4)
- [ ] `apps/field-pwa` (Track 2)
- [ ] `apps/watch-companion` (Track 3)
- [ ] Docs / CI / Root config

## Checklist

- [ ] PR title follows Conventional Commits (`feat(scope): summary`)
- [ ] Changes stay strictly within my owned module (no unapproved edits to shared contracts or other tracks)
- [ ] `make lint` (`ruff check .`) passes with zero errors
- [ ] `make test` (`pytest -v`) passes locally
- [ ] `make verify` passes locally (if contracts or core packages were touched)
- [ ] Zero PyTorch / CUDA / TensorFlow bloat introduced
- [ ] Clinical safety floor respected (SLM/ML never overrides deterministic danger-sign triage)
- [ ] Tested offline / Airplane Mode behavior (where applicable)
