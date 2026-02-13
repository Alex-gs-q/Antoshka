# Release Notes Template

## Antoshka v0.x.x-alpha (YYYY-MM-DD)

### Highlights
- 
- 
- 

### New
- 

### Improved
- 

### Fixed
- 

### Packaging
- Folder build:
  - `dist/AntoshkaApp/AntoshkaApp.exe`
- Onefile build:
  - `dist/Antoshka_onefile.exe`
  - `dist/Antoshka_onefile_debug.exe`
- Transfer packages:
  - `release/AntoshkaApp_friend_ready.zip`
  - `release/AntoshkaApp_installer_ready.zip`

### Validation
- `--self-test`: PASS/FAIL
- `--smoke`: PASS/FAIL
- `pytest -q`: PASS/FAIL

### Known Issues
- Onefile may fail on some systems with temp extraction error.
- Workaround: use folder build/installer package.

