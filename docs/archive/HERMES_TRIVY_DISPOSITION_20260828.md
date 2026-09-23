# Hermes v2026.8.27 Trivy disposition

Date: 2026-08-28 UTC

## Decision

**Production remains blocked.** This record accounts for every HIGH/CRITICAL target-package row from the final
v2026.8.27 VM certification. Per operator direction on 2026-08-28, retain the current image unchanged and do not
rebuild it. No HIGH/CRITICAL finding is accepted for production until the required time-limited risk acceptance is
completed, and no provider credential or production cutover is authorized by this record.

- Fixed-version rows are dispositioned as **FIX RECOMMENDED / ACCEPTANCE REQUIRED**: the listed package fix is
  recommended, but the operator has directed that the current image remain unchanged. Each such row therefore
  remains open until a time-limited exception is approved.
- Rows without a fixed version are dispositioned as **BLOCK**: keep production blocked; do not convert the finding
  into a time-limited risk acceptance without an explicitly named owner, compensating controls, expiry, and approval.
- Exact duplicate rows share the same disposition rule, but all 402 scanner rows are listed below.

### Risk acceptance record

- Decision: retain the current v2026.8.27 image digest; do not rebuild.
- Risk owner: **not supplied**.
- Approval: **not supplied**.
- Expiry (UTC): **not supplied**.
- Compensating controls to confirm: rootless container, read-only rootfs, no published ports, NoNewPrivileges,
  five effective capabilities (0xcb), 4 GiB service memory limit, 200% CPU limit, 512 task limit, manual
  approvals, denied cron/single-query/private-URL/lazy-install behavior, and short-lived provider credential.

Until the owner, approval, and expiry are recorded, the operator direction is treated as an unapproved exception
request rather than a production go decision.

## Evidence

- Image: `docker.io/nousresearch/hermes-agent@sha256:e0df6adebddf29b91112aefc999d4aaf6846c9eb544faca5672a16a13590ff79`
- Trivy image: `docker.io/aquasec/trivy:0.74.0`
- Report: `/home/cloudops/.local/state/hermes-e2e-vm/run-20260828T034056Z/06-trivy.json`
- Report SHA-256: `0c186e917df0c7d31c7af6cac04209febece64637f693ccd70d3942a9ff1ed4b`
- Summary: `/home/cloudops/.local/state/hermes-e2e-vm/run-20260828T034056Z/06-trivy-summary.txt`
- Summary SHA-256: `268486e10268cefb884b6e8a9fc39153354a275af1d8f381d7435a7813ba7ac7`
- Counts: 402 rows total; 20 CRITICAL; 382 HIGH; 202 unique vulnerability IDs; 400 unique
  vulnerability/package/version combinations.

Trivy documents that OS-package findings use the operating system vendor's advisory source and that an empty
fixed-version field means a distribution patch has not been provided. See the
[Trivy vulnerability-scanner guidance](https://github.com/aquasecurity/trivy/blob/main/docs/guide/scanner/vulnerability.md)
and its [finding-status documentation](https://github.com/aquasecurity/trivy/blob/main/docs/guide/configuration/filtering.md).
The local JSON report remains the source of record for the exact package versions, statuses, and row accounting.

## Required remediation

1. Keep the current image unchanged as directed; do not rebuild during this gate.
2. Keep all BLOCK rows blocked until the distribution or upstream component provides a safe update or a named
   approver records a time-limited exception with owner, compensating controls, and expiry.
3. If the exception is approved, retain this scan as its evidence, record the expiry, and do not suppress findings
   with `--ignore-unfixed` as a substitute for a disposition.

## Exhaustive row inventory

| Finding | Severity | Package | Installed | Fixed | Trivy status | Disposition |
|---|---|---|---|---|---|---|
| CVE-2026-53612 | HIGH | bsdutils | 1:2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | bsdutils | 1:2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | bsdutils | 1:2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | bsdutils | 1:2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-12064 | HIGH | curl | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8286 | HIGH | curl | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8458 | HIGH | curl | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8927 | HIGH | curl | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-33747 | CRITICAL | docker-cli | 26.1.5+dfsg1-9+b13 | 26.1.5+dfsg1-9+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-33748 | HIGH | docker-cli | 26.1.5+dfsg1-9+b13 | 26.1.5+dfsg1-9+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-33997 | HIGH | docker-cli | 26.1.5+dfsg1-9+b13 | 26.1.5+dfsg1-9+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-34040 | HIGH | docker-cli | 26.1.5+dfsg1-9+b13 | 26.1.5+dfsg1-9+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-41567 | HIGH | docker-cli | 26.1.5+dfsg1-9+b13 | 26.1.5+dfsg1-9+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-42306 | HIGH | docker-cli | 26.1.5+dfsg1-9+b13 | 26.1.5+dfsg1-9+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-58049 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | ffmpeg | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-41992 | HIGH | gzip | 1.13-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-54369 | HIGH | libacl1 | 2.3.2-2+b1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-56208 | HIGH | libaom3 | 3.12.1-1 | 3.12.1-1+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-56209 | HIGH | libaom3 | 3.12.1-1 | 3.12.1-1+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-56210 | HIGH | libaom3 | 3.12.1-1 | 3.12.1-1+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-56211 | HIGH | libaom3 | 3.12.1-1 | 3.12.1-1+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-58049 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libavcodec61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-58049 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libavdevice61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-58049 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libavfilter10 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-58049 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libavformat61 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-58049 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libavutil59 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-53612 | HIGH | libblkid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | libblkid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | libblkid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | libblkid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-4878 | HIGH | libcap2 | 1:2.75-10+b8 | 1:2.75-10+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-16554 | HIGH | libcjson1 | 1.7.18-3.1+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-29036 | HIGH | libcjson1 | 1.7.18-3.1+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-67215 | HIGH | libcjson1 | 1.7.18-3.1+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-67216 | HIGH | libcjson1 | 1.7.18-3.1+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-34980 | HIGH | libcups2t64 | 2.4.10-3+deb13u2 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-12064 | HIGH | libcurl3t64-gnutls | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8286 | HIGH | libcurl3t64-gnutls | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8458 | HIGH | libcurl3t64-gnutls | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8927 | HIGH | libcurl3t64-gnutls | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-12064 | HIGH | libcurl4t64 | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8286 | HIGH | libcurl4t64 | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8458 | HIGH | libcurl4t64 | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-8927 | HIGH | libcurl4t64 | 8.14.1-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-66046 | HIGH | libexpat1 | 2.8.2-1~deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-66046 | HIGH | libexpat1-dev | 2.8.2-1~deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58016 | CRITICAL | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58010 | HIGH | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58011 | HIGH | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58012 | HIGH | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58013 | HIGH | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58014 | HIGH | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-58015 | HIGH | libglib2.0-0t64 | 2.84.4-3~deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53612 | HIGH | liblastlog2-2 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | liblastlog2-2 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | liblastlog2-2 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | liblastlog2-2 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-34873 | CRITICAL | libmbedcrypto16 | 3.6.5-0.1~deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-34875 | CRITICAL | libmbedcrypto16 | 3.6.5-0.1~deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-25835 | HIGH | libmbedcrypto16 | 3.6.5-0.1~deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-34872 | HIGH | libmbedcrypto16 | 3.6.5-0.1~deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53612 | HIGH | libmount1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | libmount1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | libmount1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | libmount1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2025-69720 | HIGH | libncursesw6 | 6.5+20250216-2 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-13221 | CRITICAL | libperl5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42496 | CRITICAL | libperl5.40 | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-8376 | CRITICAL | libperl5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42497 | HIGH | libperl5.40 | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-48962 | HIGH | libperl5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57432 | HIGH | libperl5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57433 | HIGH | libperl5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-9538 | HIGH | libperl5.40 | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-58049 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libpostproc58 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | libpython3.13 | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | libpython3.13 | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | libpython3.13 | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | libpython3.13-dev | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | libpython3.13-dev | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | libpython3.13-dev | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | libpython3.13-minimal | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | libpython3.13-minimal | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | libpython3.13-minimal | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | libpython3.13-stdlib | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | libpython3.13-stdlib | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | libpython3.13-stdlib | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53612 | HIGH | libsmartcols1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | libsmartcols1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | libsmartcols1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | libsmartcols1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-37555 | HIGH | libsndfile1 | 1.2.2-2+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11822 | HIGH | libsqlite3-0 | 3.46.1-7+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11824 | HIGH | libsqlite3-0 | 3.46.1-7+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-0966 | HIGH | libssh-4 | 0.11.2-1+deb13u1 | 0.11.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-15370 | HIGH | libssh-4 | 0.11.2-1+deb13u1 | 0.11.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-3731 | HIGH | libssh-4 | 0.11.2-1+deb13u1 | 0.11.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-59847 | HIGH | libssh-4 | 0.11.2-1+deb13u1 | 0.11.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-59849 | HIGH | libssh-4 | 0.11.2-1+deb13u1 | 0.11.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-59850 | HIGH | libssh-4 | 0.11.2-1+deb13u1 | 0.11.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-58050 | HIGH | libssh2-1t64 | 1.11.1-1+deb13u1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-14456 | HIGH | libssl3t64 | 3.5.6-1~deb13u2 | 3.5.7-1~deb13u2 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-58049 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libswresample5 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-58049 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64830 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64831 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64832 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64833 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64834 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-64835 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66036 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66039 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66040 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-66041 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70628 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-70632 | HIGH | libswscale8 | 7:7.1.5-0+deb13u1 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-36849 | HIGH | libtiff6 | 4.7.0-3+deb13u3 | — | will_not_fix | BLOCK: no time-limited acceptance |
| CVE-2026-52490 | HIGH | libtiff6 | 4.7.0-3+deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-69720 | HIGH | libtinfo6 | 6.5+20250216-2 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53612 | HIGH | libuuid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | libuuid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | libuuid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | libuuid1 | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-6653 | CRITICAL | libxml2 | 2.12.7+dfsg+really2.9.14-2.1+deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-43185 | CRITICAL | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2013-7445 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2019-19449 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2019-19814 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2021-3847 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2021-3864 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2024-21803 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2024-58015 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-22104 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-38137 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-38187 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-38204 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-38206 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-38421 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-38636 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-39859 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-39862 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-39958 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-40025 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-68174 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-68735 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-23102 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-23208 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-23327 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-31493 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-31536 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-31568 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-43198 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-43263 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-46130 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-46181 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-46279 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-52991 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53000 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53010 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53089 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53091 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53109 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53118 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53277 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53330 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-63879 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-64017 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-64283 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-64562 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-64563 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-64564 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-64565 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68099 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68123 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68136 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68140 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68143 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68144 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68145 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68159 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68160 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68166 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68199 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68200 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68201 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68202 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68236 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68264 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68290 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68294 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68335 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68376 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68409 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-68426 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-68432 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-68470 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-68480 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-72042 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-72098 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-72130 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-72137 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.101-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-72463 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-74268 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-74269 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-74446 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74476 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74480 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74488 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74502 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74503 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74509 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74510 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74516 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74518 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74520 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-74556 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74569 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74574 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74580 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74581 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74582 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74583 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74586 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74588 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74597 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74611 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-74615 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74616 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74630 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74641 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-74662 | HIGH | linux-libc-dev | 6.12.100-1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-74669 | HIGH | linux-libc-dev | 6.12.100-1 | 6.12.105-1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53612 | HIGH | login | 1:4.16.0-2+really2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | login | 1:4.16.0-2+really2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | login | 1:4.16.0-2+really2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | login | 1:4.16.0-2+really2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53612 | HIGH | mount | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | mount | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | mount | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | mount | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2025-69720 | HIGH | ncurses-base | 6.5+20250216-2 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2025-69720 | HIGH | ncurses-bin | 6.5+20250216-2 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-60002 | CRITICAL | openssh-client | 1:10.0p1-7+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-59999 | HIGH | openssh-client | 1:10.0p1-7+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-60000 | HIGH | openssh-client | 1:10.0p1-7+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-14456 | HIGH | openssl | 3.5.6-1~deb13u2 | 3.5.7-1~deb13u2 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-14456 | HIGH | openssl-provider-legacy | 3.5.6-1~deb13u2 | 3.5.7-1~deb13u2 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-13221 | CRITICAL | perl | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42496 | CRITICAL | perl | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-8376 | CRITICAL | perl | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42497 | HIGH | perl | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-48962 | HIGH | perl | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57432 | HIGH | perl | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57433 | HIGH | perl | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-9538 | HIGH | perl | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-13221 | CRITICAL | perl-base | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42496 | CRITICAL | perl-base | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-8376 | CRITICAL | perl-base | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42497 | HIGH | perl-base | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-48962 | HIGH | perl-base | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57432 | HIGH | perl-base | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57433 | HIGH | perl-base | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-9538 | HIGH | perl-base | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-13221 | CRITICAL | perl-modules-5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42496 | CRITICAL | perl-modules-5.40 | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-8376 | CRITICAL | perl-modules-5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-42497 | HIGH | perl-modules-5.40 | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-48962 | HIGH | perl-modules-5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57432 | HIGH | perl-modules-5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-57433 | HIGH | perl-modules-5.40 | 5.40.1-6 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-9538 | HIGH | perl-modules-5.40 | 5.40.1-6 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-23949 | HIGH | python3-setuptools-whl | 78.1.1-0.1 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | python3.13 | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | python3.13 | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | python3.13 | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | python3.13-dev | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | python3.13-dev | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | python3.13-dev | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | python3.13-minimal | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | python3.13-minimal | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | python3.13-minimal | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-11940 | HIGH | python3.13-venv | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-15308 | HIGH | python3.13-venv | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-7210 | HIGH | python3.13-venv | 3.13.5-2+deb13u4 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-53612 | HIGH | util-linux | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53613 | HIGH | util-linux | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53614 | HIGH | util-linux | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-53615 | HIGH | util-linux | 2.41-5 | 2.41.5-0+deb13u1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2023-5574 | HIGH | xserver-common | 2:21.1.16-1.3+deb13u3 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-55999 | HIGH | xserver-common | 2:21.1.16-1.3+deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-56000 | HIGH | xserver-common | 2:21.1.16-1.3+deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2023-5574 | HIGH | xvfb | 2:21.1.16-1.3+deb13u3 | — | fix_deferred | BLOCK: no time-limited acceptance |
| CVE-2026-55999 | HIGH | xvfb | 2:21.1.16-1.3+deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-56000 | HIGH | xvfb | 2:21.1.16-1.3+deb13u3 | — | affected | BLOCK: no time-limited acceptance |
| CVE-2026-13149 | HIGH | brace-expansion | 5.0.6 | 5.0.7, 1.1.16, 2.1.2 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-14257 | HIGH | brace-expansion | 5.0.6 | 5.0.8, 3.0.3, 2.1.3, 1.1.17 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-69152 | HIGH | brace-expansion | 5.0.6 | 1.1.18, 2.1.4, 3.0.6, 5.0.9 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-69192 | HIGH | ip-address | 10.2.0 | 10.3.1 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-59873 | CRITICAL | tar | 7.5.16 | 7.5.19 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-59874 | HIGH | tar | 7.5.16 | 7.5.18 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-73566 | HIGH | tar | 7.5.16 | 7.5.21 | fixed | FIX: rebuild image at or above fixed version |
| CVE-2026-12151 | HIGH | undici | 6.26.0 | 6.27.0, 7.28.0, 8.5.0 | fixed | FIX: rebuild image at or above fixed version |
| GHSA-4w2j-m93h-cj5j | HIGH | quinn-proto | 0.11.14 | 0.11.15 | fixed | FIX: rebuild image at or above fixed version |
| GHSA-82j2-j2ch-gfr8 | HIGH | rustls-webpki | 0.103.10 | 0.103.13, 0.104.0-alpha.7 | fixed | FIX: rebuild image at or above fixed version |
| GHSA-4w2j-m93h-cj5j | HIGH | quinn-proto | 0.11.14 | 0.11.15 | fixed | FIX: rebuild image at or above fixed version |
| GHSA-82j2-j2ch-gfr8 | HIGH | rustls-webpki | 0.103.10 | 0.103.13, 0.104.0-alpha.7 | fixed | FIX: rebuild image at or above fixed version |
