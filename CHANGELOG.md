# Changelog

All notable changes to this project are documented in this file.

## [0.4.0-alpha] - 2026-02-13

### Added
- Headless `--self-test` mode with watchdog and clear OK/FAIL exit codes.
- Headless `--smoke` mode available from packaged build.
- Onefile debug spec (`Antoshka_onefile_debug.spec`) with console diagnostics.
- Friend-ready and installer-ready release packages in `release/`.

### Changed
- Early CLI argument parsing before heavy GUI/audio imports.
- Logging fallback behavior for restricted environments.
- README updated with alpha status, troubleshooting, compatibility and packaging notes.

### Fixed
- Frozen settings fallback path handling.
- Safer runtime checks for packaged resource availability.

### Known Issues
- Onefile can fail on some Windows systems before Python starts with bootloader temp extraction error.
- Recommended user distribution is folder build / installer package.

