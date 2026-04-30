# Information Security Policy

**YourExampleCompany** — IT Service Consultation

**Document ID:** POL-005
**Version:** 3.1
**Effective Date:** 2025-01-01
**Owner:** Information Security Office
**Approved by:** CTO, CISO
**Review Cycle:** Semi-annual

---

## 1. Purpose

This policy establishes the requirements for protecting information assets of YourExampleCompany and its clients. As an IT service consultation firm, we handle sensitive data across multiple client environments and must maintain the highest security standards.

---

## 2. Scope

Applies to all systems, networks, data, and personnel involved in storing, processing, or transmitting company and client information.

---

## 3. Data Classification

### 3.1 Classification Levels

| Level | Definition | Examples |
|---|---|---|
| **Public** | Information intended for public disclosure | Marketing materials, job postings |
| **Internal** | For internal use only, not client-specific | Internal processes, team schedules |
| **Confidential** | Client or business-sensitive information | Client source code, architecture docs, contracts |
| **Restricted** | Highly sensitive, regulatory impact | PII, credentials, financial data, health records |

### 3.2 Handling Requirements

- MUST classify all new documents and data assets within 48 hours of creation.
- MUST NOT store Restricted data on personal devices without encryption.
- MUST NOT transmit Confidential or Restricted data via unencrypted channels.
- MUST apply appropriate access controls based on classification level.

---

## 4. Access Control

### 4.1 Authentication
- MUST use multi-factor authentication (MFA) for all company systems and client environments.
- MUST use unique passwords of at least 16 characters for each system.
- MUST NOT share credentials with any other person, including team members.
- MUST NOT store passwords in plain text, browser auto-fill, or unencrypted files.
- MUST use the company-approved password manager (1Password Business) for credential storage.

### 4.2 Authorization
- MUST follow the principle of least privilege — request only the access needed for current tasks.
- MUST revoke access to client systems within 24 hours of project completion.
- MUST review access permissions quarterly for all active projects.
- MUST NOT grant administrative access without written approval from the project lead and security team.

### 4.3 Session Management
- MUST lock workstations when leaving the desk, even briefly.
- MUST NOT leave active sessions to client systems unattended.
- SHOULD configure automatic screen lock after 5 minutes of inactivity.

---

## 5. Endpoint Security

### 5.1 Company Devices
- MUST keep operating systems and software updated within 7 days of patch release.
- MUST enable full-disk encryption on all company laptops and mobile devices.
- MUST run company-approved endpoint detection and response (EDR) software at all times.
- MUST NOT disable security software for any reason without CISO approval.
- MUST NOT install software from untrusted sources on company devices.

### 5.2 Personal Devices (BYOD)
- MUST NOT use personal devices to access client production environments.
- MAY use personal devices for company email and chat with approved MDM enrollment.
- MUST report lost or stolen devices that have accessed company systems within 1 hour.

---

## 6. Network Security

- MUST use the company VPN when accessing internal systems from outside the office.
- MUST NOT connect to public Wi-Fi without VPN protection.
- MUST NOT use client VPN credentials from personal networks without VPN tunneling.
- MUST report suspicious network activity to the Security Operations team immediately.

---

## 7. Client Environment Security

### 7.1 General Rules
- MUST follow the client's security policies in addition to YourExampleCompany policies.
- MUST NOT exfiltrate client data, source code, or intellectual property.
- MUST NOT install unauthorized tools on client systems without client approval.
- MUST use separate browser profiles for each client environment.
- MUST NOT copy client data to local machines unless explicitly authorized and encrypted.

### 7.2 Source Code
- MUST NOT store client source code on personal repositories or cloud storage.
- MUST use only client-approved source control systems.
- MUST NOT share client code across projects or with other clients.
- MUST delete local copies of client repositories within 7 days of project completion.

---

## 8. Incident Response

### 8.1 Reporting Obligations
- MUST report suspected security incidents to security@yourexamplecompany.com within 1 hour of discovery.
- MUST NOT attempt to investigate or remediate incidents independently without security team guidance.
- MUST preserve evidence — do not delete logs, emails, or files related to an incident.

### 8.2 Incident Severity Levels

| Severity | Response Time | Example |
|---|---|---|
| Critical | 15 minutes | Data breach, active intrusion, ransomware |
| High | 1 hour | Credential compromise, unauthorized access |
| Medium | 4 hours | Malware detection, policy violation |
| Low | 24 hours | Phishing attempt (not clicked), minor misconfiguration |

---

## 9. Training and Awareness

- MUST complete security awareness training within 30 days of hire.
- MUST complete annual security refresher training by December 31 each year.
- MUST complete phishing simulation exercises (quarterly).
- SHOULD report phishing attempts to the security team for tracking.

---

## 10. Compliance

- This policy aligns with ISO 27001, SOC 2 Type II, and client-specific requirements.
- Non-compliance may result in disciplinary action, project removal, or termination.
- MUST cooperate with security audits and assessments.

---

*Last reviewed: 2025-01-01 | Next review: 2025-07-01*
