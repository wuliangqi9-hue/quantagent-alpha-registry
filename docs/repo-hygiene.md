# Repository Hygiene

Before publishing the GitHub repository, make sure generated and secret files
are excluded.

## Must Not Commit

- `.env` or `.env.*` files with secrets;
- private keys;
- `node_modules/`;
- `.venv/`;
- `dist/`;
- `cache/`;
- large build-info artifacts;
- Hardhat debug artifacts (`*.dbg.json`);
- logs or PID files.

## Can Commit

- source code;
- sample CSVs for offline demo mode;
- Solidity contract source;
- compact contract ABI artifacts (`contracts/artifacts/contracts/**/*.json`) when
  needed by the API or deployment docs;
- README and submission docs.

## Recommended Final Check

```bash
git status --short
```

Inspect every file before pushing. The final repo should look intentional, not
like a local working directory dump.

On Windows, you can remove common generated files with:

```powershell
.\scripts\clean_generated.ps1
```
