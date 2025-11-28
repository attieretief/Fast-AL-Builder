# Fast AL Builder

[![GitHub](https://img.shields.io/badge/GitHub-Fast--AL--Builder-blue?logo=github)](https://github.com/attieretief/Fast-AL-Builder)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AL Development](https://img.shields.io/badge/AL-Business%20Central-green)](https://docs.microsoft.com/en-us/dynamics365/business-central/dev-itpro/developer/devenv-programming-in-al)

**Ultra-fast GitHub Action for building, signing, and publishing Microsoft Dynamics 365 Business Central AL extensions.**

## Features

- ⚡ **Multi-runner optimization** - Ubuntu for build/publish, Windows for signing
- 🔍 **Smart symbol resolution** - AppSource, Microsoft, and LINC registries
- ✍️ **Code signing** - Windows SignTool with .pfx certificates
- 🏪 **AppSource publishing** - Automatic product detection and submission
- 🧪 **PR validation** - Fast compilation checks without artifacts

## Quick Start

### Basic Build

```yaml
name: Build AL Extension

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build AL Extension
        uses: attieretief/Fast-AL-Builder@v1
        env:
          LINC_TOKEN: ${{ secrets.LINC_TOKEN }}
```

### With Code Signing and Publishing

```yaml
name: Build and Publish

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build, Sign, and Publish
        uses: attieretief/Fast-AL-Builder@v1
        env:
          LINC_TOKEN: ${{ secrets.LINC_TOKEN }}
          SIGNING_CERT_BASE64: ${{ secrets.SIGNING_CERT_BASE64 }}
          SIGNING_CERT_PASSWORD: ${{ secrets.SIGNING_CERT_PASSWORD }}
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
```

## Configuration

### Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `build-mode` | `test` or `build` | `build` |
| `skip-signing` | Skip code signing step | `false` |
| `skip-publishing` | Skip AppSource publishing | `false` |
| `publish-mode` | `draft`, `submit`, or `auto-promote` | `draft` |
| `timeout-minutes` | Max pipeline wait time | `60` |

### Required Secrets

**For symbol download:**
- `LINC_TOKEN` - LINC authentication token

**For code signing (optional):**
- `SIGNING_CERT_BASE64` - Base64-encoded .pfx certificate
- `SIGNING_CERT_PASSWORD` - Certificate password

**For AppSource publishing (optional):**
- `AZURE_CLIENT_ID` - Service principal client ID
- `AZURE_CLIENT_SECRET` - Service principal secret
- `AZURE_TENANT_ID` - Azure tenant ID

### Outputs

| Output | Description |
|--------|-------------|
| `app-file` | Built .app filename |
| `app-version` | Extension version |
| `build-success` | Build status |
| `signing-success` | Signing status |
| `publishing-success` | Publishing status |

## How It Works

The action uses a multi-runner pipeline for optimal performance:

1. **Build** (Ubuntu) - Fast AL compilation with symbol resolution
2. **Sign** (Windows) - Code signing using SignTool.exe
3. **Publish** (Ubuntu) - AppSource submission

This architecture minimizes Windows runner usage while maintaining compatibility with the AL extension signing format.

## Local Testing

Test the action locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act

# Test workflow
act push -W .github/workflows/your-workflow.yml \
  --secret-file .secrets \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

See [LOCAL_TESTING.md](LOCAL_TESTING.md) for detailed instructions.

## Project Structure

Your AL repository should follow this structure:

```
your-al-repo/
├── app.json              # Required
├── src/                  # AL source files
│   └── *.al
└── .github/
    └── workflows/
        └── build.yml     # Your workflow
```

## Troubleshooting

**Symbol download fails:**
- Verify `LINC_TOKEN` is set correctly
- Check network connectivity to NuGet feeds

**Signing fails:**
- Ensure certificate is valid .pfx format
- Verify base64 encoding is correct
- Check certificate password

**Publishing fails:**
- Confirm app has AppSource ID ranges (100000+)
- Verify Azure service principal has Partner Center API access

Enable debug logging:
```yaml
env:
  ACTIONS_STEP_DEBUG: true
```

## Documentation

- [Local Testing Guide](LOCAL_TESTING.md) - Test with act
- [Contributing Guidelines](CONTRIBUTING.md) - Development setup
- [Changelog](CHANGELOG.md) - Version history

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Made with ❤️ for the Business Central community**
