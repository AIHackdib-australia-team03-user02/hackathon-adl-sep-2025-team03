## Policy Assessment

## 1. Policy Assessment

The organisation’s policy library incorporates a broad and authoritative set of Australian Government, Defence, and international cyber security standards and guidance.

**Strengths**  
- **ISM & IRAP** – *Current* (March 2025) ACSC *Information Security Manual* and “ISM March 2025 changes” provide up‑to‑date control requirements. Comprehensive IRAP governance, methodology, and templates are present (policy, examination guidance, common assessment framework, confidentiality deed, consumer guide, 2025 report template).  
- **Technical Implementation** – ASD Microsoft 365 Blueprint *Essential Eight* configuration guides (application control, MFA, patching, backups), plus the “Essential Eight Assessment Report Template” are included.  
- **Protective Security** – PSPF-linked artefacts such as the Australian Government Email Protective Marking Standard, Gateway Policy, and Hosting Certification Framework (Mar 2021) are available.  
- **Legislative/Contractual Context** – Legislative instruments (F2024L01024 + explanatory statement), Defence Export Controls guides, DFARS 252.204‑7012, and export control rules are covered.  
- **Cross‑Framework Mapping** – NIST SP 800‑171/172/221 assessment procedures and CMMC assessment process content allow for international alignment and crosswalk.

**Gaps / Issues**  
- No explicit internal *Statement of Applicability* mapping current organisational implementation against each ISM control.  
- No clear operational risk management/governance policies for ongoing control monitoring, change management, or incident response.  
- Lack of supplementary procedural documentation for ISM’s physical security, personnel security, and supply‑chain control families beyond partial PSPF coverage.  
- No evidence of tools or process for continuous compliance tracking against ISM updates.  
- Policy artefacts do not specify internal ownership/accountabilities per control area.  
- No documented remediation planning template/process aligned to IRAP assessment outputs.  
- **Freshness risk** – Core ISM/IRAP artefacts are current, but ancillary documents such as Hosting Certification Framework (Mar 2021) may require review in absence of a formal update cycle.

---

## 2. Compliance Summary

| Domain / Control Area | Status   | Notes / Evidence |
|-----------------------|----------|------------------|
| **ISM Policy Coverage** | Partial | Strong coverage of cyber controls via ISM/IRAP artefacts; missing SoA, risk mgmt, and some non‑cyber control families. |
| **Hardening – ISM-OS‑01** | Gap     | SMBv1 & weak NTLM still enabled; fails ASD Windows hardening ([Azure Policy scan evidence]). |
| **Hardening – ISM-APP‑04** | Comply  | Application control in enforce mode via Defender policies. |
| **Hardening – ISM-AUTH‑05** | Gap     | MFA not enforced for privileged “break glass” accounts. |
| **Hardening – ISM-VIRT‑02** | Comply  | Hardened STIG VM images in use via Azure Blueprints. |
| **Monitoring Coverage** | Gap     | Endpoint events only; lacks identity, network, cloud app, and non‑Windows telemetry; no alert‑rule mapping; 0‑day retention configured. |
| **Cryptography** | Partial | Strong algorithms in place; some legacy/weak protocol support remains for interoperability; exceptions require formal risk acceptance. |
| **Network Segmentation** | Gap     | User↔Server VLANs too open (RDP/SMB); Guest WiFi unrestricted; DMZ↔Server DB flows risky. |
| **Network Egress Control** | Gap     | No deny‑by‑default; Guest WiFi/User_Network unrestricted outbound; partial controls in Server_Network; DMZ mostly compliant. |
| **Wi‑Fi Security** | Partial | WPA2‑PSK with VLAN isolation but no client isolation, weak auth, no egress filtering. |

---

## 3. Remediation Plan (Prioritised)

| Priority | Action | Owner | Target Date |
|----------|--------|-------|-------------|
| **P1** | Implement deny‑by‑default ACL/NSG rules between User_Network and Server_Network; limit to required application ports. Restrict RDP/SMB to MFA‑protected admin jump hosts. | Network Security Lead | +30 days |
| **P1** | Enforce MFA on *all* privileged accounts, including break‑glass Admins, via Conditional Access. | IAM Manager | +14 days |
| **P1** | Disable SMBv1 client/server and enforce NTLMv2 via GPO/baseline templates; re‑scan for compliance. | Windows Platform Lead | +21 days |
| **P2** | Establish internal *Statement of Applicability* mapping ISM controls to implemented measures; assign control owners. | Compliance Manager | +60 days |
| **P2** | Expand monitoring to include Azure AD sign‑in/audit logs, network/firewall/proxy/DNS, application/cloud workload events; define detections with alert rules and retention ≥ 12 months. | SOC Manager | +90 days |
| **P2** | Remove direct DMZ→Server_Network DB access; implement application gateways or API layers. | Network Architect | +60 days |
| **P3** | Apply egress filtering with URL categorisation & application controls for User_Network and Guest_WiFi; implement whitelisting for Server_Network update traffic. | Network Security Lead | +90 days |
| **P3** | Upgrade Guest_WiFi to WPA3‑Enterprise, enable client isolation, and apply egress controls. | Wireless Infrastructure Lead | +120 days |
| **P3** | Document operational risk management/governance processes for control monitoring, change management, and incident response. | Risk & Governance Lead | +120 days |
| **P3** | Review and update ancillary policies/standards on a scheduled basis; formally record version control and review cycle. | Policy Owner | +120 days |
| **P4** | Develop remediation planning template/process aligned to IRAP outputs; integrate into audit follow‑up. | Compliance Manager | +150 days |
| **P4** | Draft supplementary procedures for ISM physical, personnel, and supply‑chain controls where PSPF does not cover. | Security Governance Officer | +150 days |

**Legend:**  
P1 – Critical security gap, immediate regulatory/ISM compliance risk  
P2 – High priority, material risk or auditability gap  
P3 – Medium priority, enhances maturity and resilience  
P4 – Lower priority, addresses completeness and long‑term governance