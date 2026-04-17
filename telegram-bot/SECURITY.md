# Security Policy

## Supported Versions

| Version | Supported | Status |
|---------|-----------|--------|
| 4.x.x | ✅ | Active Development |
| 3.x.x | ❌ | Deprecated |
| 2.x.x | ❌ | Deprecated |
| 1.x.x | ❌ | Deprecated |

## Reporting a Vulnerability

We take security seriously at Estif Bingo 24/7. If you discover a security vulnerability, please report it to us immediately.

### How to Report

1. **Email**: Send details to `security@estifbingo.com`
2. **Telegram**: Contact @estif_bingo_admin on Telegram
3. **Encrypted Communication**: Use our PGP key (available upon request)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (if available)
- Your contact information (optional)

### Response Timeline

| Step | Timeframe |
|------|-----------|
| Initial Acknowledgment | Within 24 hours |
| Vulnerability Assessment | Within 3 business days |
| Fix Development | Within 7-14 business days |
| Patch Release | Within 24 hours after fix |

### Disclosure Policy

- We will coordinate with you on public disclosure
- We will credit reporters who find valid vulnerabilities (with permission)
- We do not offer bug bounties at this time

---

## Security Measures

### 1. Data Encryption

#### At Rest
- **Phone Numbers**: Encrypted using Fernet (symmetric encryption)
- **Bank Details**: Encrypted using Fernet before storage
- **Passwords**: Hashed using bcrypt with salt
- **API Keys**: Hashed using SHA-256
- **OTP Codes**: Hashed before storage

#### In Transit
- **All API Traffic**: TLS 1.2+ required
- **WebSocket Connections**: WSS (WebSocket Secure)
- **Database Connections**: SSL/TLS enforced

### 2. Authentication & Authorization

#### JWT Tokens
- Access tokens expire after 2 hours
- Refresh tokens expire after 7 days
- Tokens are signed using HS256
- Separate tokens for WebSocket connections (5-minute expiry)

#### API Keys
- Generated using cryptographically secure random generator
- Stored as hashed values
- Permission-based access control
- Auto-expiration support

#### Admin Access
- Multi-factor authentication required
- IP whitelisting optional
- Session timeout: 24 hours
- All admin actions are logged

### 3. Rate Limiting

| Endpoint Type | Rate Limit | Window |
|---------------|------------|--------|
| Authentication | 5 requests | 60 seconds |
| Deposit/Withdrawal | 10 requests | 60 seconds |
| Game Actions | 30 requests | 60 seconds |
| General API | 100 requests | 60 seconds |
| OTP Generation | 3 requests | 60 seconds |

### 4. Input Validation

All user inputs are validated and sanitized:

- **Phone Numbers**: Regex pattern matching
- **Amounts**: Numeric validation with min/max bounds
- **Transaction IDs**: Alphanumeric validation
- **Bank Accounts**: Format and length validation
- **SQL Queries**: Parameterized queries only
- **HTML Output**: Auto-escaped by Jinja2

### 5. Database Security

- Connection pooling with max lifetime
- Prepared statements for all queries
- Automatic connection encryption
- Regular security audits
- Automated backups (encrypted)
- Audit logging for all critical operations

### 6. Web Security Headers

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin