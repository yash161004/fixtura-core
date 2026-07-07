# Phase 1 Notes

## Deviations & Simplifications

1. **Table-Agnostic DB Permissions (v1 simplification)**:
   As stated in the instructions, the `CapabilityToken` for database access specifies global `read` and `write` booleans instead of per-table scopes. This is an explicit v1 simplification to reduce complexity in the permission engine while ensuring the architectural patterns (validation, checking, execution) are correctly laid down.

2. **HTTP Redirection Handling**:
   The HTTP tool explicitly rejects private/loopback/link-local ranges (SSRF protection). It uses `allow_redirects=False` to disable automatic redirect-following. This ensures that any redirects must be handled manually by the agent through sequential calls, preventing bypass of the domain or IP validation on subsequent hops.

3. **HTTP IP Resolution & SNI**:
   The HTTP tool resolves domains to IPs natively using Python's `socket.gethostbyname` to check against private/loopback IP address ranges prior to sending the HTTP request via `requests`. While standard `requests.request` will re-resolve the DNS internally (which is a theoretical DNS rebinding vector), doing the IP check before request submission fulfills the v1 Addendum requirement for explicit SSRF protection without requiring an external proxy or a custom DNS resolver adapter.

4. **Sandbox Path Validation**:
   The filesystem tool relies on `Path.resolve()` to fully evaluate paths, stripping out any `../` or symlinks before comparing it to the resolved sandbox root directory using `relative_to`. Any path not mathematically inside the sandbox root will trigger a sandbox violation.
