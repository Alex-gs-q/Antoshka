# Support and Troubleshooting

## Quick Diagnostics

Run from packaged folder build:

```powershell
.\AntoshkaApp.exe --self-test
.\AntoshkaApp.exe --smoke
```

Expected:

- `SELF-TEST OK`
- `SMOKE OK`

## Common Problems

### App does not start

1. Move package to latin-only path, for example `C:\Antoshka\`.
2. Check write access to `%TEMP%` and `%LOCALAPPDATA%\Temp`.
3. Temporarily allow app in SmartScreen/Defender.

### Onefile fails at startup

If you see `Failed to create parent directory structure`:

1. Use folder build or installer package (recommended).
2. Run debug onefile build and share console output.

### Microphone is not working

1. Enable microphone permissions in Windows privacy settings.
2. Verify `stt.mode` in `config/settings.json`.
3. Use text mode for demo if mic is unavailable.

### No AI response

1. Set `OPENAI_API_KEY` in environment.
2. Ensure provider is configured in `config/settings.json`.
3. Check network access and request limits.

## What to Include in Bug Report

1. App version and commit hash
2. Exact command used
3. Full stdout/stderr or screenshot
4. File `pre_release_report.txt` if available

