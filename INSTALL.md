# Install ESRA for ChatGPT and Codex

ESRA is one plugin containing five skills. Python 3.11 or newer is required for the optional local runtime and hook.

## ChatGPT Desktop

Add the released GitHub marketplace:

```bash
codex plugin marketplace add rrpauls/chatgpt-esra --ref v0.4.1
```

Restart ChatGPT Desktop, open **Plugins**, select the **ESRA for OpenAI** source, and install **ESRA for OpenAI**. Start a new chat after installation.

Availability depends on your ChatGPT plan, workspace permissions, and product rollout. A workspace administrator can distribute ESRA by opening **Admin > Plugins > Add > Import marketplace**, entering `https://github.com/rrpauls/chatgpt-esra`, and selecting tag `v0.4.1`.

## Codex

```bash
codex plugin marketplace add rrpauls/chatgpt-esra --ref v0.4.1
codex plugin add chatgpt-esra@esra
```

Start a new Codex task. Review the local lifecycle hook with `/hooks`; disable it there if you only want the five skills.

## Release ZIP

For an offline/local install, download and extract `esra-installer.zip`, then use the extracted directory instead of GitHub:

```bash
codex plugin marketplace add /absolute/path/to/esra-installer
```

Then install from ChatGPT Desktop as above, or run `codex plugin add chatgpt-esra@esra` for Codex.

The hook runs only where the local execution environment is available. Installing the plugin on the web does not deploy local scripts. ESRA does not require Hermes or write to Hermes paths.

## Remove

```bash
codex plugin remove chatgpt-esra@esra
codex plugin marketplace remove esra
```
