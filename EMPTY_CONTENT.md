# Mitigation Plan: Empty Model Responses

## Objectives
- Detect when an adapter returns an empty string (after trimming whitespace).
- Retry the request once (configurable in the future) to guard against transient provider quirks.
- If the retry also yields empty output, record the match as a failed turn and allow the tournament controller to continue.

## Proposed Steps
1. **Survey Current Behaviour**
   - Audit each adapter's `send` implementation to confirm where empty content is surfaced. Many already raise `AdapterUnavailable`; others return an empty string. Document the behaviour so our mitigation covers all cases.

2. **Normalise Empty Content Signalling**
   - Introduce a shared helper (e.g., `ensure_non_empty_reply(text: str) -> str`) inside `saber.utils.hooks` or a new module that raises a dedicated exception like `AdapterEmptyResponse` when `text.strip()` is falsy.
   - Call this helper immediately after `run_postprocess` in each adapter to guarantee consistent handling regardless of provider quirks.

3. **Retry Hook Integration**
   - Update the retry mechanism (`retry_send` in `saber.application.match_service`) to treat `AdapterEmptyResponse` as a retryable error, mirroring current handling for `AdapterUnavailable` and `AdapterRateLimit`.
   - Configure it to attempt one additional retry (total of two attempts). Make the retry count configurable via tournament runtime settings if we need more flexibility later.

4. **Terminal Failure Handling**
   - When retries are exhausted, return a structured failure payload so the match result marks the turn as unsuccessful without aborting the entire tournament. This likely means bubbling an `AdapterEmptyResponse` up so the tournament controller can log the issue and continue with the next scheduled match.

5. **Telemetry & Logging**
   - Emit a warning-level log entry the first time the empty-response retry path triggers, including adapter id and model name for diagnostics. On permanent failure, log an error with the same metadata and note that the run will be marked as failed.

6. **Testing**
   - Add unit tests for the helper to ensure it raises on empty strings and passes through valid text.
   - Add integration tests around the dummy adapter (forcing an empty response) to verify the retry logic kicks in and, after two empty replies, marks the attempt as failed while allowing the tournament loop to proceed.

7. **Documentation**
   - Update the README troubleshooting section to mention the automatic retry for empty responses and how operators can adjust retry counts if/when that becomes configurable.

## Open Questions
- Should the retry count be configurable per model via `runtime`? For this iteration we can hardcode a single retry and revisit configurability once we gather operational feedback.
- Do we need to persist the failure reason in match artifacts for offline analysis? Likely yes; ensure the error code or message is recorded alongside the transcript.
