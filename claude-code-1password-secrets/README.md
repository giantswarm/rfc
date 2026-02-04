---
creation_date: 2025-02-04
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-up
state: review
summary: A guide for securely using Claude Code CLI and IDE plugins on Linux by storing secrets in 1Password and running the tool in a sandboxed environment using bubblewrap.
---

# Securely Using Claude Code CLI with 1Password Secrets on Linux

## Problem Statement

Claude Code CLI (and IDE plugins) can execute arbitrary commands, including those that require authentication tokens (e.g., `gh`, `devctl`, `opsctl`). Storing these secrets as plain environment variables or in dotfiles poses security risks:

1. **Secret exposure**: Claude Code could accidentally leak secrets in logs, error messages, or when suggesting commands.
2. **Overly broad access**: The tool might access files or directories outside the intended project scope.
3. **Credential persistence**: Secrets stored in shell profiles or environment files remain accessible even when not needed.

## Proposed Solution

Use a combination of:

1. **1Password service accounts** with dedicated, limited-scope vaults for AI tool access
2. **1Password CLI (`op`)** for just-in-time secret injection via `op://` URIs
3. **Bubblewrap (`bwrap`)** sandboxing to restrict filesystem access and isolate the Claude Code process

This approach ensures secrets are never directly exposed to Claude Code while still allowing authenticated commands to work seamlessly.

## Implementation

### Step 1: Create a Dedicated 1Password Vault

1. Log into [1Password Web](https://1password.com) and create a new vault named `ai-$NAME` (e.g., `ai-jonas`).
2. Add the secrets Claude Code will need (e.g., `OPSCTL_GITHUB_TOKEN`) to this vault.

### Step 2: Create a 1Password Service Account

1. Create a 1Password service account named `ai-$NAME` with access **only** to the `ai-$NAME` vault.
2. Store the service account token in your personal `Employee` vault, naming it `service-account-token-ai-$NAME`.

This ensures the service account has minimal permissions—only accessing secrets explicitly placed in the AI vault.

### Step 3: Create the Launcher Script

Create a script (e.g., `~/bin/run-claude.sh`) that:

- Retrieves the service account token from 1Password
- Launches Claude Code inside a bubblewrap sandbox
- Passes secrets as `op://` URIs (not raw values)

```bash
#!/bin/sh
PROJECT_DIR="$(realpath .)"
if [ -s "$1" ]; then
    PROJECT_DIR="$(realpath "$1")"
fi

# Safety check: prevent running in home or root directories
if [ "$PROJECT_DIR" = "$(realpath "$HOME")" ] || [ "$PROJECT_DIR" = "$(realpath /)" ]; then
    echo "Error: don't give Claude access to high-level directories! Run it somewhere else." 1>&2
    exit 1
fi

# Configuration
vault="ai-jonas"  # Change to your vault name
account_token="$(op item get --vault 'Employee' "service-account-token-$vault" --reveal --fields credential)"

bwrap \
    --ro-bind /usr /usr \
    --ro-bind /lib /lib \
    --ro-bind /lib64 /lib64 \
    --ro-bind /bin /bin \
    --ro-bind /etc/resolv.conf /etc/resolv.conf \
    --ro-bind /etc/hosts /etc/hosts \
    --ro-bind /etc/ssl /etc/ssl \
    --ro-bind /etc/passwd /etc/passwd \
    --ro-bind /etc/group /etc/group \
    --ro-bind "$HOME/.gitconfig" "$HOME/.gitconfig" \
    --ro-bind "$HOME/.1password" "$HOME/.1password" \
    --ro-bind "$HOME/.nvm" "$HOME/.nvm" \
    --ro-bind "$HOME/.local" "$HOME/.local" \
    --ro-bind "$HOME/.ssh" "$HOME/.ssh" \
    --ro-bind "$HOME/.config/gh" "$HOME/.config/gh" \
    --dir "$XDG_RUNTIME_DIR" \
    --ro-bind "$HOME/bin" "$HOME/bin" \
    --bind "$PROJECT_DIR" "$PROJECT_DIR" \
    --bind "$HOME/.claude" "$HOME/.claude" \
    --bind "$HOME/.claude.json" "$HOME/.claude.json" \
    --bind "$HOME/.local/share/claude" "$HOME/.local/share/claude" \
    --bind "$HOME/.m2" "$HOME/.m2" \
    --bind "$HOME/.gradle" "$HOME/.gradle" \
    --bind "$HOME/go" "$HOME/go" \
    --bind "$HOME/.npm" "$HOME/.npm" \
    --bind "$HOME/.java" "$HOME/.java" \
    --bind "$HOME/.cache/pip" "$HOME/.cache/pip" \
    --bind "$HOME/.cache/helm" "$HOME/.cache/helm" \
    --bind "$HOME/.cache/go" "$HOME/.cache/go" \
    --bind "$HOME/.cache/go-build" "$HOME/.cache/go-build" \
    --setenv "OP_SERVICE_ACCOUNT_TOKEN" "$account_token" \
    --setenv "GH_TOKEN" "op://$vault/OPSCTL_GITHUB_TOKEN/password" \
    --setenv "GITHUB_TOKEN" "op://$vault/OPSCTL_GITHUB_TOKEN/password" \
    --setenv "OPSCTL_GITHUB_TOKEN" "op://$vault/OPSCTL_GITHUB_TOKEN/password" \
    --tmpfs /tmp \
    --proc /proc \
    --dev /dev \
    --share-net \
    --unshare-pid \
    --die-with-parent \
    --setenv IS_SANDBOX 1 \
    --chdir "$PROJECT_DIR" \
    --ro-bind /dev/null "$PROJECT_DIR/.env" \
    --ro-bind /dev/null "$PROJECT_DIR/.env.local" \
    --ro-bind /dev/null "$PROJECT_DIR/.env.production" \
    "$(command -v claude)" --dangerously-skip-permissions
```

Make the script executable:

```bash
chmod +x ~/bin/run-claude.sh
```

### Step 4: Configure Claude Code to Use `op run`

Claude Code must be instructed to prefix authenticated commands with `op run --` so that 1Password injects the actual secret values at runtime.

Add the following to your project's `.claude/CLAUDE.md` or global Claude settings:

```markdown
# 1Password Integration

When running commands that require authentication tokens (gh, devctl, opsctl, etc.),
prefix them with `op run --` to inject secrets from 1Password.

Example:
- Instead of: `gh pr list`
- Use: `op run -- gh pr list`

This allows secrets stored as `op://` URIs to be resolved at runtime.
```

### Step 5: IDE Plugin Configuration

Configure your IDE's Claude Code plugin to use the launcher script instead of calling `claude` directly:

- **VS Code**: Update the `claude-code.executablePath` setting to point to `~/bin/run-claude.sh`
- **JetBrains IDEs**: Configure the Claude Code plugin's executable path in Settings

## Security Properties

This setup provides several security guarantees:

| Property | Mechanism |
|----------|-----------|
| **Secret isolation** | Secrets exist only as `op://` URIs; actual values are injected only when `op run` executes |
| **Minimal vault access** | Service account can only access the dedicated AI vault, not your Employee vault |
| **Filesystem sandboxing** | Bubblewrap restricts access to only necessary paths; project `.env` files are masked |
| **Process isolation** | `--unshare-pid` prevents the sandboxed process from seeing other processes |
| **Scope limitation** | Script refuses to run in `$HOME` or `/` directories |

## Customization

### Adding More Secrets

To add additional secrets for Claude Code to use:

1. Add the secret to your `ai-$NAME` vault in 1Password
2. Add a `--setenv` line to the bwrap command with the `op://` URI:
   ```bash
   --setenv "MY_NEW_TOKEN" "op://$vault/my-secret-name/password" \
   ```

### Adjusting Filesystem Access

Modify the `--ro-bind` (read-only) and `--bind` (read-write) lines to match your development environment. The current configuration supports:

- Node.js (`.nvm`, `.npm`)
- Java (`.m2`, `.gradle`, `.java`)
- Go (`go`, `.cache/go`, `.cache/go-build`)
- Python (`.cache/pip`)
- Kubernetes/Helm (`.cache/helm`)

## Prerequisites

- **1Password CLI** (`op`): Install from [1Password CLI documentation](https://developer.1password.com/docs/cli/)
- **Bubblewrap** (`bwrap`): Install via your package manager (e.g., `apt install bubblewrap`)
- **Claude Code CLI**: Install from [Anthropic](https://docs.anthropic.com/en/docs/claude-code)

## Open Questions

- Should we provide a centralized, team-managed vault instead of individual `ai-$NAME` vaults?
- How should this integrate with CI/CD pipelines that also use Claude Code?
- Could the `run-claude.sh` script be improved, e.g. to make it more compatible or protect the service account token better?

## References

- [1Password Service Accounts](https://developer.1password.com/docs/service-accounts/)
- [1Password Secret References (op:// URIs)](https://developer.1password.com/docs/cli/secret-references/)
- [Bubblewrap Documentation](https://github.com/containers/bubblewrap)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
