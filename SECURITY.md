# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability within Atomic Search, please follow responsible disclosure:

1. **DO NOT** create a public GitHub issue
2. Send details to security@atomic-search.dev
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

We aim to respond within 48 hours and will work with you to:

- Confirm the vulnerability
- Determine severity
- Develop a fix
- Credit you (if desired) in the release notes

## Security Features

### Zero Telemetry
- No analytics
- No tracking
- No telemetry

### Data Protection
- Encrypted session storage
- Secure password hashing (PBKDF2)
- API key validation

### Request Security
- CSRF protection
- Rate limiting
- Input sanitization
- XSS prevention

### Headers
All responses include security headers:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Referrer-Policy: strict-origin-when-cross-origin
```

## Best Practices

### For Users
1. Use HTTPS in production
2. Set a strong SECRET_KEY
3. Enable rate limiting
4. Keep the application updated

### For Self-Hosting
1. Use a reverse proxy with TLS
2. Enable fail2ban for SSH
3. Use a firewall
4. Regular backups

## Security Updates

Security updates will be released promptly. Follow the repository to get notified of new releases.
