# xsync backlog — default engine for a two-pane file transfer app

Audit date: 2026-10-10. Based on the current source, [README](README.md), and
[daily-driver backlog](backlog.md). This is a separate product backlog; existing
CLI work and completion records remain in `backlog.md`.

## Target experience and scope

Open a local or SSH directory in either pane, browse independently, select files
and folders, and copy or move them to the other pane. Resolve conflicts, manage
the transfer queue, recover interrupted work, and refresh both panes without
opening a terminal. xsync should provide the normal browsing and transfer path
and expose enough information for the app to explain exactly what happened.

Initial scope: macOS/Linux, local-to-local and local-to-SSH transfers in either
direction. Same-host remote operations, remote-to-remote transfers, additional
protocols, and Windows are explicit follow-on work. Two panes do not imply
automatic bidirectional synchronization; that needs separate conflict/history
semantics.

The app owns pane rendering, selection, drag and drop, keyboard shortcuts,
connection profiles, credential storage, notifications, and queue persistence.
xsync owns filesystem operations, transfer correctness, capability negotiation,
operation control, and structured results. Stories marked **shared** require an
engine contract plus app integration.

## Foundation already available

Do not restart these as missing features; extend them for the GUI use case.

| Existing capability | Evidence | Remaining GUI gap |
|---|---|---|
| Local copy, SSH push/pull, atomic output, collision and symlink protections | `src/local.cpp`, `src/remote.cpp`, `src/destination.cpp`; T-01–T-15 | Explicit job semantics, conflict decisions, and observable outcomes |
| Local and remote metadata listings, including nonrecursive listings | `src/listing.h`, `src/listing.cpp`; E-05 | Public structured browsing interface, cancellation, and incremental delivery guarantees |
| Selected-file transfers, relative paths, NUL-delimited file lists, filters | `src/selection.cpp`; E-08/E-09 | Literal path identities and explicit source-to-destination mappings |
| Verified-prefix resume and large-file delta transfer | `src/delta.cpp`; E-01/E-04 | Pause/recovery lifecycle and private partial-file management |
| Itemized output and internal structured file events | `src/output.h`, `src/output.cpp`; E-02/E-03 | Versioned live events for a pipe consumer; current non-TTY file output is sorted and flushed at the end |
| Signal cancellation, remote cleanup, error summaries, bandwidth limits and idle timeouts | `src/main.cpp`, `src/transport.cpp`, `src/rate_limit.cpp`; E-06/E-07/E-13 | Per-job commands, typed errors, runtime controls, and GUI authentication |
| Metadata preservation, sparse files, hard links, APFS clones | E-10/E-11/E-12; README compatibility notes | Capability reporting and understandable per-item limitations |
| Remote helper discovery/install, protocol 4/3 compatibility, rsync fallback | `src/install.cpp`, `src/fallback.cpp`; R-02–R-09 | App-managed probing, deployment, and predictable fallback behavior |

The current build exposes an executable, not a supported embeddable library
(`CMakeLists.txt`). Engine options, statistics, stop state, and output sinks are
process globals (`src/common.h`, `src/output.h`, `src/progress.h`). Remote-to-remote
transfers are explicitly rejected in `src/main.cpp`. Internal structured wire
events are not yet a public GUI API.

## Priority and status

All stories below remain **open** unless explicitly marked done. They describe missing public capabilities or
acceptance work beyond existing CLI behavior; they do not claim that the
underlying copy primitive is absent. P0 blocks a reliable GUI integration, P1
completes the everyday two-pane workflow, and P2 expands reach or improves scale.
Acceptance criteria are proposed targets, not measured results.

### Implementation progress — 2026-10-11

The contract prototype is implemented as `xs --app` for local/SSH copying and
browsing with headless authentication; see
[schema 1](docs/app-protocol.md), [the reference client](tools/app_client.py),
and [local](tests/app_test.py) / [SSH acceptance coverage](tests/app_ssh_test.py).
G-01–G-08 are done for the engine/reference-client contract, backed by the
macOS/Linux and real-SSH acceptance cases below. Visual pane, prompt and queue
integration remains app-owned. G-09 actions and G-10 safe moves are also done;
G-11 pause/resume and private recovery is also done for that contract;
G-12–G-18 remain open for the complete P1 workflow.

G-11 now has a tested private local/SSH recovery foundation: opt-in retained regular
files, explicit verified-prefix resume and revision-bound inspection/cleanup.
Confirmed local/SSH pause checkpoints, directory/symlink receipts, saved
interactive decisions, scoped policies and keep-both mappings are implemented
and pass the acceptance checks below. Persistent queue/reconciliation and the
remaining P1 workflow requirements are still open.

| Story | Implemented in the prototype | Still required for acceptance |
|---|---|---|
| G-01 **done** | Schema negotiation, request/job IDs, monotonic events, bounded NDJSON, raw byte paths, exact decimal integers, local/SSH copy/cancel and browse reference client | Further item/error contracts belong to G-04/G-05 |
| G-02 **done** | Early app-mode entry bypasses configs/environment options and all fallback paths; explicit native capabilities; SSH probe and negotiated native app bridge; unsupported/old helpers and changed wire paths/options fail before writes | New operations must preserve these guarantees |
| G-03 **done** | Immediate local/SSH listings in bounded unsorted batches, stat/lstat, home/root resolution, precise attributes, symlink targets and literal byte paths; injected partial/unreadable listings; reference pane rejects stale results during independent navigation/cancellation | Visual pane rendering remains app-owned |
| G-04 **done** | Live aggregate/item progress, hashing/reuse and metadata stages; stable byte identities and attempt counters; receiver checksum failure cannot become success; completion follows publication/metadata/receiver/SSH/child completion; bounded backpressure; source/staged/published/reused/wire counters are distinct | New operations must preserve these completion/progress guarantees |
| G-05 **done** | Typed native/request/browse/preflight/transport failures, source scan/read/revalidation and receiver output/metadata errors; complete observed selection/item outcomes; failure inventories retain exact paths and publication/metadata state; reference retries preserve nested destinations and client-owned SSH profiles; lost work remains unknown | New operations must preserve native attribution and outcome/retry guarantees |
| G-06 **done** | Private same-user askpass broker; typed host-key/credential prompts and replies; agent/key/passphrase/password, strict/first-use trust, jump aliases and existing connection reuse; real SSH copies and reference callback; separate authentication/prompt/operation idle deadlines; no secret argv or event logs | Visual prompt rendering and credential storage remain app-owned |
| G-07 **done** | Explicit entry/contents selections and literal mappings; local/SSH revision-bound replace/skip/keep-both/cancel prompts; file, directory, symlink and case/Unicode conflicts; scoped policies; rejected stale replies; new prompts after revision changes; exclusive name choice/publication; inventory/retry mappings; bounded decision/cancellation lifecycles | Visual decision rendering remains app-owned; roots/ancestors retain hard identity fences and existing-target syscall windows remain documented |
| G-08 **done** | One supervised job per process; acknowledged/bounded cancellation; control/event/parent/connection-loss supervision; local/remote destination locks; inode ownership checks for staging publication/cleanup; concurrent transfers preserve each other's options, counters, staged files and completion | Arbitrary external-writer races remain subject to the documented filesystem-operation windows |

App-mode copies currently require an existing real destination directory.
Advisory locks coordinate cooperating app-mode jobs; arbitrary external writers
still have a check-to-rename race window for existing replacements. File
completion means native filesystem operations finished, not power-loss durability.
P0 contract acceptance does not imply that the P1 filesystem stories or a visual
application are complete.

The G-07 acceptance pass adds `on_conflict:"ask"` and private conflict bridge 1.
Prompts bind replies to their observed native revision. Invalid, stale, duplicate
and unavailable decisions cannot mutate a target. A changed destination produces
a fresh prompt before mutation; policies apply only to the same conflict kind,
in the exact parent directory or the job. Nonempty unselected directory trees
remain protected. Existing case/Unicode aliases report their actual names;
planned aliases cannot authorize replacement of another selected object.

Keep-both chooses a component under destination name-equivalence rules and the
existing root locks. Regular files publish without replacement; directories and
links create exclusively. Creation/publication collisions ask again, including
with a retained staged file after close. Item mappings preserve stable identities
and make retries use the actual destination. Late replacement of an empty
directory cannot delete descendants, and default permissions follow the newly
confirmed destination or the source for a new file.

The reference client consumes progress while its conflict callback waits and
continues processing cancellation and decision deadlines. Replies arriving before
an SSH prompt cannot interrupt native handshaking. Cancelling an accepted remote
decision is reported as cancellation, rather than an unexplained disconnect.

Validation: the complete 73-case local API/mapping/retry/conflict pass passed on
macOS (two invalid-UTF-8 filesystem skips) and Linux (unprivileged permissions and
two case-sensitive filesystem fixtures skipped). The final 24-case conflict,
mapping and retry pass adds blocked-callback progress/cancel/deadline handling and
staged file-versus-directory replacement; macOS passed with one byte-name skip,
Linux with two case-alias skips. Focused close-boundary fixtures also passed on
both platforms after excluding Linux's filesystem-name probe from the staging
close hook. All 56 real-SSH cases passed with the Linux client; the preceding
54-case macOS suite passed with one byte-name skip. The additional early-stale
control case and all interactive SSH cases passed with both clients after the
final routing guard. All 38 CLI destination-scope/delta regressions passed.
These combined checks cover every current local and SSH acceptance case. Logs
are in `.bench/gui-conflicts-*`; production compilation and diff whitespace
checks passed.

Earlier implementation and validation records follow chronologically. Their
then-open G-07 statements are superseded by the current acceptance above.

Validation for the earlier foundation pass: `tests/app_test.py` ran 25 cases on macOS and Linux
(24 passed and one platform-specific skip on each). Linux exercised real
invalid-UTF-8 filenames; macOS exercised unprivileged permission failures.
The 58-case CLI output/list/progress/error/broken-stdout/destination-scope
regression run passed with one Linux-only fixture skipped on macOS. The
reference client was exercised for probe, listing, successful copy, and
acknowledged cancellation with atomic partial cleanup.

The SSH pass exercises first/changed/unknown host keys, encrypted key and
password challenges, rejected/stale/cancelled answers, agent authentication,
jump aliases, reuse of an independently managed master connection, old/missing
helpers, operation idle timeout, control loss and hard supervisor death. Both
the Linux engine and the native macOS engine run without a controlling TTY
against an isolated Linux SSH helper. The app-facing reference client answers
typed prompts through a callback; it never parses terminal text for control.
The earlier 18 SSH cases passed on Linux; macOS passed 17 with the isolated Linux
jump-topology case skipped. The latest capability/framing changes also passed
focused native macOS checks.

The SSH transfer pass adds an explicitly negotiated private native stream on
the same authenticated channel. Source selections stay literal; the helper
revalidates wire paths/options against the JSON request and locks its real
destination before writing. Copies use native atomic outputs and receiver
completion, preserve requested timestamps/permissions, and report cleanup as
unknown after connection loss. Acceptance covers push/pull, selective copies,
symlinks, batch skip/replace, encrypted-key/password copies, missing/symlink
destinations, old bridge refusal, overlapping copies with independent browsing,
cancel/control/event loss, hard parent death and killed SSH connections.
Full adversarial per-item acceptance, remaining item phases and interactive conflicts remain
P0 work; the release bar has not been reduced to the passing prototype.

The pane/progress/outcome pass adds deterministic listing faults, stale-pane
invalidation, published-byte accounting for local copies, observable file and
deferred-directory metadata phases, and typed source failures with explicit
retry selections. Metadata permission failures stay distinct from content
failures. Source changes/vanishing preserve existing good output. Observations
without a native errno report a null code rather than inventing one.
Latest validation: the 32-case local API suite passed on macOS and Linux
(31 passed and one platform-specific skip on each). All 32 SSH cases passed
with the Linux client/helper. The native macOS client passed the 31-case full
SSH suite with two platform-specific skips, plus the new copy-authentication
case and strengthened partial/permission/stale-pane checks in a focused run.
The source-change/vanishing tests verify both typed reasons and atomic output
preservation; failed-file retries are checked against final file contents.
The 80-case CLI output/list/progress/error/broken-stdout/destination/wire
regression run passed (one Linux-only skip on macOS); the earlier 15-case
mixed-version/frozen-v3 negotiation run also passed. The subsequent item-outcome pass below extends completion coverage; remaining
item/error and interactive conflict acceptance remained required at that stage;
subsequent G-04/G-05 audits below close those two stories.

The item-outcome pass streams stable job-relative identities, source/destination
byte mappings, native stages, staged/reused counters, retries and authoritative
success/skip/failure results. Regular file results follow publication and
requested metadata; directory results follow deferred metadata. Metadata errors
retain the fact that content was published. Source scan failures propagate to
receiver-owned directory outcomes, including over SSH. Successful jobs reject
incomplete result inventories. The reference inventory creates explicit retry
selections and keeps interrupted item outcomes unknown. The private SSH bridge
is version 2, so older bridge-1 helpers are refused before operations.
Skip policy now preserves existing files when an incoming directory conflicts
with them; SSH descendants of that skipped directory are explicitly skipped.
Validation: all 36 local API cases completed on native macOS and Linux
(35 passes and one platform-specific skip each); the added automatic-retry
case also passed on both platforms. All 35 real-SSH cases passed on Linux;
the native macOS client passed 33 with two platform-specific skips. The
80-case CLI regression suite passed with one Linux-only skip on macOS.
Tests cover complete mixed inventories, source/metadata failures, source
retries, deferred directory completion, cancellation/unknown outcomes and
file-versus-directory skip conflicts in both SSH directions. G-04/G-05
were still open at that stage for error-site and adversarial lifecycle acceptance;
G-06–G-08 remained open at that pass; the following acceptance audit closes G-06.

The destination-revision pass adds native metadata fingerprints to browse
entries, receiver checks before staging/publication and after closing staged
files, and root/ancestor identity guards. Observed changes return typed conflicts
with expected/observed revisions and preserve the current occupant. Publication
to an absent path uses atomic no-replace rename. The private SSH bridge is now
version 3; older bridges are refused before copying. Existing replacements still
have a check-to-rename window against arbitrary writers, and directory guards
compare identity rather than changing timestamps. Interactive G-07 remains open.

This pass also fixes an SSH teardown race that could report cancellation after
all items were successfully skipped: the adapter now waits until it records the
native transfer result. Validation: all 42 local API cases completed on native
macOS and Linux (41 passes and one platform-specific skip each). All 37 real-SSH
cases passed on Linux. Native macOS passed 35 with two platform-specific skips;
the revised jump-host test then passed on macOS as well, leaving only the
filesystem's invalid-UTF-8 restriction unexercised there. The 80-case CLI
regression suite passed with one Linux-only skip on macOS.

G-06 acceptance audit: real-SSH tests cover agent/key/passphrase/password,
first/changed/strict unknown host keys, rejected/stale/cancelled credentials,
unreachable hosts, separate connection/authentication/prompt/idle deadlines,
SSH config/jump aliases, and independently managed connection reuse. Tests
inspect arguments/events for secret leakage; answers use the private same-user
broker. The reference callback consumes actionable typed prompts without a TTY,
and CLI push/pull consumes this contract. These satisfy G-06's written done
criteria. Credential storage and visual prompt rendering belong to the app as
defined by the scope, not additional engine acceptance requirements.

The job-isolation pass retains app staging inodes through publication and
verifies ownership before publication or cleanup. A file, symlink or directory
replacing a registered temporary entry is preserved and cannot be published as
the copied content. Concurrent local transfers and concurrent real-SSH writers
use different options: cancelling one preserves the other's staging identity,
metadata policy, item counters and successful result. Similarly named unrelated
temporary files remain untouched. These checks address observed replacements,
with the documented check-to-operation window against arbitrary external tools.
Validation: 44 local API cases on native macOS and Linux, 43 passes and one
platform-specific skip each; all 39 real-SSH cases on Linux, plus the two added
SSH cases on native macOS. Targeted CLI error (11), destination-scope (14) and
metadata-composition (1, with local/push/pull/in-place/clone/dry-run subcases)
checks passed. The metadata fixture now recognizes and verifies the existing
native dry-run summary separately from itemized rows; engine CLI behavior did
not change.

G-08 acceptance audit: concurrent browsing and copies retain separate request
streams, options and outcomes; cancellation acknowledges the target job and
uses documented escalation bounds. Tests cover overlapping/aliased destinations,
ordinary cancellation, closed control/event pipes, hard supervisor death and
SSH disconnect, plus unrelated concurrent writers and replaced staging entries.
Remote writers are supervised on channel/parent loss. Cleanup is reported as
finished after graceful local cleanup or unknown after forced/channel loss;
interrupted item outcomes remain unknown in the reference client. These satisfy
G-08's written done criteria. G-04/G-05 were closed by subsequent audits below;
G-07 remains open.

The hashing/reuse pass exposes delta signature construction and reconstructed
output verification as item/aggregate hashing work. Receiver phase sampling
continues throughout quiet reads and metadata, then stops before terminal
acknowledgement. Local, push and pull tests distinguish staged/reused work from
publication, verify the final contents, and inject checksum-read failures that
preserve good destinations with zero published bytes and failed item outcomes.
Validation: all 46 local API cases on macOS/Linux (45 passes and one
platform-specific skip each); all 41 real-SSH cases passed on Linux, and native
macOS passed 40 with its invalid-UTF-8 filesystem case skipped. All 24 CLI delta
regressions passed, including local/push/pull edits, basis races and retries.

G-04 acceptance audit: updates arrive during native work using stable byte-safe
item identities, exact counters and unknown totals. Staged and reused work do
not imply publication; hashing, transferring, waiting and file/deferred-directory
metadata are observable. Results wait for receiver writes/checksums, requested
metadata, native worker completion, SSH exit and supervised child reap. Tests
cover failed receiver checksums, source retries, skipped jobs, metadata failures,
slow/closed consumers and interrupted inventories. Buffers and consumer stalls
are bounded; errors/results remain reliable for a draining consumer. Completion
is explicitly filesystem completion, not power-loss durability. These satisfy
G-04's written done criteria. G-05 was subsequently completed by the error/outcome audit below; G-07 remains open.

G-05 acceptance audit: native source and receiver failures retain their machine
category, operation, endpoint, side, stage, exact path/item identity and actual
errno where available. Logical source/destination revision mismatches keep a
null native code and explicit reason. Engine/protocol failures also emit typed
errors with exact engine status and nullable attribution; clients never match
human diagnostics. Source stat/readlink failures own failed child outcomes,
while unreadable/incomplete containers retain a failed container outcome.
Failed preflight reports every observed selection and skips valid siblings
without copying them. Failed removals cannot become successful symlink/directory
items. Disk-full cleanup retains the active failed item; undisclosed interrupted
work stays unknown. The reference client retains all observed outcomes and
builds explicit retries grouped by destination parent, so a nested failed file
cannot overwrite an unselected sibling at the destination root. Helpers without
`typed_transfer_errors: true` are refused before SSH copy mutation.

Validation: all 50 local API cases passed on macOS and Linux, with one
platform-specific skip each. All 45 real-SSH cases passed with the Linux client;
the native macOS client passed 44 with its invalid-UTF-8 filesystem case skipped.
The additional nested-retry acceptance case passed in both SSH directions with
both clients; two reference retry cases passed locally on both platforms.
All 35 CLI delta/error regressions passed after source revalidation changes,
and the earlier 80-case output/list/progress/error/destination/wire regression
run passed with one macOS platform skip. Coverage includes permission, disk-full,
vanished-source (also during second-attempt revalidation), content/checksum,
metadata, conflict, unsupported helper/selection, SSH authentication/host-key/
network errors, cancellation and unknown interrupted outcomes. These satisfy
G-05's written done criteria for the advertised local/SSH copy contract.
G-07 is the remaining P0 story. The following pass implements destination
mappings; interactive decisions, scoped policies and safe keep-both naming
still need implementation and acceptance.

The first G-07 pass adds optional `destination_name` byte components to entry
selections. Actual source paths remain unchanged; mapped names become the
transfer paths and item identities at the root. Files, folders and symlinks
can be copied under another literal name, and selections with the same source
basename can coexist when destination names differ. Invalid names, duplicate
destination names and mappings on contents selections fail before writes.
Preflight failures and both reference retry APIs retain the mapped name.
SSH negotiates `selection_mappings: true` before enabling a mapped copy; older
helpers are refused rather than silently copying under the source basename.

Validation: all 56 local API/mapping/retry cases passed on macOS (54 passes and
two invalid-UTF-8 filesystem skips). Linux ran all 56 with 55 passes and its
unprivileged permission fixture skipped. All 49 real-SSH cases passed with the Linux client;
native macOS passed 48 with its invalid-UTF-8 case skipped. New SSH coverage
copies mapped duplicate basenames, folders and links in both directions,
retains actual source paths, preserves unselected siblings, retries mapped I/O
failures and refuses missing/false/wrongly typed mapping capabilities before
mutation. All 38 CLI destination-scope and local/push/pull delta regressions
passed. G-07 remains open: interactive decisions, scoped apply-to-all policies,
fresh decisions after destination revisions change, and safe keep-both names
are still required. The current capability continues to advertise
`interactive_conflicts: false` and only batch replace/skip policies.

The destination-root audit closes a setup race before interactive decisions
are added: a preflight-pinned app root is checked before setup, and a later
failed stat cannot fall through to the CLI's implicit mkdir path. The engine
leaves a displaced root absent, preserves its old contents, and reports every
observed item as failed with no publication or metadata completion. A native
stat failure retains its errno instead of treating the directory as newly
created. Reference container retries succeed after the root is restored.
Validation: the 57-case local API/mapping/retry suite and 50-case real-SSH suite
passed with both clients (macOS: two local and one SSH UTF-8 skips; Linux: one
local permission-fixture skip). The subsequent late-stat regression passed
locally on macOS/Linux and in both SSH directions with each client. Missing-root
and late-stat focused cases also verify preserved siblings and exact retry
outcomes. These are destination-precondition foundations for G-07; interactive
conflicts, scoped policies and keep-both remain open.

## P0 — A reliable engine contract

### G-01 — Versioned machine interface (engine)

**Status: done — engine and reference client, macOS/Linux and real SSH.**

Expose requests, responses, and asynchronous events over a documented interface.
Start with a subprocess interface so the app can isolate jobs; an in-process
library is not a prerequisite. Define request/job IDs, schema negotiation,
capabilities, event ordering, stream framing, size limits, and shutdown behavior.

**Done when:** a small reference client can probe, list, start a copy, cancel it,
and consume its final result without parsing terminal text. Paths round-trip as
raw filesystem bytes with a separate display representation, including invalid
UTF-8 and newlines. Integer sizes/timestamps remain exact in JavaScript clients.
Unknown optional fields are tolerated; incompatible versions fail before writes.

### G-02 — Deterministic GUI execution and explicit capabilities (engine)

**Status: done — explicit native execution/capabilities, including old-peer refusal.**

Add an app mode with explicit options and no accidental personal defaults,
terminal rendering, or unannounced rsync re-exec. The current wrapper can clear
`XSYNC_CONFIG` and `XSYNC_OPTS`; formalize this behavior in the supported contract.
Report local and negotiated remote support before enabling an operation.

**Done when:** a user's config cannot introduce deletion, filters, or output
changes into a GUI request. The client learns the engine/backend, peer version,
and supported operations. Unsupported operations return typed results before
mutation. Any fallback preserves the machine contract or requires the app to
select a separately supported adapter; it never silently changes output format.

### G-03 — Structured pane browsing and path semantics (engine)

**Status: done — local/SSH contract and reference pane acceptance, including partial lists and stale navigation.**

Expose `list`, `stat`/`lstat`, home/root resolution, and symlink information for
local and SSH endpoints. Separate endpoint identity from path data and separate
literal paths from optional glob expansion. Reuse native listing machinery.

**Done when:** either pane can list immediate children with name, type, size,
precise modification time, permissions, and link target. Empty, missing,
unreadable, and partially listed directories are distinct outcomes. Listings
arrive in bounded batches, can be cancelled, and carry request IDs so late
results cannot replace a newly navigated directory. Names containing `:`, `*`,
`?`, leading `-`, spaces, and newlines remain literal selected objects.

### G-04 — Live progress and authoritative completion (engine)

**Status: done — live item/aggregate progress and receiver completion acceptance, local/real SSH.**

Publish job and item lifecycle events independently of the TTY renderer and its
truncated display names. Include connecting, scanning, hashing, transferring,
applying metadata, deleting, and waiting for the receiver. Separate logical
bytes, resumed/reused bytes, wire bytes, and receiver-completed work.

**Done when:** streamed updates reach a pipe consumer during the job, have stable
item IDs, and distinguish unknown totals from zero. No successful job completion
is emitted before receiver writes and requested metadata operations finish.
Slow consumers cannot cause unbounded memory growth; progress may coalesce but
errors and terminal results remain reliable. Define file completion separately
from power-loss durability. Related CLI stories: U-04, U-05, U-07, U-08.

### G-05 — Typed errors and complete per-item outcomes (engine)

**Status: done — typed errors, observed item outcomes and destination-preserving retries, local/real SSH.**

Keep human diagnostics, but expose error category, operation, endpoint, item ID,
path, native error code where available, and retryability. Retain per-item
outcomes beyond the current first-ten-error summary.

**Done when:** the app can distinguish authentication, host-key, network,
permission, disk-full, vanished-source, conflict, unsupported-feature, content,
and metadata failures without matching message strings. Every job has one final
status: success, partial failure, failure, or cancellation; a lost process is
reported by the client as an interrupted/unknown outcome. Failed-item selection
can drive a retry without reconstructing it from logs.

### G-06 — Headless SSH connection and authentication flow (shared)

**Status: done — engine and reference-client integration, macOS/Linux and real SSH.**

Make agent/key/passphrase/password authentication and host-key verification work
when launched from a desktop app with no controlling terminal. Define a secure
OpenSSH/askpass or equivalent integration; keep SSH config, jump-host, identity,
and connection-reuse behavior available.

**Done when:** first connection, changed host key, encrypted key, rejected
credentials, cancelled prompt, and unreachable host produce actionable app
states. Secrets never enter command-line arguments or diagnostic/event logs.
Separate connection/authentication deadlines from transfer idle timeouts; an
open prompt does not look like a hung transfer. Known-host verification remains
enabled. Extend the existing real-SSH coverage from R-01.

### G-07 — Exact selection and interactive conflict decisions (shared)

**Status: done — engine/reference client, macOS/Linux and real SSH, including revision races and scoped decisions.**

Accept explicit source selections and destination mappings with defined
copy-folder versus copy-contents behavior. Add per-conflict replace, skip,
keep-both/rename, and cancel decisions, plus scoped apply-to-all policies.
Existing `--update` and `--ignore-existing` are useful batch policies, not the
complete interactive workflow.

**Done when:** multi-selection cannot overwrite unselected siblings or trigger
mirror deletion. File/file, directory merge, file/directory, symlink, and
case/Unicode collisions return structured conflicts. Revalidate destination
identity before applying a decision; a concurrent destination change creates a
new conflict. Keep-both names are reserved safely under concurrent jobs.

### G-08 — Job isolation and controlled cancellation (engine)

**Status: done — subprocess isolation, cancellation and staging ownership acceptance, local/real SSH.**

Provide a job handle and acknowledged cancellation. Initially one subprocess
per active operation can isolate global state. Define temporary-file ownership,
overlapping-destination policy, and what happens if the app or control pipe dies.

**Done when:** concurrent listing and transfer jobs do not mix options, progress,
errors, or cancellation. Cancelling one job stops its local and remote work
within a documented bound and reports cleanup/partial retention. Conflicting
destination writes are rejected or serialized. App exit leaves no orphaned
remote writers; unrelated jobs remain unaffected. Related: Q-12.

## P1 — Complete the everyday two-pane workflow

| ID | Needed feature / owner | Done when |
|---|---|---|
| G-09 | **Done — filesystem actions** (engine): mkdir, rename, explicit delete, and metadata edits independent of a transfer | Local and SSH actions return structured per-item results. Rename defines replace/no-replace behavior; recursive delete requires an explicit scope and never follows directory symlinks. Stale pane entries are revalidated. Capabilities distinguish permanent delete from trash; unsupported trash is not presented as undoable deletion. |
| G-10 | **Done — safe move** (engine): same-filesystem rename and cross-filesystem/endpoint copy-then-remove | A source is removed only after the destination reports the required successful completion and the source identity is rechecked. Partial moves report copied, removed, and remaining items separately. Directories are removed only when safely empty; cancellation and metadata failures cannot discard the only good copy. Native `--remove-source-files` is currently unsupported/fallback-only. |
| G-11 | **Done — pause, resume, and private partials** (engine) | A pause reaches a documented safe state without relying on `SIGSTOP` of one side of an SSH session. Resume revalidates source/destination and reuses the existing verified-prefix mechanism. Incomplete data is associated with its job in a private staging location, not mistaken for a completed pane entry or allowed to replace an existing good destination. Stale partial cleanup is explicit. Native `--partial-dir` is currently unsupported. |
| G-12 | **Persistent queue and restart recovery** (shared) | The app persists endpoint/selection/options and engine recovery IDs, can reorder queued jobs, and limits active jobs independently of worker count. After app restart or disconnect, it reconciles completed, partial, and unknown work before retrying. Retry-failed and bounded reconnect/backoff do not repeat destructive actions blindly or retry cancelled jobs. Credentials stay outside queue records. |
| G-13 | **Structured comparison and transfer preview** (engine) | Dry-run emits planned copies, metadata updates, conflicts, skips, and deletions with reasons and totals. The plan distinguishes selected copy from mirror/sync and never writes. Execution revalidates stale plans; incomplete scans cannot authorize deletions. Direction is explicit, and two-way synchronization is not inferred. Extends U-09. |
| G-14 | **Responsive connections and independent browsing** (shared) | Connection reuse is supported and measured across navigation and transfer requests. Users can navigate both panes while a transfer runs; a large scan cannot monopolize browsing. Cancellation and connection failure invalidate only affected requests. Define session lifetime and reconnect behavior without requiring a persistent daemon for the first release. |
| G-15 | **Pane refresh and destination preflight** (engine) | Successful operations identify affected paths so the app can invalidate cached listings. Expose filesystem capacity, read-only state, name constraints, case behavior, and metadata support where detectable, with explicit unknown values. Space estimates account for atomic staging, retained partials, and sparse/clone uncertainty; actual write errors remain authoritative. |
| G-16 | **Resource controls across jobs** (shared) | The queue enforces global/per-endpoint concurrency and aggregate bandwidth limits; active jobs accept safe bandwidth changes. Browsing remains usable under bulk transfers. Worker counts, rate limits, and job counts have distinct meanings and observable effects. Builds on existing per-transfer `--jobs` and `--bwlimit`. |
| G-17 | **App packaging and remote helper lifecycle** (shared) | Ship and locate a pinned engine independently of the user's PATH; verify release integrity and app/engine compatibility. Probe remote support before a job. Missing/old helper states offer an explicit install/update action with structured progress and failure results, reusing `--install`; starting a transfer never silently deploys a helper. Test launch from a normal desktop environment on supported macOS/Linux targets. |
| G-18 | **GUI contract and failure acceptance suite** (engine) | A reference client exercises browse → select → copy → conflict → cancel/resume → move/delete → refresh locally and over real SSH without a TTY. Include unusual path bytes, old peers, slow/closed event readers, disk-full, source/destination races, app crash, disconnect, and simultaneous jobs. Verify final trees and per-item outcomes, and keep existing CLI regression checks passing. |

### G-09 acceptance — independent filesystem actions

Implemented in `src/app_actions.cpp`, schema-1 validation/supervision, the SSH
adapter, and `tools/app_client.py`. Both endpoints advertise action version 1;
SSH rejects missing/wrong action versions before sending a mutation. Requests
bind literal selected names to complete parent/entry revisions. Rename offers
explicit replacement and kernel no-replace; native directory replacement never
recursively removes existing children. Recursive delete requires explicit scope,
inventories/revalidates before writes, walks with NOFOLLOW and ancestor identity
checks, and reports each removed/failed descendant. Metadata edits pin regular
files/directories and report partial chmod/time failures truthfully. Changed
items emit listing invalidations. Permanent delete, unavailable trash and no undo
are separate capabilities. See `docs/app-protocol.md` for limits and syscall
race semantics.

Acceptance: `tests/app_actions_test.py` has 25 cases: 24 pass on macOS with one
filesystem-invalid-UTF8 skip, and all 25 pass on Linux. They cover stale parents,
leaves and replaced roots, literal names, empty/nonempty directory replacement,
symlink-safe recursive removal, incomplete inventory, per-child removal errors,
partial metadata application, competing mkdir, replaced metadata names,
inventory cancellation, hard-link/selected-source aliases and the reference CLI workflow. Five real SSH cases pass
against the Linux helper from the native macOS engine, including raw invalid
UTF8 names, refresh, stale leaves, replacement, strict old-helper rejection,
incomplete scans, partial metadata failure and the full reference CLI action
workflow without a TTY. Existing 52 local app cases also
pass (one host-filesystem skip) after these additions. The broader Linux app
contract and native-host SSH suites pass, as do the 38 destination-scope/delta
CLI checks. G-11–G-18 remain open.

### G-10 acceptance — safe move

Implemented in `src/app_move.cpp`, supervised schema-1 `move` requests,
`fingerprint`, native cross-directory no-replace rename, the retained SSH move
lease, and the reference CLI/`MoveInventory`. Selections and the destination
parent bind complete revisions. Inventory/overlap checks precede writes. Native
local renames report inode-preserving moves; cross-filesystem and local/SSH
moves copy before removal. A successful whole-copy outcome, actual byte/link
verification, required destination metadata and a final source revision check
are all required for cleanup. Known revision changes from earlier selected
hard-link removals are accounted for. Directories are removed only when empty,
and contents roots remain. Copy, removal, retention and unknown outcomes stay
separate, including fatal-worker recovery from the supervisor's inventory.

Local source parents/destination roots remain leased through verification and
cleanup. The SSH helper requires exact move/lease versions, owns its locks
before native I/O, retains the authenticated connection for restricted read and
selected nonrecursive-delete RPCs, and releases/finishes before frontend success.
Competing app writers cannot enter between remote publication and source removal.
Ordinary copies and CLI sessions do not use the private leased-wire extension.
Metadata unsupported by the destination, including macOS symlink modes on Linux,
retains the source. As documented for G-09, arbitrary external writers retain
syscall race windows; this is not transactional rollback or power-loss durability.

Acceptance: all 25 `tests/app_move_test.py` cases pass on native macOS and Linux,
including a real separate APFS volume on macOS and `/dev/shm` on Linux. Coverage
includes native files/directories, copy/remove, contents and directory merge,
source/destination revision guards, selected aliases, hard links, symlinks,
interactive replace/keep-both/skip/cancel, disk-full and metadata failures,
new directory children, source changes/removal errors, busy roots, frontend
crash and cancellation, retained locks, reference CLI and incomplete receipt
rejection. Ten move-specific real SSH cases pass from the native macOS engine
against the Linux helper, covering both directions, literal/mapped names,
contents/hard links, keep-both/cancel, metadata/removal/disk-full failures,
old/malformed lease capabilities, concurrent writers, helper loss and no-TTY CLI.
The complete pre-addition SSH suite passes 70/71 cases with one host-filesystem
invalid-UTF8 skip; the additional remote disk-full case also passes. The broader
Linux suite passes 161/164 cases (root-permission and two case-sensitive
filesystem skips), including all 25 moves and all 38 destination-scope/delta CLI
checks. The native macOS app/CLI regression run passes 136/139 cases with three
filesystem-invalid-UTF8 skips. G-11–G-18 remain open; next is safe pause/resume
with private retained partials.

### G-11 private local recovery foundation — in progress

`copy.options.retain_partials: true` stages regular files in a job-owned private
vault instead of publishing an interrupted fragment over a good destination.
Engine-generated recovery IDs bind literal selections, destination and copy
semantics without saving credentials or resource settings. `resume` rechecks
all recorded destination revisions before writes, rescans current sources,
hashes any retained prefix against the current source and checks source stability
before publication. Changed/corrupt prefixes are copied fresh; short/empty
sources cannot publish an old retained tail. Discarding unusable data preserves
its destination guard. Finished regular-file receipts remain bound to their
published revisions.

`recovery_state` inspects an inactive job under the destination lock. Hard-crash
state remains an observation requiring verification and reconciliation.
`cleanup_partials` requires the inspected job revision and validates its full
scope before removal; it rejects symlinks, unexpected directories and hardlinks,
uses guarded unlink plus empty-only rmdir, and preserves published destinations
and other jobs. Valid managed vaults are hidden from app pane/recursive scans;
foreign same-named directories are visible and refused. Store updates are
atomic, with filesystem-completion rather than power-loss durability.

All **28 new private recovery cases pass on macOS and Linux**, including real
interruption, changed sources, corrupt prefixes, shortened/empty files, byte
paths/mappings, changed destinations/root/data ownership, whole-inventory resume
guards, worker SIGKILL, explicit cleanup and the reference-client helpers.
Injected ENOSPC during both writing and partial trimming proves cleanup remains
bounded and preserves destination guards. The complete local app/action/move,
destination-scope, delta and CLI-resume run passes **194/197 cases on each
platform**, with three expected platform/filesystem skips per run. The four
hostile resume-wire cases pass after correcting their omitted `LIST_END` fixture;
native CLI push/pull resume also passes both signal and disconnect cases with
verified retained bytes and measured remaining wire traffic. Eight targeted
real-SSH copy/move regressions pass, including cancellation/helper loss and
no-TTY reference clients.

This was the initial local foundation, extended by the SSH bridge below.
Public safe pause acknowledgement, interactive-conflict recovery and completed directory/
symlink reconciliation are unfinished. SSH/`ask` recovery is rejected before
staging in that initial phase. G-12–G-18 remain open under the full P1 goal; the next step is a safe
pause/resume protocol with authoritative receiver-stop evidence over SSH.

### G-11 SSH private recovery bridge — in progress

Opt-in private recovery now supports native SSH pushes and pulls. The helper
must advertise exact private-recovery capabilities, and the native channel
must negotiate the dedicated private-partials bit plus verified-prefix resume.
Unsupported or malformed capabilities reject the request before any store is
created. Pull storage begins after native negotiation. The frontend announces
the recovery ID before connecting, and resumed attempts preserve that ID and
the original semantic binding. SSH bindings record host/user/port and endpoint
kinds without saving authentication files, credentials or resource settings.
Native helpers validate their binding against the negotiated role, literal
selection, destination and options before handoff.

Remote inspection and explicit revision-guarded cleanup use the authenticated
JSON channel and the same scope/ownership checks as local recovery. Receiver
metadata finalization errors enter the native completion acknowledgement;
published data cannot conceal a failed completion record. Endpoint attribution
and verified-prefix reuse metrics remain truthful in both directions.

Bulk resume no longer keeps a descriptor open per candidate during native NEED
preflight. It stores a full revision/checksum, reopens the selected prefix when
needed, then validates its revision and bytes again. A real 600-file SSH pull
under a 128-descriptor limit reproduces EMFILE on the old implementation and
passes after this change, with exact final contents and reused-byte totals.
A second race case changes a retained prefix after its snapshot hash and proves
the reopen guard rejects it while preserving the good destination.

Acceptance: **31 private-recovery cases pass on native macOS and Linux**. The
full real-SSH bridge run passes **79/80 cases** with one host-filesystem invalid
UTF-8 skip; after the descriptor change, all **nine SSH recovery cases pass**.
They cover interruption/resume in both directions, literal/mapped names,
changed destinations, corrupt local/remote prefixes, shrunken sources, stale
and hostile cleanup scopes, old/malformed capability rejection, final metadata
ENOSPC and bounded descriptor use. The earlier CLI/app regression runs remain
recorded above; the descriptor change also receives a fresh local app/action/
move, destination-scope, local delta and hostile-wire regression run, passing
**149/152 cases** with three host-filesystem invalid-UTF8 skips.

Public safe pause was unfinished at this bridge phase; the implementation below
adds authoritative cessation evidence. G-11 remains open for interactive-conflict
recovery and completed directory/symlink reconciliation. G-12–G-18 remain open
under the full P1 goal. Cancellation and inactive recovery inspection remain
separate from safe pause acknowledgement.

### G-11 confirmed local/SSH pause — in progress

Recoverable copies now accept `pause` while running. An accepted `pause_ack`
means stopping has started; a terminal `paused` result requires the frontend
worker to be reaped, the original helper parent/worker lifetime lease to be
exclusively reacquired over fresh authenticated SSH, and a receiver checkpoint
under the destination lock. The lease binds exact inode revision plus secure
job/attempt/role contents, with no PID-based remote killing. Missing, replaced,
stale and busy lease observations cannot confirm a pause. Pause uses TERM and
bounded escalation, without SIGSTOP in production.

Checkpointing revalidates the whole recorded destination inventory, private
data ownership and original semantic binding before atomically recording paused
state. Metadata/disk-full failures report an unconfirmed pause. Cancellation,
frontend loss or signals override pending pause; ordinary copies, moves and old
pause peers decline it without stopping the transfer. Resume remains explicit
and rechecks actual source/destination content and identities.

Helper lifetime receipts persist in the destination store, including new
per-attempt receipts on resume and cleaned receipts after confirmed pause.
Normal completion/cancellation leaves runtime leases available for explicit
revision-guarded `recovery_quiescence` cleanup. It refuses unknown children,
symlinks, wrong ownership/link counts and changed identities before removing
anything. Historical metadata flags remain observations, not authoritative
process-lifetime or completion evidence. The reference client supports pause
controls and construction of exact actor inspection/cleanup requests.

The stuck-worker fixture also exposed a macOS coordinator bug: a nonterminal
wait observation could enter a blocking reap. The coordinator now requires an
actual exited/killed/dumped status, preserving its escalation deadline.

Acceptance: all **44 private recovery/pause cases pass on macOS and Linux**.
The macOS aggregate run passes **214/218 cases**, with four expected filesystem/
real-SSH-fixture skips; the additional parent-only lease-holder case passes
separately. The Linux aggregate includes that case and passes **215/219 cases**,
with four expected root/filesystem/real-SSH-fixture skips. The full native-macOS
to Linux-helper SSH suite passes **83/84 cases**, with one host-filesystem
invalid-UTF8 skip. Coverage includes confirmed pause/resume in both directions,
persisted receipts/new attempts/explicit cleanup, forced reaping, parent-only and
worker-only lease holders, changed targets, ENOSPC checkpointing, hostile scopes,
missing/replaced/stale evidence, malformed peer capabilities, cancellation and
frontend loss. Existing copy/conflict/action/move/delta/hostile-wire and CLI
signal/disconnect/prefix regression cases remain green.
At this pause phase, G-11 remained open for interactive-conflict recovery and
completed directory/symlink reconciliation, including source type changes.

### G-11 directory/symlink recovery receipts — in progress

Recovery now records directory and symlink destinations as well as regular
files, including unchanged links and metadata-only paths. Resume validates the
whole recorded inventory before any new writes. Active directories bind inode,
type, permissions, ownership and flags while allowing child work to change
timestamps/size/link counts. Finalization and confirmed pause freeze full
revisions, so later directory timestamp or permission edits cannot be adopted
as the previous job's work. Raw crashes retain guarded active observations;
destination-mutation/receipt-publication gaps remain unknown work for G-12.

Source type changes revalidate the old destination, remove only an obsolete
owned private prefix, and replace its receipt with the new node's observation.
All regular-file/symlink/empty-directory transitions are supported; replacing
nonempty directories still fails without removing their children. Older
regular-file receipts remain resumable. The current private vault is reserved,
so a foreign source directory or explicit mapping with that name cannot modify
its marker or data.

SSH requires exact `recovery_entries: "1"` capability support before private
staging, in addition to the existing recovery bridge. Helpers that only support
regular-file receipts, or advertise malformed capability values, fail explicitly
before receiving the transfer request. Native negotiation and ordinary CLI
behavior remain unchanged.

Acceptance: all **56 private recovery/pause cases pass on macOS and Linux**.
The final macOS app/recovery run passes **107/108 cases**, with one expected
filesystem invalid-UTF8 skip; all **16 real-SSH recovery/pause cases pass** after
the final vault guard. Broader macOS/Linux runs pass **225/229 cases**, with four
expected filesystem/root/real-SSH-fixture skips, and the full SSH run passes
**86/87 cases**, with one host-filesystem invalid-UTF8 skip. The final focused
runs recheck the affected recovery paths after the reserved-vault guard.
Coverage includes nested pause/reuse and hard-kill recovery, completed and active
directory edits, changed symlinks, all safe source type transitions, nonempty
directory preservation, legacy receipts, old/malformed helper rejection,
private-vault collisions, disk-full metadata handling and bounded descriptors.

At this directory-receipt phase, G-11 remained open for interactive-conflict recovery. The next work was to persist
validated decisions and original-to-resolved destination mappings, including
keep-both and skip, before enabling `ask` recovery. The complete G-12–G-18 scope
remains active.

### G-11 acceptance — interactive recovery

Private local and SSH `ask` copies now persist validated per-source decisions,
original-to-actual destination mappings, and bounded job/directory policies
before acknowledging an applied decision or writing its destination. Resume
validates the entire receipt/choice inventory and restores renamed parents
before descendant work. Completed keep-both outputs reuse the same destination
and verified bytes; skip choices preserve their targets. An unanswered conflict
gets a fresh prompt token after resume. New selection collisions and unsafe
source type changes require another decision, while edited recorded destinations
fail before any new writes.

Opaque private data names let a fresh revision-bound publication-time decision
rebind pending bytes to a keep-both target. Duplicate pending-data references,
out-of-root choices and failed choice-metadata writes cannot authorize mutation.
The `conflict_replayed` event and recovery inspection expose saved choices and
policies without persisting prompt tokens or credentials. Private interactive
SSH transfers require exact `recovery_conflicts: "1"` capability support; old or
malformed peers fail before transfer requests/staging.

Final acceptance runs pass **243/247 cases on macOS**, **242/247 cases on Linux**,
and **92/93 real-SSH cases** with the native macOS frontend and Linux helper.
The skips are expected filesystem/root/real-SSH-fixture exclusions. All 72 local
private recovery/pause cases pass on macOS; Linux skips the case-alias fixture.
The suites include publication-time revision changes, disk-full metadata,
saved scoped decisions in both SSH directions, unapproved paused prompts,
literal byte mappings, changed completed targets, malformed metadata, bounded
descriptors and existing CLI/app/action/move/delta regressions. Logs:
`.bench/gui-choice-acceptance-{local,linux,ssh}.log`; build and whitespace checks
pass. G-11 is done for the engine/reference-client contract.

Individual metadata files are replaced atomically; mapping/receipt/choice updates
are not a multi-file transaction. A crash in that gap remains unknown work for
G-12 reconciliation and cannot authorize blind retry. G-12–G-18 remain open.

### G-12 persistent copy queue journal — in progress

`tools/app_queue.py` now supplies a reference `PersistentQueue` and an
`execute_next` worker using the schema-1 client. The bounded private journal
holds literal endpoint/selection/options, SSH profile references, recovery IDs,
item mappings/outcomes and authoritative results. It rejects connection objects,
credentials, arbitrary saved fields and destructive operations. One manager
holds an exclusive lifetime lock. A claim is synced/replaced before engine
launch; failed writes prevent admission, and an uncertain post-replace directory
sync blocks dispatch until reopen/reconciliation.

Waiting copies can be reordered or cancelled, and the independent active-job
limit is enforced across concurrent worker callers. Completed/cancelled jobs
stay terminal across restart. Unfinished attempts become `needs_reconciliation`,
retaining known outcomes and marking pending items unknown. Recovery inspections
are observations, including a store claiming `completed`; they cannot invent a
missing authoritative result. An authoritative paused private copy resumes only
after an explicit request, with the same recovery ID and restored keep-both
mapping. The worker saves lifecycle events before notifying the app and reaps
its engine on callback/stream failure. Prompt traffic is not journalled.

Acceptance: all **17 queue boundary/integration cases pass on macOS and Linux**.
The additional real-SSH queue case passes both push and pull, covering private
pause, manager restart, keep-both resume, prefix reuse, old destination
preservation and runtime-only SSH profiles. Tests cover a hard manager exit
after claim, stale attempts, corrupt journals, one-manager admission, ENOSPC
and directory-sync failures, cancellation and durable results. Logs:
`.bench/gui-queue-journal-{local,linux,ssh}.log`. Production engine code is
unchanged from the complete G-11 acceptance runs above.

At this first journal phase, G-12 remained open for full source/destination/helper reconciliation of unknown
work, retry-failed and bounded reconnect/backoff, as well as app integration.
The reference queue currently accepts copies only and has no background
scheduler. G-16 endpoint/global resource policy and the rest of G-13–G-18 remain
open; this foundation does not complete the full P1 goal.

### G-12 guarded restart reconciliation — in progress

`verify_recovery` now validates an inspected private inventory against the
original copy binding without modifying destinations or recovery metadata.
Inspection exposes an inventory token over sorted file names/full revisions,
so in-place metadata edits cannot evade stale-directory checks. Verification
guards recorded destinations, source selection scope, policies/choices and
private data ownership, rejects duplicate/orphan data and unknown publication
gaps, and rechecks the inventory before its authoritative result. Published,
pending and prepared record counts describe observations; even a completed
store cannot retroactively prove a missing operation result. Source scanning
and candidate-byte verification remain mandatory during resume.

The queue's `reconcile_job` performs inspection, fresh authenticated helper
lease checks, and guarded verification before marking unknown work
`recoverable`. A cleaned header marker requires the matching authoritative
helper-close proof saved by the queue; missing/stale evidence is never proof.
Recovered work stays out of dispatch until an explicit resume request. Changed
destinations or malformed/unknown private work remain blocked. Private SSH
receiver verification requires exact capability/operation support before the
request; missing bridges and old/malformed helpers fail explicitly.

Pause/cancel intent is saved before sending a control, and accepted acknowledgements
are recorded by attempt. Losing the final result cannot turn cancellation into
retry, even when the remaining data validates. Read-only reconciliation has
bounded backoff for typed busy destination/actor locks and network failures;
authentication, stale/changed guards, protocol failures and user cancellation
do not qualify under a broad retryable flag. Clients are reaped between attempts.

Validation: the broad app/queue/CLI pass runs **281 cases** on each platform:
**277 pass on macOS** and **276 pass on Linux**, with four/five expected
filesystem/root/real-SSH-fixture skips. All **79 private-recovery cases** pass
on macOS; Linux skips its case-alias fixture. The final **28 queue cases pass
on both platforms**, including the additional malformed ready/cancel-intent
case and final actor-revision checks. The 96-case real-SSH pass exposed three
fixture failures in the new capability test (an extra browse endpoint in a
copy-shaped request); the corrected capability test and both queue-recovery
cases pass in the final three-case SSH rerun. The other 92 cases passed with
one expected host invalid-UTF8 skip. Together these runs exercise every current
SSH case, including both directions of unknown-work reconciliation and
keep-both resume, and missing/malformed capabilities/bridges before requests.

Coverage includes read-only metadata/content preservation, stale in-place edits,
orphan/unknown data, changed targets and bindings, source changes after
verification, lost completed results, exact helper proof matching, saved close
proofs, durable cancel intent and bounded read-only backoff. Logs:
`.bench/gui-reconcile-acceptance-{local,linux,ssh}.log`,
`.bench/gui-reconcile-final-queue-{local,linux}.log` and
`.bench/gui-reconcile-final-ssh.log`. Production compilation and whitespace
checks pass. The final focused runs cover the stricter bridge/cancel-intent/
actor-revision guards added after the broad runs.

G-12 remains open for publication-gap reconciliation, selective directory
retry-failed, failed-only private-prefix reuse and automatic queue reconnect/backoff
policy, plus the remaining app integration. G-13–G-18
retain their full scope. This phase does not complete the full P1 goal.

### G-12 — Durable explicit failed-leaf retries

The reference queue now provides `retry_failed(job_id, item_ids=None)` for
reported failed files/symlinks with authoritative failed/partial-failure outcomes.
It checks byte source paths against the original selections, scopes actual
destination mappings to the original endpoint, groups nested leaves by their
mapped parent, and preserves renamed names and external profile references.
Only failed items qualify; unknown, cancelled, skipped and completed items stay
outside retries, and saved cancellation intent rejects the operation. The
reference inventory helpers also exclude cancelled items/operations, including
their unknown-item opt-in path.

Retry admission saves every child and its original attempt/item lineage in one
durable journal update. Duplicate admission is rejected after manager restart;
failed children can be retried through their own outcomes, while cancelling a
waiting child cannot be bypassed by retrying its original parent again. Original
outcomes remain intact. `replace` becomes `ask` for a fresh revision-bound
decision against a present target. Fresh subset copies have independent private
recovery IDs and source reads; original stores remain available for guarded
inspection/cleanup. Their old receipts can become stale after subset publication
and then cannot authorize a whole-job resume.

Directory failures reject default retry selection rather than silently omitting
them or broadening the retry into completed children. Callers may explicitly
select supported failed leaves while the directory remains unresolved. Selective
directory retries, missing mapping/preflight cases and failed-only prefix reuse
remain part of the open G-12 acceptance work. G-13–G-18 remain open at full scope.

Validation: the current app/mapping/retry/queue acceptance pass runs **94 cases**
on each platform: **92 pass on macOS** with two expected fixture skips and
**93 pass on Linux** with one expected fixture skip. All **35 queue cases** and
all **three retry-helper cases** pass on both platforms. The mapped real-SSH
retry case passes for both push and pull, retaining destination names, external
profiles and original outcomes across queue restart, with a fresh conflict
decision against present targets. Local coverage additionally proves a nested
keep-both parent survives retry while a changed completed source sibling is not
copied again; new/private recovery IDs remain separate. Journal fault injection,
forged path/endpoint mappings, duplicate admission, malformed lineage, failed
child retries, saved cancellation and directory broadening all have coverage.
Logs: `.bench/gui-retry-failed-acceptance-{local,linux}.log` and
`.bench/gui-retry-failed-ssh.log`. Python compilation and whitespace checks pass.

### G-12 — Bounded reconnect before copy submission

The engine now advertises exact string `copy_reconnect: "1"` and emits
`copy_not_submitted` only when its SSH adapter failed before queuing any operation
request bytes. Submission is marked before buffering/writing the request; a
failed or partial write cannot claim the remote copy never started. Missing item
or actor events alone remain insufficient. Before submission, no destination
copy/recovery data can have been created, though broker files and locks exist.
An announced recovery ID alone does not prove a created store.

The queue provides an opt-in durable policy via `enqueue(..., reconnect_delays=)`
or `set_reconnect` before a first claim. At most eight retries each wait at most
five seconds, with a saved budget/history/deadline. An authoritative failed
attempt must have the exact engine capability, unsubmitted-copy receipt and only
typed retryable SSH network/network-timeout errors. Authentication, host-key,
protocol and other errors, transfer/recovery activity, missing results, exhausted
budgets and pause/cancel intent cannot qualify. Pending reconnects survive
manager restart, retain their failed attempt result, release active-job slots,
participate in reorder and can be cancelled during backoff. Clock rollback
clamps and persists the remaining wait to its configured bound.

`execute_queue` yields each authoritative attempt result and waits responsively
for ready reconnects. Every attempt uses a fresh/reaped client and resolves its
runtime profile again. Fresh copies discard the allocated but never-created
recovery ID; explicitly resumed jobs preserve their existing private binding/ID.
Credentials and diagnostic/prompt text remain outside the journal. Active or
possibly submitted work still requires its separate reconciliation contract;
this phase does not automatically resume uncertain transfers.

G-12 remains open for selective directory/missing-mapping retries, failed-only
prefix reuse, publication-gap reconciliation, reconnect/resume policy after
possible submission and remaining app integration. G-13–G-18 retain full scope.

Validation: the broad app/mapping/retry/queue/private-recovery/conflict pass runs
**199 cases**: **197 pass on macOS** with two expected invalid-UTF8 filesystem
skips and **195 pass on Linux** with four expected root/case-alias fixture skips.
The final **44 queue cases pass on both platforms**, including the new commit
fault case and the stricter mutation-entry guard added after that broad run.
Coverage includes exact/missing/malformed capabilities, missing receipts/results,
mixed authentication/protocol errors, transfer activity, cancellation during
backoff, clock rollback, durable budget exhaustion, profile refresh, responsive
worker stopping and result/admission persistence boundaries. Fault injection
showed that a no-op claim after uncertain directory sync could hide the queue's
poisoned state; mutation entry points now consistently reject until reopen.

The four-case real-SSH pass succeeds in both directions: refused connection then
queue restart/reconnect, request received by a helper then abrupt disconnect
without automatic retry, private keep-both pause/restart/resume, and mapped
failed-leaf retry. The final private-resume case additionally inserts a refused
connection before successful resume: both directions retain the same recovery
ID, replay the keep-both mapping and reuse verified prefix bytes. The initial
post-submission fixture used the wrong internal operation-name assertion; it was
corrected to `_native_transfer`, and its complete four-case rerun passes.
Logs: `.bench/gui-reconnect-acceptance-{local,linux}.log`,
`.bench/gui-reconnect-final-queue-{local,linux}.log`,
`.bench/gui-reconnect-final-ssh.log` and `.bench/gui-reconnect-resume-ssh.log`.
Production compilation, Python compilation and whitespace checks pass. No claim
of complete G-12 or full P1 acceptance is made by this phase.

### G-12 — Guarded automatic disconnect recovery

Private SSH queue jobs can explicitly opt into `recover_disconnected=True` with
a bounded reconnect policy. Possible submission, lost frontend results and
manager restart first produce unknown work, preserving known item outcomes and
any authoritative network-failure result in history. Fresh inventory inspection,
authenticated helper-quiescence proofs and original-binding/destination guards
must pass before a durable resume admission. The engine then checks current
source data and retained prefixes before writes. Missing completion is never
reported as success. This continues the whole selection rather than only failed
leaves.

Each reconciliation cycle has a durable claim token and uses the shared active
limit. Stale proofs cannot authorize another cycle. Restart during inspection
or after verification discards proof; retryable read-only busy/network failures
use the same saved bounded budget as pre-submission reconnect. Known permanent
errors, changed guards, missing evidence and cancellation prevent admission.
`cancel_recovery` persists stop intent while keeping the uncertain outcome
unknown. Default policy remains manual. Missing recovery IDs still require
manual investigation; reserving an identity before launch remains open.

Validation: **209 cases** run on each platform: **207 pass on macOS** with two
invalid-UTF8 filesystem skips, and **205 pass on Linux** with four root/case-alias
fixture skips. These include **53 queue cases** for durable claim/admission,
restart, shared budget exhaustion, long job IDs, malformed journal rejection,
late proof rejection and saved cancellation. Two additional real-SSH tests cover
both directions across eight subcases: consumer loss with valid recovery,
foreign destination edits and cancellation, plus killing the transfer's SSH
transport. Valid cases resume the original private ID/mapping and reuse verified
prefix bytes; changed targets and cancelled work admit no copy.

Logs: `.bench/gui-auto-recovery-acceptance-{local,linux}.log` and
`.bench/gui-auto-recovery-final-ssh.log`. G-12 remains open for identity reservation
before the first receipt, publication gaps, selective directory/missing-mapping
retries, failed-only prefix reuse and app integration. G-13–G-18 retain full scope.

### G-12 — Recovery identity saved before copy submission

The engine advertises exact `copy_recovery_identity: "1"` and accepts a
caller-reserved top-level `recovery_id` for private copies. IDs remain 32 lowercase
hex characters, require `retain_partials: true`, and do not change the semantic
binding. A fresh copy refuses an existing job directory; only an explicit
guarded `resume` may reopen it. The native SSH header already carries this ID,
so its existing recovery capability negotiation remains in force.

After hello and before operation submission, the reference worker saves a random
private ID in the queue journal and attaches it to the request. A failed commit
prevents submission. Older engines retain their allocated-ID/receipt behavior;
ordinary copies receive no ID. This closes the missing-ID window when a capable
engine creates destination work but the queue receives none of its initial
events. Inspection can recover actor receipts from the original private header,
then obtain fresh quiescence/inventory/destination proof before admitting resume.
Identity reservation alone never proves that a copy started or a store exists;
missing/incomplete stores remain unknown and cannot authorize a fresh copy.

Validation: the expanded app/mapping/retry/queue/private-recovery/conflict/move
pass runs **239 cases per platform**: **237 pass on macOS** with two expected
filesystem skips and **235 pass on Linux** with four expected root/case-alias
skips. This includes **56 queue cases** and **81 private-recovery cases**. New
coverage checks exact capability negotiation, durable reservation before run,
failed reservation commits, receipt loss/restart, malformed/nonprivate IDs and
collision refusal without destination/store changes. **23 CLI trust/defaults
cases** also run per platform: all pass on macOS, with two expected Linux skips.

Three real-SSH tests pass across **10 push/pull subcases**. Dropping every initial
engine receipt still recovers the saved ID, checks header actor leases, replays
the keep-both mapping and reuses verified prefix bytes. Killed transports also
recover; changed outputs and saved cancellation admit no copy. Logs:
`.bench/gui-recovery-identity-acceptance-{local,linux}.log`,
`.bench/gui-recovery-identity-cli-{local,linux}.log`,
`.bench/gui-recovery-identity-ssh.log` and
`.bench/gui-recovery-identity-guards-ssh.log`. Production build, Python compilation
and whitespace checks pass. G-12 remains open for incomplete store creation and
publication gaps, selective directory/missing-mapping retries, failed-only prefix
reuse and app integration. G-13–G-18 retain full scope.

### G-12 — Regular-file publication-gap reconciliation

The receiver now saves a `publishing` intent before renaming completed private
data. It binds the actual destination guard, staging inode's final attributes and
a full-file XXH3-128 digest. A failed intent write prevents publication; guards
are rechecked after hashing/metadata work. Fresh publication-time conflict choices
rebind the retained data and require a new intent for the actual output.

Read-only verification can resolve an intent into retained data when the private
name remains and its full revision/original destination guard pass. After rename,
the private name must be absent and the destination must match the intended
inode, type, link count, mode, ownership, flags, size, mtime and complete digest.
The unresolved-intent check allows rename's ctime change; it establishes current
identity/content/attributes rather than the absence of every external edit.
After all inventory and conflict guards pass, resume or a confirmed pause
checkpoint freezes a full destination revision, including ctime. Read-only
verification changes no record and never proves the missing overall result.
Source data is checked again before a new authoritative copy outcome.

Direct resume now also rejects unknown private files, unreferenced data, unsafe
types/ownership and extra links before normalizing receipts or writing any
destination. This matches the automatic reconciler's existing inventory guard.
Regular-file replacement, exclusive absent-name publication and empty-file
crash gaps have coverage. The intent requires an additional bounded-buffer read
of completed data; unreadable published outputs cannot pass that proof.

Validation: final combined app/mapping/retry/queue/private-recovery/conflict/
move/actions/CLI-trust/defaults runs contain **295 cases per platform**:
**292 pass on macOS**, with three invalid-UTF8 filesystem skips, and **289 pass
on Linux**, with six root/case-filesystem fixture skips. These include **89
private-recovery cases**, **56 queue cases** and **23 CLI cases**. New crash
fixtures stop the worker before or after actual publication, check read-only
verification, full revision normalization, source changes, failed intent writes,
content/attribute/inode/link changes, empty files and unknown private inventory.

The final three-test real-SSH pass covers **12 push/pull subcases**. Crashing
the frontend/receiver after publication reconciles the saved intent and resumes
after authenticated helper/inventory checks; a foreign output edit admits no
copy. Lost initial receipts, private prefix/mapping reuse and saved cancellation
also pass after the stricter admission guard. Logs:
`.bench/gui-publication-final-all-{local,linux}.log` and
`.bench/gui-publication-final-ssh.log`. Production compilation, Python compilation
and whitespace checks pass.

G-12 remains open for incomplete initial store creation, directory/symlink
creation/removal gaps, interrupted metadata-write/remapping transactions,
selective directory/missing-mapping retries, failed-only prefix reuse and app
integration. G-13–G-18 retain their full requirements; this is verified progress
within the existing P1 goal.

### G-15 — Read-only destination preflight foundation

`src/app_preflight.cpp`, the supervised `preflight` request, SSH capability
negotiation and the reference CLI now expose an existing destination directory's
capacity, read-only state, effective directory access, detectable name/case
constraints and metadata support. Exact decimal-string arithmetic preserves
values beyond JavaScript's integer range and returns null for unknown or
overflowing byte products. Query errors do not invent zero capacity or name
limits. The directory is pinned and its logical identity is checked again
before an observation is returned. No write probe or source scan is performed.
Helpers must advertise both the operation and exact `destination_preflight:
"1"` before receiving the request.

Optional caller-supplied regular-file sizes produce logical totals, the largest
concurrent atomic staging bound, retained-data coexistence and an allocation-unit
rounded data estimate. Existing destinations/partials already consume observed
available space; the estimate assumes no early reclamation and does not double
count staging and final data. Source inputs remain unverified, physical storage,
metadata overhead and quota requirements remain unknown, and filesystem
allocation uncertainty is explicit. A fitting estimate grants no copy
authorization; actual write/metadata failures remain authoritative. The contract
and reference CLI are documented in `docs/app-protocol.md`.

Acceptance: ten `tests/app_preflight_test.py` cases cover read-only observations,
exact large budgets, staging/retention accounting, strict invalid inputs,
missing/nondirectory/symlink roots, query failure, unbounded name limits,
capacity-product overflow, read-only mounts, replaced-root races and the no-TTY
CLI. All ten pass on Linux; nine pass on macOS with the Linux read-only mount
fixture skipped. Together with existing browse, filesystem-action and move
coverage, 109/112 cases pass on macOS (three platform skips) and 111/112 pass on
Linux (one root-permission skip). Two real SSH cases pass from the native macOS
engine against the Linux helper, including five absent/malformed capability or
operation subcases that submit no request. Evidence is in
`.bench/gui-preflight-regression-{local,linux}.log` and
`.bench/gui-preflight-ssh.log`. All 23 CLI trust/default cases also pass on macOS;
21/23 pass on Linux with two case-sensitive-filesystem skips, recorded in
`.bench/gui-preflight-cli-{local,linux}.log`. Production compilation, Python
compilation and whitespace checks pass.

G-15 remains open for complete copy/resume invalidation coverage, verified
source-plan budgeting and visual pane integration. G-12–G-18 retain their full
requirements within the existing P1 goal.

### G-15 — Copy/resume refresh and stale pane generations

The public supervisor now advertises `copy_invalidation: "1"`. Local copies,
SSH push/pull and private resume emit conservative destination `invalidate`
hints after each non-skipped item receipt, using its actual mapped/keep-both
path. Directory hints include descendants. Failed metadata, failed staging and
other failed item attempts do not suppress refresh or become successful item
receipts. A single final hint covers the destination tree, including attempts
with missing outcomes after a fatal worker, cancellation, pause or disconnect.
It precedes the native completion summary to preserve summary/result adjacency;
missing-summary attempts receive the hint after worker cleanup. Invalid controls
that terminate an accepted copy also preserve the scope hint. Invalid requests
rejected before supervision and read-only operations emit no copy hints.

Hints retain the original request's endpoint/profile attribution, byte paths
and logical destination spelling through ancestor aliases. They never prove
publication, completion or remote quiescence. A disconnected helper still
requires reconciliation, and a killed frontend/unread event stream cannot
guarantee delivery; applications invalidate their outstanding job scopes on
restart. Existing transfer-capable helpers require no new wire feature because
the frontend derives hints from the already negotiated receipts and job scope.

The reference `ListingView` can bind its endpoint and accept a mutation hint
from another job with that job's original endpoint. It matches SSH connection
profiles and byte-component scopes, distinguishes similarly prefixed siblings,
discards stale entries/status and rejects late navigation results until a new
listing starts. Profile edits and physical/logical aliases remain part of the
application's cache identity policy. The protocol and README document the
refresh workflow and its limits.

Acceptance: ten `tests/app_refresh_test.py` cases cover mapped files/directories/
symlinks, raw invalid UTF8 names (Linux), ancestor aliases, publication followed
by metadata failure, failed staging/skip, a worker killed after publication,
invalid-control cleanup, browse/copy/refresh, late navigation events, independent
SSH profiles and read-only/invalid-request isolation. Private recovery fixtures
also assert the single scope hint through cancellation, pause and every direct
resume. The final combined app/mapping/retry/queue/private/conflict/move/action/
preflight/refresh and CLI trust/default suites pass 310/315 on native macOS
(five platform skips) and 309/315 on Linux (six root/filesystem skips). Four real
SSH cases pass with explicit destination attribution, nested byte paths,
published metadata failures and keep-both private resume in both directions.
Final evidence is `.bench/gui-invalidation-final-all-{local,linux}.log` and
`.bench/gui-invalidation-final-ssh.log`. The prior ordering regression is fixed
and the original summary/result check passes unchanged. Native/Linux production
builds, Python compilation and whitespace checks pass.

At this phase G-15 remained open for verified source-plan budgeting and full pane integration;
G-12–G-18 retain their complete requirements in the P1 goal.

### G-13 — Read-only plans and initial stale-copy admission

`src/app_preview.cpp` composes the existing local/SSH read operations into an
explicit selected-copy or mirror preview. It inventories selected source trees
and the full destination without following symlinks, applies detectable
case/Unicode rules, and emits byte-preserving copy, directory creation,
metadata, unchanged, conflict, skip, blocked and deletion proposal rows with
reasons and exact counts. Regular files remain copy proposals even when initial
metadata matches, matching app copy behavior; source contents are not read.
Selected-copy leaves unrelated destination entries alone. Mirror is one-way
proposal-only, never deletion authorization or executable sync.

The combined inventory is bounded to 100,000 entries and depth below 256.
Post-descent and final node revision checks reject observable changes. Unsupported
source types, incomplete/unreadable scans, overflow and cancellation cannot
produce a usable guard. Known case collisions mark both selected rows and their
descendants conditional; unknown naming behavior requires native execution
checks. An unrelated unreadable destination subtree also makes this full-tree
preview incomplete. Valid private recovery vaults retain their ordinary hidden
listing treatment. Preview creates no output, probe or recovery files and emits
no copy invalidation hints.

Complete selected-copy previews provide a token binding normalized selections,
copy options, public connection selectors, observed revisions, link targets and
detectable name/metadata behavior. The reference `TransferPreview` validates
successful completion and constructs `copy.expected_preview`; the client
requires exact capability version `transfer_preview: "1"` before submission.
The supervisor repeats the inventory before copy discovery/staging/store
creation, rejecting stale or incomplete plans without copy writes. Accepted
plans emit `preview_revalidated` before ordinary native copy begins. Read-only
error/auth forwarding goes directly to the public event sink, avoiding recursive
re-entry into the active preview collector.

This also advances G-15: revalidated source stat sizes supply exact logical and
atomic-staging upper bounds under the actual jobs limit. Skips and metadata-only
rows do not count; conditional regular-file copies do. Budget inputs are verified
metadata, not verified contents. Hidden retained data is not inventoried, so its
logical total and coexisting logical total are null. Existing allocations already
consume available capacity; physical allocation, quotas and metadata costs remain
unknown/advisory, and actual write errors remain authoritative.

Acceptance: fifteen `tests/app_preview_test.py` cases cover read-only selected
and mirror proposals, deterministic tokens, stale source/destination/options,
conditional budgets, metadata restoration, case aliases/collisions, unsupported
source types, bounded depth, incomplete scans, cancellation, strict fields,
client capability checks and the headless CLI. The combined app/preview/refresh/
preflight/mapping/retry/queue/private/conflict/move/action and CLI trust/default
suites pass 325/330 on macOS (five platform skips) and 322/330 on Linux (eight
root/filesystem skips). Two real SSH cases pass: push/pull guarded copy with
changed remote source/destination rejection, and mirror deletion proposals
without mutation or an executable guard. Final evidence is
`.bench/gui-preview-final-all-{local,linux}.log` and
`.bench/gui-preview-final-ssh.log`. Native and Linux production builds, Python
compilation and whitespace checks pass.

G-13 remains open for mirror execution with safe deletion phases and binding
preview revisions throughout native publication/remote handoff. The initial
admission gate is explicitly non-atomic; changes after it still require native
guards and can produce fresh conflicts. Persistent queue plan integration,
visual preview/pane integration, retained-data budgeting where needed and
measured SSH reuse remain open under G-12/G-14/G-15. G-12–G-18 retain their full
requirements in the existing P1 goal.

### G-13 — Native local revision checks after admission

`src/app_preview_guard.cpp` retains the admitted inventory through local native
copy. Source checks cover initial planning, rescanned directories, regular-file
open, publication after metadata/private-intent work, and final directory
metadata. Each check revalidates selected source ancestors, including observable
child additions/removals and ancestor replacements. Changed source content cannot be adopted by the ordinary fresh-source
retry under an old plan. Destination expectations cover planning and interactive
replies; publication cannot adopt a changed target via a new conflict prompt.
Typed `preview_execution` errors and affected item failures use `stale_preview`.
Completed siblings remain authoritative; no transaction/rollback is claimed.

The guard accepts explicit keep-both mappings and owned destination setup
observations. Native exclusive operations check new names. After initial
directory admission, object identity, permissions, ownership and flags remain
bound while directory size, link count and times can change from child writes.
Source revisions continue excluding access time. The additional capability is
exact `preview_revision_binding: "1"`, with supported endpoint kinds currently
`["local"]`. Existing SSH guarded-copy behavior remains the initial read-only
gate plus ordinary native checks pending negotiated helper handoff.

This advances through-execution binding without completing G-13: syscall race
windows, concurrently changed directory children after native listing, SSH
handoff and guarded mirror/deletion phases still require work. G-12–G-18 remain
open with their complete requirements.

Acceptance: the 337-case combined regression suites pass 332 cases on macOS
(five skips) and 329 on Linux (eight skips); three real SSH preview/auth/copy
cases pass. Subsequent guard refinements pass the complete 26-case preview suite
on macOS and 24 cases on Linux (two filesystem skips). They cover source changes
during reads, destination edits while awaiting a decision and after staging,
symlink source replacement, source ancestor child additions, directory metadata
restoration, virtual destination roots, affected leaf attribution, owned root
permission changes, keep-both trees with/without retained data, and `/.` source
aliases. Evidence is `.bench/gui-preview-binding-all-{local,linux}.log`,
`.bench/gui-preview-binding-ssh.log` and
`.bench/gui-preview-binding-final-focused-{local,linux}.log`. Both final production
builds, Python compilation and whitespace checks pass.

## P2 — Broader reach and scale

| ID | Needed feature / owner | Done when |
|---|---|---|
| G-19 | **Remote-to-remote and same-host remote copies** (engine) | Define same-host server-side operations and cross-host relay/direct modes. Report where bytes flow, what storage a relay requires, and which endpoint authenticates each leg. Both legs support cancellation, conflicts, and truthful progress. Never assume agent forwarding. Current CLI rejects two remote endpoints. |
| G-20 | **Optional endpoint adapters** (shared) | Decide whether SFTP-only hosts, FTP(S), WebDAV, SMB, or object storage belong in the product. Each adopted adapter implements the same browsing/job contracts and advertises its actual semantics. Native xsync over SSH remains the preferred path; rsync fallback does not imply support for these protocols. |
| G-21 | **Windows host support** (engine) | Decide native Windows versus an explicitly documented WSL integration. Cover packaging, SSH, drive/UNC paths, reserved names, case behavior, permissions, long paths, and safe replace/cancel semantics before advertising Windows support. Current release targets are macOS and Linux. |
| G-22 | **Large-directory and mixed-workload budgets** (engine) | Benchmark first listing batch, navigation cancellation, event latency, peak memory, and transfer throughput for large directories and concurrent small/large-file jobs on LAN and high-latency SSH. Set release budgets from those measurements; add bounded paging/backpressure and tune connection reuse where needed. Reuse F-01, F-09, and F-13 rather than duplicating transfer benchmarks. |
| G-23 | **Remote preview/edit support** (shared) | If included in the app, support bounded reads/downloads and upload-on-save with a source revision precondition. Editing a stale downloaded file triggers a conflict; previews cannot allocate unbounded memory or hydrate/download large files without an explicit policy. |
| G-24 | **Optional embeddable library** (engine) | Only if subprocess overhead or host integration warrants it, extract per-session/per-job state, replace process exits with returned errors, and publish a versioned ABI/bindings. Multiple engine instances coexist safely in one process. Benchmark the benefit before taking on library compatibility obligations. |

## Delivery order and release bar

1. **Contract prototype:** G-01–G-03 and a minimal reference client; preserve the
   current CLI while proving browse/copy through the new interface.
2. **Usable transfer integration:** G-04–G-08, with G-18 coverage added alongside
   each contract. This establishes progress, authentication, conflicts, and cancel.
3. **Everyday file manager:** G-09–G-17 and the complete G-18 acceptance suite.
   Prioritize private partials before persistent recovery and safe completion
   acknowledgements before copy-then-remove moves.
4. **Expand from measured demand:** G-19–G-24. These are not prerequisites for the
   initial local/SSH product.

xsync is ready to be the default engine for the initial scope when all P0 and P1
acceptance criteria pass: users can browse, copy, move, rename, delete, resolve
conflicts, queue work, and recover interruptions from the app; completion and
failure are explainable per item; no normal workflow requires terminal parsing
or an undisclosed change of backend. Visual app design is outside this backlog.
