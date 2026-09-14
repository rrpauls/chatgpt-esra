# Install ESRA in Codex

Requires the Codex CLI with plugin support and Python 3.11 or newer.

## Release archive

1. Download `esra-installer.zip` from the latest GitHub Release and extract it.
2. In a terminal, replace `/absolute/path/to/esra-installer` with the extracted directory:

   ```bash
   codex plugin marketplace add /absolute/path/to/esra-installer
   codex plugin add chatgpt-esra@esra
   ```

3. Start a new Codex task. Review the local lifecycle hook with `/hooks`; disable it there if you only want the five ESRA skills.

The runtime writes private local state to `PLUGIN_DATA` when installed as a plugin. It does not require Hermes or write to Hermes paths.

## Skills only

To install only the five portable skills, without the Codex runtime or hook:

```text
$skill-installer install every skill from https://github.com/rrpauls/chatgpt-esra/tree/main/skills for my user scope
```

## Remove

```bash
codex plugin remove chatgpt-esra@esra
codex plugin marketplace remove esra
```

