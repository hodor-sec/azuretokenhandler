# Azure Token Handler

> **⚠️ Work in Progress (WIP)**
>
> This project is actively being developed. Features, authentication flows, arguments, and output may change. Expect occasional bugs and incomplete functionality.

## Overview

Azure Token Handler is a Python utility for acquiring Microsoft Entra ID (Azure AD) OAuth 2.0 access tokens using multiple authentication methods.

The goal of the tool is to simplify testing, security research, development, and troubleshooting by providing a single interface for obtaining tokens for various Azure resources and Microsoft applications.

The tool supports both interactive and command-line usage and includes built-in helpers for common Microsoft client IDs, resource endpoints, and scopes.

---

## Usage

Basic syntax:

```bash
python aztokenhandler.py -m <method> -tid <tenant-id>
```

By default the tool runs in **interactive mode**, prompting you to select:

- Client ID
- Resource
- Scope

You can also provide these values directly using command-line arguments.

---

# Command Line Arguments

| Argument | Description |
|----------|-------------|
| `-m` | Authentication method |
| `-tid` | Tenant ID |
| `-pid` | Partner / Cross-tenant ID |
| `-cid` | Client ID |
| `-r` | Resource |
| `-s` | Scope |
| `-ru` | Redirect URI |
| `-c` | ESTSAUTHPERSISTENT cookie |
| `-un` | Username |
| `-pw` | Password |
| `-tpw` | Temporary Access Pass |
| `-cs` | Client Secret |
| `-rt` | Refresh Token |
| `-cpfx` | PFX certificate |
| `-cpw` | PFX password |
| `-cpk` | PEM private key |
| `-ct` | Certificate thumbprint |
| `-p` | HTTP(S) proxy |
| `-cp` | Copy access token to clipboard |
| `-v` | Verbose JWT output |
| `-t` | Test token against the selected resource |

---

## Features
### Multiple authentication methods
  - Cookie (ESTSAUTHPERSISTENT)
  - Username/password (ROPC)
  - Refresh Token
  - Client Secret
  - Device Code
  - Client Certificate (PEM or PFX)
  - Temporary Access Pass (TAP)(DEFUNCT)

### Interactive selection menus
  - Common Microsoft client IDs
  - Common Azure resource URLs
  - Common OAuth scopes

### Outputs:
  - Access Token
  - Refresh Token
  - ID Token (when available)

### Optional JWT decoding
  - Header
  - Payload
  - Scopes
  - Roles

### Resource validation
  - Microsoft Graph
  - Azure Resource Manager
  - Azure Key Vault
  - Azure Storage

### Copy access token directly to the clipboard

 Proxy support

---

## Supported Authentication Methods

| Method | Description |
|---------|-------------|
| `cookie` | Uses an ESTSAUTHPERSISTENT cookie to obtain an authorization code and exchange it for an access token. |
| `ropc` | Resource Owner Password Credentials flow using username/password. |
| `refresh` | Uses an existing refresh token to obtain a new access token. |
| `secret` | Client Credentials flow using an application client secret. |
| `device` | Device Code flow for interactive authentication. |
| `certificate` | Client Credentials flow using a certificate (PEM or PFX). |
| `tap` | ROPC using a Temporary Access Pass (experimental). |
---

## Included Resources

The interactive menu includes several commonly used Azure resources:

- Microsoft Graph
- Azure Resource Manager
- Azure Resource Manager (Legacy)
- Azure AD Graph (Legacy)
- Azure Key Vault
- Azure Storage
- Azure SQL Database
- Azure Cosmos DB
- Azure Event Hubs
- Azure Service Bus
- Azure DevOps

Custom resources are also supported.

---

## Included Client IDs

Several well-known Microsoft public client IDs are included for convenience:

- Microsoft Azure CLI
- Microsoft Graph PowerShell
- Azure PowerShell
- Azure AD PowerShell
- Microsoft Office
- Microsoft Teams
- Microsoft Copilot
- SharePoint Online
- Microsoft Intune Company Portal
- Microsoft Authentication Broker

A custom application (client ID) option is available, to authenticate using cert's or secrets (SP's).

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<yourrepo>/aztokenhandler.git
cd aztokenhandler
```



---

# Examples

## Device Code Flow

```bash
python token.py -m device -tid <tenant-id>
```

---

## Username / Password (ROPC)

```bash
python token.py \
    -m ropc \
    -tid <tenant-id> \
    -un user@contoso.com \
    -pw Password123!
```

---


## Client Credentials (Client Secret)

```bash
python token.py \
    -m secret \
    -tid <tenant-id> \
    -cid <application-id> \
    -cs <client-secret>
```

---

## Refresh Token

```bash
python token.py \
    -m refresh \
    -tid <tenant-id> \
    -rt <refresh-token>
```

---

## Certificate Authentication (PFX)

```bash
python token.py \
    -m certificate \
    -tid <tenant-id> \
    -cid <application-id> \
    -cpfx certificate.pfx \
    -cpw password
```

---

## Certificate Authentication (PEM)

```bash
python token.py \
    -m certificate \
    -tid <tenant-id> \
    -cid <application-id> \
    -ct <thumbprint> \
    -cpk privatekey.pem
```

---

## Cookie Authentication

```bash
python token.py \
    -m cookie \
    -tid <tenant-id> \
    -c <ESTSAUTHPERSISTENT_COOKIE>
```

---

## Temporary Access Pass (Experimental)

```bash
python token.py \
    -m tap \
    -tid <tenant-id> \
    -un user@contoso.com \
    -tpw ABCDEF123456
```


---

## Testing Resource Access

After acquiring a token, automatically validate it against the selected resource:

```bash
python token.py \
    -m device \
    -tid <tenant-id> \
    -t
```

---

## Verbose JWT Output

Decode the JWT and display its contents:

```bash
python token.py \
    -m device \
    -tid <tenant-id> \
    -v
```

---

## Copy Access Token to Clipboard

```bash
python token.py \
    -m device \
    -tid <tenant-id> \
    -cp
```

---

## Using a Proxy

```bash
python token.py \
    -m device \
    -tid <tenant-id> \
    -p 127.0.0.1:8080
```

---

## Verbose Mode

When `-v` is specified, the tool locally decodes the JWT and displays:

- JWT Header
- JWT Payload
- OAuth scopes (`scp`)
- Application roles (`roles`)

This allows you to quickly inspect the permissions contained within the token without relying on external JWT decoding tools.

---

## Resource Validation

The `-t` switch can automatically validate the obtained token against supported Azure services.

Currently supported:

- Microsoft Graph (`/me`)
- Azure Resource Manager
- Azure Key Vault
- Azure Storage

---

## Disclaimer

This project is intended for:

- Azure administration
- OAuth troubleshooting
- Security research
- Development
- Lab environments
- Authorized security assessments

Only use this tool against tenants, applications, and resources you own or have explicit permission to test.

---

## Project Status

> **🚧 Work in Progress**
>
> This project is under active development. Features, authentication methods, command-line options, and output formats may change between releases. Feedback, issues, and contributions are welcome.
