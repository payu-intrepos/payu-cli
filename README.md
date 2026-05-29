# payu-cli

Command-line interface for PayU payment operations — wraps the [PayU OneAPI](https://oneapi.payu.in) endpoints into a standalone CLI.

## Install

### Quick Install (macOS & Linux)

```bash
curl -fsSL https://payu.in/cli/install.sh | bash
```

This detects your OS and architecture, downloads the binary, and installs it to `~/.local/bin`.

### Manual Download

**macOS (Apple Silicon):**
```bash
curl -fsSL https://payu.in/cli/latest/payu_mac-os_arm64.tar.gz | tar -xz
chmod +x ./payu
sudo mv payu /usr/local/bin/
```

**macOS (Intel):**
```bash
curl -fsSL https://payu.in/cli/latest/payu_mac-os_x86_64.tar.gz | tar -xz
chmod +x ./payu
sudo mv payu /usr/local/bin/
```

**Linux (x86_64):**
```bash
curl -fsSL https://payu.in/cli/latest/payu_linux_x86_64.tar.gz | tar -xz
chmod +x ./payu
sudo mv payu /usr/local/bin/
```

**Linux (ARM64):**
```bash
curl -fsSL https://payu.in/cli/latest/payu_linux_arm64.tar.gz | tar -xz
chmod +x ./payu
sudo mv payu /usr/local/bin/
```

### Verify

```bash
payu version
```

### Install from Source (developers)

Requires Python 3.10+.

```bash
git clone <repo-url> && cd payu-cli
pip install -e .
```

## Configure

```bash
# interactive prompts
payu config set

# or one-liner
payu config set \
  --client-id YOUR_ID \
  --client-secret YOUR_SECRET \
  --merchant-id YOUR_MID \
  --auth-token YOUR_TOKEN

# multiple profiles
payu config set --profile staging --client-id ...
payu config show --profile staging
payu config list

# or use environment variables (no config needed)
export CLIENT_ID=...
export CLIENT_SECRET=...
export MERCHANT_ID=...
export AUTH_TOKEN=...
```

Secrets are stored in the OS keyring when available; falls back to `~/.config/payu-cli/config.json` (chmod 600).

## Commands

### Payment Links

```bash
payu pay create-link --amount 5000 --desc "Web Dev Services" --email abc@example.com
payu pay create-link -a 2500 -d "Consulting" -n "Raj Kumar" -p "+919876543210"
```

### Invoices

```bash
payu pay invoice INV-12345
payu pay invoice INV-12345 --from 2024-01-01 --to 2024-06-30
```

### Transactions

```bash
payu txn get 40368706955
payu txn list --from "2024-01-01 00:00:00" --to "2024-01-31 23:59:59"
payu txn list --from "2024-01-01 00:00:00" --to "2024-01-31 23:59:59" \
  --status captured --mode UPI --limit 50
payu txn summary --from "2024-01-01 00:00:00" --to "2024-01-31 23:59:59" --mode UPI,CC
```

### Refunds

```bash
payu refund search --from 2024-01-01 --to 2024-01-31
payu refund search --from 2024-01-01 --to 2024-01-31 --status success
payu refund summary --from 2024-01-01 --to 2024-01-31
```

### Settlements

```bash
payu settlement get SETL-12345
payu settlement get SETL-12345 --utr UTR123456 --tid TXN789
```

## Building from Source

To produce a standalone binary (no Python required to run):

```bash
pip install pyinstaller
make build
# → dist/payu (standalone binary)
# → dist/payu_mac-os_arm64.tar.gz (release archive)
```

## Architecture

```
payu_cli/
├── __init__.py       # version
├── main.py           # typer app, command groups, config commands
├── config.py         # credential profiles (keyring + file)
├── auth.py           # OAuth client_credentials + direct bearer
├── api.py            # httpx client wrapping all OneAPI endpoints
├── formatters.py     # rich table output for every command
└── commands/
    ├── payments.py       # pay create-link, pay invoice
    ├── transactions.py   # txn get, txn list, txn summary
    ├── refunds.py        # refund search, refund summary
    └── settlements.py    # settlement get
```

## License

MIT
