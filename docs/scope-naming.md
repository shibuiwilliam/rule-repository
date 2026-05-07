# Scope Naming Convention

Rules in the Rule Repository are organized by **scope** — a hierarchical label that determines which rules apply to a given evaluation context.

## Format

```
<domain>/<area>[/<region>][/<sub>]
```

- **domain** — The top-level organizational function (e.g., `engineering`, `hr`, `legal`)
- **area** — A specific area within the domain (e.g., `python`, `attendance`, `nda`)
- **region** — Optional geographic qualifier (e.g., `jp`, `us`, `eu`)
- **sub** — Optional further specialization

## Standard Domains

| Domain | Description | Example Scopes |
|--------|-------------|----------------|
| `engineering` | Software development and DevOps | `engineering/python`, `engineering/api`, `engineering/database`, `engineering/security` |
| `hr` | Human resources and people operations | `hr/attendance/jp`, `hr/recruitment`, `hr/compensation`, `hr/training` |
| `legal` | Legal affairs and contract management | `legal/contracts/nda`, `legal/contracts/msa`, `legal/ip`, `legal/litigation` |
| `finance` | Financial operations and accounting | `finance/expenses/jp`, `finance/invoices`, `finance/revenue`, `finance/tax/jp` |
| `compliance` | Regulatory compliance and governance | `compliance/anti-bribery`, `compliance/privacy/jp`, `compliance/aml`, `compliance/export-control` |
| `sales` | Sales operations and customer engagement | `sales/pipeline`, `sales/pricing`, `sales/contracts`, `sales/commission` |
| `marketing` | Marketing and advertising | `marketing/brand`, `marketing/advertising/jp/pharma`, `marketing/content`, `marketing/events` |
| `infosec` | Information security | `infosec/access-control`, `infosec/incident-response`, `infosec/data-classification` |
| `esg` | Environmental, social, and governance | `esg/environment`, `esg/diversity`, `esg/supply-chain`, `esg/reporting` |
| `procurement` | Vendor and supplier management | `procurement/vendor-selection`, `procurement/contracts`, `procurement/payment` |

## Conventions

1. **Lowercase, slash-separated.** No spaces, no underscores in the path.
2. **Region codes use ISO 3166-1 alpha-2.** `jp` for Japan, `us` for United States, `eu` for EU, `gb` for United Kingdom.
3. **Global scope.** Rules without a region qualifier apply globally.
4. **Specificity wins.** During evaluation, more specific scopes override less specific ones. A rule scoped to `hr/attendance/jp` takes precedence over one scoped to `hr/attendance` for Japanese employees.
5. **Multiple scopes.** A rule may belong to multiple scopes: `["compliance/anti-bribery", "finance/expenses/jp"]`.
6. **Wildcards in queries.** The search API supports prefix matching: searching for `compliance/*` returns all compliance rules.

## Examples

### Engineering
```yaml
scope: ["engineering/python"]           # Python coding standards
scope: ["engineering/python/api"]       # Python API-specific rules
scope: ["engineering/database"]         # Database design and migration rules
scope: ["engineering/security"]         # Application security rules
```

### HR
```yaml
scope: ["hr/attendance/jp"]            # Japanese attendance and overtime rules
scope: ["hr/recruitment"]              # Hiring and interview rules
scope: ["hr/compensation/jp"]          # Japanese compensation rules
```

### Legal
```yaml
scope: ["legal/contracts/nda"]         # NDA review rules
scope: ["legal/contracts/msa"]         # MSA review rules
scope: ["legal/ip"]                    # Intellectual property rules
```

### Finance
```yaml
scope: ["finance/expenses/jp"]         # Japanese expense claim rules
scope: ["finance/invoices"]            # Invoice processing rules
scope: ["finance/tax/jp"]              # Japanese tax compliance
```

### Compliance
```yaml
scope: ["compliance/anti-bribery"]     # Anti-corruption (global)
scope: ["compliance/privacy/jp"]       # APPI privacy rules
scope: ["compliance/privacy/eu"]       # GDPR privacy rules
scope: ["compliance/advertising/jp/pharma"]  # Yakukiho advertising
```
