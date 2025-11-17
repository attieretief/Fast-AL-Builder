# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Fast AL Builder GitHub Action
- Support for AL compilation with automated symbol management
- Intelligent dependency resolution from NuGet and custom registries
- Smart version generation based on git events and branches
- Azure Key Vault code signing integration
- AppSource publishing with automatic product detection
- PR check mode for fast compilation validation
- Multi-version support for different BC versions
- Configurable build targeting (OnPrem/Cloud)

### Features
- **Environment Setup**: Automatic installation of AL compiler from NuGet
- **Project Analysis**: Intelligent parsing of app.json and build configuration
- **Symbol Management**: Download Microsoft BC symbols and dependency symbols
- **Build Process**: Compilation with version management and permission cleanup
- **Code Signing**: Azure Key Vault integration with cross-platform support
- **AppSource Publishing**: Automated submission to Microsoft AppSource
- **Multi-Version Support**: Support for BC17, BC18, BC19, BC22, BC Cloud versions

### Scripts
- `install-al-compiler.sh` - AL compiler installation and setup
- `analyze-project.sh` - AL project analysis and configuration
- `download-symbols.sh` - Symbol and dependency management
- `build-extension.sh` - AL compilation with version management
- `code-sign.sh` - Azure Key Vault code signing
- `publish-appsource.sh` - AppSource publishing automation

### Examples
- Basic workflow example
- Advanced workflow with code signing and AppSource
- Multi-version matrix build example

### Documentation
- Comprehensive README with usage examples
- Contributing guidelines
- MIT License
- Example workflows for different scenarios

## [1.0.0] - 2024-11-17

### Added
- Initial release