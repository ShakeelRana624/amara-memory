# Security Policy

The AMARA project takes the security and integrity of cognitive memory systems seriously.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within AMARA, please report it responsibly rather than opening a public issue.

- **Email**: security@amara.ai (or open a private security advisory on GitHub)
- **Response Timeline**: The maintainers will acknowledge receipt within 48 hours and provide a vulnerability assessment within 5 business days.

When submitting a vulnerability report, please include:
- A clear description of the potential vulnerability.
- Steps to reproduce or a minimal proof of concept (PoC).
- The affected AMARA version and runtime environment.
- Potential impact on memory stores, agent context isolation, or data confidentiality.

## Security Considerations for Cognitive Memory

When building with AMARA:
- **Credential Storage**: Never store API tokens, private encryption keys, or sensitive credentials within agent cognitive memories.
- **Context Isolation**: Ensure multi-tenant or multi-agent memory namespaces are strictly separated when using shared persistence backends.
- **Input Sanitization**: Validate and sanitize external memory injections to mitigate prompt-injection and indirect context-tampering risks.

