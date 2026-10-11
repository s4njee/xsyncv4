# xs subprocess interface, schema 1

`xs --app` selects the GUI subprocess contract before CLI defaults are
loaded. The versioning, deterministic execution and browsing contracts have
acceptance coverage for G-01–G-03 and headless SSH G-06 in [backlog-gui.md](../backlog-gui.md).
Live progress and completion (G-04) and job isolation (G-08) also have acceptance
coverage. Typed outcomes/retries (G-05) and interactive conflicts (G-07) are
implemented in the engine and reference client. Independent filesystem actions
(G-09) and safe moves (G-10) also have local and real SSH coverage; visual app integration remains
app-owned. See the backlog for platform acceptance evidence.
Launch one process for each browsing or transfer operation. The supported
platforms are macOS and Linux. No terminal or controlling TTY is needed.

## Framing and negotiation

Requests arrive on stdin and events leave on stdout, one UTF-8 JSON object per
line. Every frame ends with LF; newlines in JSON strings must be escaped.
Requests may be at most 1,048,576 bytes before LF, nesting is limited to 32, and
sessions accept at most 32 ordinary request IDs. Conflict replies use IDs
derived from bounded pending prompts and do not consume that ordinary ID ledger. Duplicate JSON keys, malformed UTF-8,
unpaired Unicode surrogates, duplicate IDs and truncated frames are rejected.
Unknown optional fields are ignored except in filesystem action, move, preview and destination preflight requests, which
reject unknown fields so unsupported destructive options cannot be overlooked.
Unsupported **operation, endpoint kind,
conflict policy, or schema values** are errors. Internal `_native_` operations
belong to the private engine bridge; GUI clients use the advertised public
operations. Do not use unknown fields to
request mandatory behavior: inspect capabilities and use a supported field.

The first request must be:

```json
{"id":"hello","op":"hello","schema":"1"}
```

IDs are caller-assigned, unique, 1–128 printable ASCII characters without
spaces. Conflict-response IDs follow the rule below and may be reused after
a rejected response for the same pending prompt. The `capabilities` response identifies the engine version, source
revision, native backend, supported operations, endpoints and limits. Schema
negotiation fails before any filesystem operation. There is no rsync re-exec,
remote helper deployment or CLI option passthrough.

Every outgoing event has `schema: "1"`, the corresponding request `id`, and a
strictly increasing decimal-string `seq` across the process. The active
operation's ID is also its job ID. Events for its cancellation acknowledgement
carry the cancel request ID and the target `job_id`. Request IDs allow the app
to ignore an old directory listing after navigation.

Versions, lengths, sizes, modes, timestamps, counters, native error codes and
sequences are strings, including values outside JavaScript's exact-number
range. Use `BigInt` for integer arithmetic; never convert file sizes or seconds
to `Number` first. Timestamps use signed `mtime_seconds` and nonnegative
`mtime_nanoseconds` separately. Modes contain permission bits as decimal strings.
Booleans remain JSON booleans. Unknown totals are `null`, not zero.
Entry permission modes omit file-type bits; revision modes include them.

## Read-only destination preflight

`destination_preflight: "1"` advertises the public `preflight` operation for local
and SSH endpoints. The SSH adapter requires this exact string version and the
operation in the helper's advertised operations before submitting the request.
This observation uses an existing directory; a missing path, nondirectory or
final symlink fails with a typed `destination_preflight` error. It pins the
directory and checks that its logical name still identifies the same object
before returning. Ancestor aliases retain normal path semantics.

```json
{"id":"budget","op":"preflight","endpoint":{"kind":"local","path":{"bytes_hex":"2f746d702f64657374"}},"space":{"regular_file_sizes":["9000","2000","1"],"jobs":"2","retained_logical_bytes":"700"}}
```

The request accepts only `id`, `op`, `endpoint` and optional `space`. A supplied
`space` object requires `regular_file_sizes`, an array of at most 100,000
nonnegative decimal strings bounded by signed 64-bit file size. Optional `jobs`
is a decimal string in 1–64 (default 64); `retained_logical_bytes` is a
nonnegative unsigned 64-bit decimal string (default 0). Unknown budget fields,
nonstring integers, invalid values and aggregate overflow fail validation
before endpoint activity. Omit `space` for filesystem observation alone.

A successful request emits `destination_preflight` before its terminal result.
It contains the byte-preserving `path`, `endpoint`, complete directory
`revision`, `filesystem_type`, `read_only`, `directory_access_allowed`, and:

* `capacity`: exact decimal-string `total_bytes`, `free_bytes`,
  `available_bytes` and `allocation_unit_bytes` from `fstatvfs`, with
  `native_error` on query failure. Byte-product overflow and unavailable values
  are null. Available bytes describe the current filesystem allocation view,
  without a quota guarantee.
* `names`: `max_component_bytes`, `limit_kind` (`bounded`, `unbounded` or
  `unknown`), optional `native_error`, `case_sensitive`,
  `unicode_normalization`, and `invalid_utf8_supported`. POSIX NUL and slash
  restrictions are `forbidden_bytes_hex: "002f"`; `dot_components_allowed` is
  false. Volume capabilities and known directory casefold flags are used where
  available. Unsupported observations remain null; no probe file is created.
* `metadata`: `permissions`, `root_times`, `extended_attributes`, `acls` and
  `file_flags` describe detectable volume support, otherwise null. They do not
  promise that particular source metadata can be applied by the current user.

The filesystem type is a native macOS name or decimal Linux filesystem type
code, otherwise null. Effective directory write/search access is advisory;
known read-only mounts report access false. Unknown mount/access observations
remain null. Concurrent child changes do not invalidate a read-only observation
of the same directory. The response always has `advisory: true`,
`copy_authorized: false` and `write_probe_performed: false`; it neither reserves
capacity nor authorizes execution from a stale pane or preview.

`space` is null without budget inputs. Otherwise it reports exact
`copy_logical_bytes`, `regular_files`, `jobs_bound`,
`atomic_staging_peak_logical_bytes` (sum of the largest files up to the jobs
bound), `retained_logical_bytes`, and `coexisting_data_logical_bytes` (selected
plus retained). Caller sizes are unverified: `inputs_verified` is false. Supply
the sizes of regular files intended for the copy and its actual worker bound;
this operation does not scan or compare source selections.

`new_regular_data_allocation_estimate_bytes` rounds each selected file to the
observed allocation unit and sums it, or is null when unavailable or overflowing.
`data_budget_fits_available` compares that estimate with observed available
space, otherwise is null. Atomic staging and the eventual published file count
as one new allocation in this estimate. Existing destinations and retained
partials already consume observed available space, so they are not subtracted
again (`retained_already_consumes_available: true`); no early reclamation is
assumed (`reclaim_before_publication: false`). The current app copy options use
neither sparse nor clone shortcuts (`copy_uses_sparse` and `copy_uses_clone` are
false). Filesystem compression, allocation, quotas, metadata and prefix reuse
can still change the physical requirement. `filesystem_allocation_uncertainty`
is true; `physical_requirement_bytes`, `metadata_overhead_bytes` and
`quota_remaining_bytes` are null. Even a fitting budget is advisory; actual
write and metadata errors remain authoritative.

The reference CLI accepts `preflight PATH`, repeatable `--regular-file-size`,
`--jobs` and `--retained-logical-bytes`, plus the standard SSH endpoint options.
Preview supplies verified source metadata sizes as described below. Full visual
pane integration remains part of G-13/G-15; copy/resume refresh hints are described below.

## Read-only transfer preview

`transfer_preview: "1"` advertises `preview`, with `preview_modes` containing
`selected_copy` and `mirror`. `preview_endpoint_kinds` gives supported endpoints;
`preview_execution_modes` currently contains only `selected_copy`. This is a
frontend composition of `lstat`, `list` and `preflight`; SSH helpers need the
existing read operations and exact `destination_preflight: "1"` capability.
They do not need a helper-side `preview` operation. No probe files, private
recovery stores or output directories are created by preview.

```json
{"id":"plan","op":"preview","mode":"selected_copy","sources":[{"endpoint":{"kind":"local","path":{"bytes_hex":"2f746d702f736f75726365"}},"mode":"contents"}],"destination":{"kind":"local","path":{"bytes_hex":"2f746d702f64657374"}},"options":{"on_conflict":"ask","jobs":"2"}}
```

The request accepts only `id`, `op`, `mode`, `sources`, `destination`, and
`options`. Selections accept only `endpoint`, `mode`, and `destination_name`.
Endpoint and selection semantics are those of copy; approved options are
`on_conflict`, `preserve_times`, `preserve_permissions`,
`conflict_timeout_seconds`, `jobs`, `bandwidth_bytes_per_second`, and
`retain_partials`. Mirror requires one directory `contents` selection. Direction
is explicit in the summary (`local`, `push`, or `pull`); no two-way operation is
inferred.

The engine inventories selected source trees and the entire destination tree,
without following symlinks. Advertised `preview_max_entries: "100000"` bounds
their combined entries (including roots); `preview_max_depth: "256"` rejects
entries at depth 256. Unreadable unrelated destination subtrees therefore make
the preview incomplete. Valid private recovery vaults remain hidden under the
ordinary app listing rules. Directory revisions are checked after descent and
every observed node is revalidated before completion. This is a sequence of
observations, not an atomic filesystem snapshot.

`preview_item` carries byte-preserving `path`, stable `item_id`, `source_path`
(null for destination-only entries), `destination_path`, endpoint kinds, full
source/destination revisions, `entry_type`, `logical_bytes`, `action`, `reason`,
`conditional`, and `execution_recheck_required: true`. Actions are `copy`,
`create_directory`, `metadata_update`, `unchanged`, `conflict`, `skip`, `delete`,
and `blocked`. Regular files are proposed for copying even when their initial
metadata matches, consistent with app copy's content-checking behavior; preview
does not read or compare file contents. Native copy may reuse matching delta
blocks. Equal symlink targets and directory metadata can be classified without
reading file content. Directory time restoration includes descendant changes.

Known destination case/Unicode rules match existing spelling and identify
colliding selected names. Unknown rules and rules for new directories require
execution-time checks. Conflicts remain conditional; keep-both mappings and
interactive decisions are resolved during copy. Selected-copy destination-only
entries are skips with reason `outside_selected_copy`. Mirror reports them as
`delete` proposals with reason `destination_only`; no preview authorizes deletion.

`preview_summary` reports `mode`, `direction`, `complete`, decimal-string action
counts, `source_entries`, `destination_entries`,
`regular_data_upper_bound_bytes`, `names_require_execution_recheck`, `token`,
`token_algorithm: "xxh3-128"`, `execution_supported`, and `execution_guard`.
It always reports `deletion_authorized: false`, `snapshot_atomic: false`, and
`source_content_verified: false`. Scan failure, unsupported source types,
inventory limits or cancellation yield no usable token/guard and a failing or
cancelled terminal result. Partial rows may still be displayed as proposals.
Mirror never supplies an execution guard.

A complete preview also emits `destination_preflight` with a
budget derived from revalidated regular-file stat sizes. Copy/conflict rows
contribute to the upper bound; skipped, metadata-only and symlink rows do not.
`space.inputs_verified` is true, while `space.source_content_verified` is false.
Because hidden recovery vaults are not inventoried,
`retained_data_inventory_complete` is false and `retained_logical_bytes` and
`coexisting_data_logical_bytes` are null. Existing retained allocations already
consume available capacity. Allocation, quota and metadata uncertainty remain
explicit; the verified logical estimate is advisory.

To start the corresponding copy, remove `mode`, use `op: "copy"`, assign a new
ID, and attach the exact `execution_guard` as `expected_preview`:

```json
{"version":"1","mode":"selected_copy","token":"0123456789abcdef0123456789abcdef"}
```

The shown token is illustrative. Its actual value binds normalized selections,
destination, copy options, public connection selectors, complete observed
revisions, link targets and detected name/metadata rules. Authentication file
paths (`identity_file`, `known_hosts_file`) and fluctuating free capacity are
excluded. Tokens are opaque engine/platform observations, not a portable saved
plan format or a security credential. `expected_preview` rejects unknown fields,
versions and modes, and requires a lowercase 32-character hexadecimal token.
Clients must check exact `transfer_preview: "1"` before submitting this required
behavior; older engines can ignore unknown optional copy fields.

The frontend repeats the read-only inventory before any copy discovery,
staging or recovery-store creation. A mismatch or incomplete revalidation emits
`stale_preview` and fails without starting copy. A match emits
`preview_revalidated`, then invokes normal native copy and its conflict and
publication guards.

`preview_revision_binding: "1"` and
`preview_revision_binding_endpoint_kinds: ["local"]` advertise additional native
checks for local guarded copies. The admitted source revisions and per-selection
destination expectations remain in memory until native workers finish. Source
entries are checked during planning, regular-file open and publication, after
blocking private publication-intent work, and before final directory metadata
restoration. Each check also revalidates selected source ancestors, so observable
child additions/removals and ancestor replacements cannot authorize publication
under the old inventory. A source changed during reading cannot be retried as newly observed
content under the old plan. Destination planning and conflict replies must match
the admitted revision; later rechecks cannot adopt a changed target or open a
fresh replacement prompt. Affected items fail with reason `stale_preview` and an
error at stage `preview_execution`. Already completed siblings remain completed;
the operation is not a rollback transaction.

Explicit keep-both decisions can choose new names. Their expected absence and
the descendants of renamed directories are checked by native exclusive creation
and publication. Directory timestamps, size and link count change as the job
publishes children, so subsequent directory checks retain object identity,
permissions, ownership and flags while allowing those child-mutation fields to
change. The destination root is checked before private-store creation and again
before native setup; permission changes made by setup are recorded as owned
observations. Source access time is excluded from revision equality as usual.
Entry selections use a virtual destination root without a directory item; its
identity and metadata are checked too. A stale destination ancestor also marks
the affected leaf stale, and final metadata cannot overwrite that external edit.

These checks remain subject to the documented syscall check-to-mutation windows
and do not provide an atomic tree snapshot, freeze all unrelated destination
entries, or detect every concurrent directory-child change after native listing.
SSH guarded copies currently retain the initial admission gate and ordinary
native checks: revision expectations still need a negotiated helper handoff.
Guarded mirror execution and full cross-endpoint plan binding remain open G-13
requirements. Clients can inspect the additional binding capability when they
require the stronger local behavior.

The reference CLI supports `preview` with copy's endpoint/selection flags and
`--mode selected_copy|mirror`. `TransferPreview` collects rows and the final
summary; `execution_request(new_id)` validates a successful complete selected
plan and constructs a guarded copy. Reference queue persistence of these plans,
visual pane integration and SSH connection reuse remain open.

## Independent filesystem actions

Capabilities advertise `filesystem_actions: "1"` and the public operations
`mkdir`, `rename`, `delete`, and `metadata`. These operate on an existing parent
directory, locally or over SSH. Remote helpers must advertise this exact action
version and the requested operation before the adapter sends a mutation.
`permanent_delete: true`, `trash: false`, and `undo_delete: false` distinguish
permanent removal from an unavailable trash/undo facility. There is no trash
fallback. Ordinary CLI behavior is unchanged.

Every action request contains `endpoint` (the parent), `parent_revision` (the
complete directory revision from `lstat`), and `items` (1–1,024 distinct literal
names). Each item contains `name: {"bytes_hex": "…"}` and `expected_revision`
copied from the pane's entry. Names are single components of 1–255 bytes; `/`,
NUL, `.` and `..` are rejected. The parent revision is checked before the first
action; its identity is checked throughout. Existing entries require complete
revision objects, including identity, type, mode, ownership, flags, size and
mtime/ctime seconds and nanoseconds. Absence is exactly `{"exists": false}`.
Stale preconditions produce failures without applying the stale action.

Operation-specific fields are:

| Operation | Request fields and behavior |
|---|---|
| `mkdir` | Items require absent revisions. Optional `mode` is a decimal string of permission bits, subject to the process umask; default `0777` before umask. Creates only the requested level. An existing name is never replaced. |
| `rename` | Requires explicit boolean `replace`. Each item adds `destination_name` and `destination_revision`, within the same parent. No-replace requires an absent target and uses the kernel's exclusive rename. Replacement revalidates the observed target and uses native rename semantics: directories can replace only empty directories, and type errors never trigger recursive removal. Selected sources cannot also be other selected targets, including observed inode aliases. Same-inode regular-file hard-link targets produce an explicit conflict rather than a native no-op. |
| `delete` | Requires explicit boolean `recursive`. False unlinks leaves and removes only empty directories. True first inventories the selected tree without following directory symlinks, revalidates the inventory, then removes children before their directories. An incomplete inventory authorizes no removal of that selection. Inventories are bounded to 100,000 entries and depth 256; exceeding either bound fails before removal. |
| `metadata` | Requires `mode`, `mtime`, or both. `mode` is a decimal permission string, at most `4095` (`07777`). `mtime` has signed decimal-string `seconds` and `nanoseconds` in `0`–`999999999`; access time stays unchanged. Only regular files and real directories are supported. The engine pins a descriptor with no symlink following; symlink/special-file metadata edits fail explicitly. |

For example, permanent nonrecursive removal of a selected entry is:

```json
{"id":"remove","op":"delete","endpoint":{"kind":"local","path":{"bytes_hex":"2f746d702f70616e65"}},"parent_revision":{"exists":true,"device":"1","inode":"2","links":"2","mode":"16877","uid":"501","gid":"20","flags":"0","size":"64","mtime_seconds":"1600000000","mtime_nanoseconds":"0","ctime_seconds":"1600000000","ctime_nanoseconds":"0"},"recursive":false,"items":[{"name":{"bytes_hex":"61"},"expected_revision":{"exists":true,"device":"1","inode":"3","links":"1","mode":"33188","uid":"501","gid":"20","flags":"0","size":"5","mtime_seconds":"1600000000","mtime_nanoseconds":"0","ctime_seconds":"1600000000","ctime_nanoseconds":"0"}}]}
```

These example revisions are placeholders; use actual pane observations.
The reference client's `action_request` builds a request from retained pane
entries, and `prepare_action` refreshes `lstat` and `list` before CLI actions.
It refuses to prepare actions from failed or incomplete browsing results.

Each observed outcome is an `action_result` with `operation`, stable byte-relative
`item_id`, actual `path`, optional `destination_path`, `endpoint`, `status`,
`changed`, `removed`, `metadata_complete` (boolean for metadata, otherwise null),
and `undoable: false`. Recursive deletion emits an outcome for each inventoried
entry; an inventory failure emits a failed selected-root outcome. One failing
selection does not turn successful siblings into failures. A chmod followed by
a failed time update is `partial_failure` with `changed: true` and
`metadata_complete: false`. `summary` counts `items_changed` and `items_failed`.
Typed errors preserve native errno or use null for logical `stale_entry`,
`stale_parent` and `root_unavailable` failures. These actions never automatically
retry destructive failures.

Every changed outcome emits `invalidate` with the affected `path`, `parent_path`
and optional `destination_path`. Refresh both rename names. Cancellation during
inventory leaves that selection intact; cancellation during deletion preserves
already reported removals and may leave remaining outcomes unknown. An
interrupted stream is never proof that an action did not occur: reconcile the
filesystem before retrying.

Advisory inode locks coordinate app mutations with transfers. Recursive walking
pins directories, checks ancestor identities, and never follows directory
symlinks. Metadata changes stay on the pinned object if its name is replaced;
the postcheck reports partial failure rather than claiming the new named object
was updated. As with transfer replacement, arbitrary writers still have a
check-to-syscall window for existing-name rename/unlink; the API does not promise
transactional compare-and-swap, rollback, or power-loss durability. Exclusive
mkdir/no-replace rename and empty-only directory removal retain kernel guards.

## Safe moves

`safe_move: "1"` advertises the public `move` operation. It takes the copy
`sources`, `destination`, and `options`, plus a complete
`destination_parent_revision` from `lstat` of the destination directory. Each
selected source requires `expected_revision` from `lstat`. Selection modes,
literal `destination_name`, conflict policies and resource options match copy.
Move accepts only `on_conflict`, `preserve_times`, `preserve_permissions`,
`conflict_timeout_seconds`, `jobs`, and `bandwidth_bytes_per_second`; unknown
request, selection and option fields fail validation. The reference
`prepare_move` binds current observations, and the reference CLI defaults to
preserving times and permissions. Local/local and local/SSH in both directions
are supported. Remote/remote transfer remains outside this scope.

A complete source inventory precedes mutation, bounded to 100,000 entries and
256 levels. Overlapping selections, directory aliases, destinations inside a
selected tree and destinations aliasing another selected source are rejected
before the first rename. A local same-filesystem entry can use native rename,
with kernel no-replace for an absent target and guarded explicit replacement.
Existing directories merge through copy rather than recursive replacement.
Interactive requests use the copy conflict bridge, including keep-both mappings.
Cross-filesystem moves and SSH moves use copy followed by source cleanup.

Cleanup requires successful completion of the whole copy phase. A failed or
cancelled copy grants no source-removal permission, even for items that were
published earlier. Each completed regular file or symlink is verified at both
ends using `fingerprint`, which returns the normal entry/revision plus
`fingerprint: {algorithm: "xxh3-128", hex: "<32 lowercase hex digits>",
bytes_hashed: "<decimal>"}`. It hashes regular-file bytes or the literal link
target without following symlinks. Opened/named leaf and parent identities are
rechecked; reading errors or source changes cannot produce a receipt. The source
revision must match the inventory, and the final delete must match the verified
source revision. Known ctime/link-count changes from earlier removals or renames
of selected hard links are accounted for without relaxing data, mode or mtime
checks. Required destination mode and mtime are verified too. Unrepresentable
metadata, such as macOS symlink permission bits on Linux, retains the source and
reports partial failure. Cleanup removes directories only with empty-only
`rmdir`; newly appeared/unselected children are retained. A contents move keeps
its selected root.

The move holds exclusive advisory locks on local source parents and destination
roots, with shared ancestors, throughout copy, verification and cleanup. Locks
are reused by nested action/copy operations. SSH helpers additionally require
exact `move_lease: "1"`, action version 1, fingerprint support and transfer bridge
3. Missing, old or malformed lease capabilities fail before mutation. The helper
owns its locks before starting native data I/O, then retains the same
authenticated session for restricted verification and nonrecursive selected
source-removal RPCs. Receiver sessions permit reads inside the destination;
sender sessions permit reads and removal only within the submitted selections.
RPCs use monotonic derived IDs and are bounded to one million calls. They retain
normal frame, process supervision and consumer-stall limits. An abandoned idle
lease expires after one hour; EOF, cancellation or helper loss closes it. No
persistent daemon is required. Lease release and helper exit must succeed before
the frontend reports terminal success.

The private wire extension `PF_APP_LEASE` (bit 38) and `F_APP_END` (40) delimit
native transfer completion without closing the leased channel. A sender emits
the empty end marker after receiving `F_DONE`; a receiver accepts it only after
required completion. Leased native readers never read ahead across this boundary.
Ordinary CLI and app copies mask the extension out and retain their existing
teardown behavior. Private bridge operations are engine-owned.

`move_discovered` identifies each inventoried item before mutation using stable
original byte-relative `item_id`, actual `source_path`, planned
`destination_path`, endpoint kinds and `scope_root`. `move_result` carries the
actual mapped destination, `status`, `reason`, `copied`, `renamed`, `removed`,
`remaining`, `destination_completed` and `content_published`. A native rename
reports `renamed/removed: true` and `copied: false`. A completed copy with failed
source removal reports both `copied` and `remaining`; it must not be retried as a
blind move. Unknown observations are null. The supervisor retains the inventory
outside the engine worker. If a fatal engine exit or cancellation prevents final
receipts, it emits `status: "unknown"`, nullable removal/retention state and
`reason: "move_outcome_unknown"` for unfinished items. Known copy/publication
receipts and earlier completed moves are preserved. This does not infer that an
unreported unlink or rename did not occur.

`move_summary` reports decimal-string `items_copied`, `items_removed`,
`items_remaining`, `items_unknown`, `items_renamed`, and `items_total`.
Supervisor recovery adds `recovered: true`. Counts describe observed outcomes;
unknown states never count as confirmed remaining items. Source removals and
native renames emit affected-path invalidations. `MoveInventory` retains unknown
work and checks the complete result count before accepting success. As with
filesystem actions, arbitrary external writers retain a check-to-syscall window;
these locks coordinate app jobs, not filesystem transactions or power-loss
rollback. Reconcile unknown work before retrying.

## Endpoints and paths

Endpoint identity and filesystem paths are separate. Schema 1 supports:

```json
{"kind":"local","path":{"bytes_hex":"2f746d702f736f75726365"}}
```

`bytes_hex` is an even-length hexadecimal encoding of raw filesystem bytes.
Paths must be absolute, at most 4,096 bytes, and contain no NUL. Trailing slashes
are normalized; folder semantics are specified explicitly in copy selections.
The optional incoming `display` field is ignored. Outgoing paths and names have
both `bytes_hex` and `display`; display is valid UTF-8 with replacement characters
for invalid bytes. Always use bytes for identity and requests. Newlines, colons,
spaces, `*`, `?`, and leading dashes have literal filesystem meanings. No glob,
remote-spec, shell, variable or tilde expansion runs on these paths.

Host filesystems can reject invalid UTF-8 filenames themselves; the byte codec
still round-trips such identities without corrupting them. Resolving home uses
the launching environment's `HOME`; it does not run a shell.

## Operations

After negotiation, `{"id":"probe","op":"probe"}` repeats capabilities without
starting a job. With an SSH `endpoint`, probe instead starts a supervised remote
negotiation job and ends with a result. Local probes remain session requests.
`{"id":"shutdown","op":"shutdown"}` returns a successful result and exits.
Otherwise send exactly one operation below, keep stdin open, and consume its
stream through the terminal result. The process exits after this operation.
There are no additional queued operations in a process.

| Request | Required fields | Events |
|---|---|---|
| `list` | `endpoint` | `started`, bounded `entries` batches, errors, `result` |
| `stat` | `endpoint` | `started`, `entry` for the referent, errors, `result` |
| `fingerprint` | `endpoint` for a regular file or symlink | `started`, fingerprinted `entry`, errors, `result` |
| `lstat` | `endpoint` | `started`, `entry` for the selected object, errors, `result` |
| `resolve` | `location: "home"` or `"root"` | `started`, `resolved` endpoint, `result` |
| `copy` | `sources`, `destination`, `options` | `started`, phases, progress, item updates, errors/diagnostics, summary, `result` |
| `move` | copy fields plus complete source/destination revisions | inventory, copy/conflict/progress events, move outcomes/summary, `result` |
| `cancel` | `job_id` of the active operation | `cancel_ack`, then the operation's terminal `result` |
| `pause` | `job_id` of an active recoverable copy | `pause_ack`, reconciliation events, `paused`, then a `paused` result when confirmed |

`list` returns immediate children, never recursively descends or follows a child
directory symlink. Each entry includes byte-safe name/path, type, exact size and
mtime, permission mode, device/inode and `link_target` (a byte-safe path value for
symlinks, otherwise `null`). `stat` follows the final symlink; `lstat` preserves
it, including dangling links. File contents are not read for browsing.

Each entry also includes a `revision` observation with `exists`, device/inode,
link count, full native mode, uid/gid, flags, size and precise mtime/ctime.
Integer fields are decimal strings. An absent revision is `{"exists":false}`;
an unavailable observation is `null`. Access time is excluded. This is a native
metadata fingerprint, not a content hash or a client-supplied precondition.

Batches contain at most 128 entries and are also capped by serialized size.
Order follows directory enumeration and is **not sorted**. The app may sort its
own pane. Empty directories emit no batches and succeed. Missing or unreadable
directories fail with native errors. A child that vanishes or cannot be examined
is reported as an error, and the remaining listing ends as `partial_failure`.
Directory enumeration uses an open descriptor, so renaming the directory does
not redirect reads through a newly replaced parent; listed path strings can
still become stale and must not be treated as revision preconditions.
The reference client's `ListingView` resets when navigation starts and ignores
events from older request IDs, including their late errors and final results.
It keeps delivered entries alongside errors for a partial listing. Pass the
pane's endpoint to `ListingView(request_id, endpoint)` or
`begin(request_id, endpoint)` to enable refresh routing. For a mutation's
`invalidate` event, call `invalidate(event, operation_endpoint)` with the job's
original affected endpoint. Kind/path alone cannot identify an SSH host; the
reference view matches the saved connection profile as well. Local byte paths
and SSH byte paths stay separate. An affected pane discards its entries and
status, sets `invalidated: true`, and ignores late events from that navigation.
Begin a fresh navigation and list again; completed item receipts are not
replacement listing entries. Path matching respects byte-component boundaries,
including recursive ancestor hints; a similarly prefixed sibling is unaffected.
For older action hints without `recursive`, the view conservatively treats
the affected path as a subtree. Logical aliases and edited connection profiles
require the application's cache identity policy; matching does not infer alias
equivalence or resolve a changed profile to a host.

### Copy/resume pane invalidation

`copy_invalidation: "1"` advertises destination refresh hints from the public
supervisor for local copies, SSH push/pull and private resume. These are
`invalidate` events with byte-preserving `path` and `parent_path`, destination
`endpoint` (`local` or `ssh`), boolean `recursive`, `reason`, and `item_id`.
Their public request ID binds them to the job's original destination/profile.
Each non-skipped `item_result` with a destination in the selected scope is
followed by a `transfer_item` hint for its actual mapped/keep-both path and item
ID; directory hints cover descendants. This also covers published data with
failed metadata and other failed item attempts. Skipped entries produce no
per-item hint. Refresh hints are conservative: they prove neither mutation nor
successful publication, and preserve the item/whole-job outcome separately.

One `transfer_attempt` hint covers the whole selected destination tree, with
`recursive: true` and `item_id: null`. It precedes the native completion summary;
when that summary is missing, it is emitted after the frontend worker is reaped
and before the terminal result. This includes cancellation, pause, fatal workers,
failed preflight and a disconnected helper, where individual receipts may be
missing. The fallback also applies after invalid active-job controls terminate
an already accepted copy. Invalid copy requests rejected before supervision and
read-only browsing/preflight/recovery verification emit no copy hints.
No paths or credentials from a different job are inferred or exposed.

The frontend derives these hints from its bound destination and already
negotiated item receipts; an older transfer-capable helper need not advertise a
new refresh capability. Hints cannot prove that a disconnected helper has
stopped. Keep affected results unknown and use the recovery quiescence protocol
before resuming or treating a fresh listing as a final recovered snapshot.
If the frontend/event consumer itself is killed or stops reading, receipt
delivery is not guaranteed; invalidate its outstanding destination scopes on
restart. No invalidation authorizes a destructive action from cached entries.

### Copy request

```json
{
  "id":"copy-1",
  "op":"copy",
  "sources":[
    {"endpoint":{"kind":"local","path":{"bytes_hex":"2f746d702f736f75726365"}},"mode":"contents"}
  ],
  "destination":{"kind":"local","path":{"bytes_hex":"2f746d702f64657374696e6174696f6e"}},
  "options":{
    "on_conflict":"replace",
    "preserve_times":true,
    "preserve_permissions":true,
    "jobs":"4",
    "bandwidth_bytes_per_second":"0"
  }
}
```

The destination must already exist as a real directory; a final destination
symlink is rejected. `entry` copies the selected file/link/folder under its
basename into that directory. `contents` copies a real directory's immediate
children and their descendants into the destination, and must be the only
selection. An entry selection array allows 1–1,024 selections with distinct source path
strings and distinct destination names; a filesystem root or final `.`/`..`
component must use contents mode.

An `entry` selection can specify `destination_name: {"bytes_hex":"..."}`. It
names one literal child of the destination directory, using 1–255 raw bytes.
Empty names, `.`, `..`, `/` and NUL bytes are rejected before writes. No shell or
glob expansion occurs. Without this field the source basename is used. Two
selected objects can share a basename when their destination names differ. A
mapped folder retains all child names below its new top-level name; symlink
target bytes are copied literally. `contents` cannot specify `destination_name`.
This provides an explicit mapping inside the chosen destination directory;
nested destination paths and implicit creation of another destination root are
unavailable.

For example, selections for `/source/a/file` and `/source/b/file` can specify
`destination_name` byte values for `first` and `second`. They then copy to
`/destination/first` and `/destination/second`, leaving `/destination/file`
untouched. Probe `selection_mappings: true` before offering these selections.
The SSH adapter requires this Boolean capability from the helper whenever a
selection specifies a destination name; an absent, false or wrongly typed
capability fails with `unsupported_feature` before the remote operation.

`on_conflict`, `preserve_times` and `preserve_permissions` are mandatory explicit
choices. `replace` uses native batch replacement and directory merging; `skip`
preserves existing file/link nodes, including file-versus-directory conflicts;
existing real directories still merge.
`ask` enables the interactive decisions described below. Batch replace/skip
retain their existing behavior and do not pause for input. The app must explain
the chosen policy before launching a copy.

With `destination_revision_checks:true`, the receiver observes existing targets
during planning and rechecks their native revisions before staging and before
regular-file publication, including after closing the staged output. A changed
target produces a typed conflict and preserves the observed occupant. The
selected destination root is checked again before setup; app jobs never use
the CLI fallback that creates a missing root. If the root disappears or cannot
be examined after anchoring, observed items fail without applying metadata or
publishing content. Actual stat errors retain errno; revision mismatches retain
their expected/observed snapshots. Restore or explicitly choose an existing
destination before retrying. The root and directory ancestors are checked for device/inode
and type identity; directory timestamps change during the job and are not
compared. Publishing to an observed absent path uses the kernel's atomic
no-replace rename. Unsupported no-replace operations fail rather than falling
back to overwriting a newly created file.

Existing-target replacement still has a check-to-rename window against arbitrary
external writers. These checks do not provide transactional compare-and-swap against arbitrary
external writers. Interactive replies and
keep-both publication use the protections described below.

### Interactive conflicts

Probe `interactive_conflicts:true` before offering `on_conflict:"ask"`. SSH also
requires the helper's exact `conflict_bridge:"1"`; absent, false or incorrectly
typed capabilities fail before starting the remote operation. Standard copies
continue to require transfer bridge 3 and do not negotiate the new native
control feature with an older helper.

A `conflict` event contains `conflict_id`, `revision_token`, `item_id`, literal
`path` and `source_path`, `endpoint`, `side:"destination"`,
`stage:"waiting_conflict"`, native `destination_revision`, the prior
`expected_revision` (null before initial planning), `kind`, `reason`,
`allowed_actions`, `scopes` and `timeout_seconds`. `existing_name` supplies the
actual destination component (null for an absent target), including case/Unicode
aliases of the requested name. Kinds are `file_file`,
`directory_merge`, `type_mismatch`, `symlink` and `name_collision`. The event
identifies a pending decision; it does not authorize a mutation by itself.

Reply on the original process stdin:

```json
{"id":"decision-CONFLICT_ID","op":"conflict_response","job_id":"copy","conflict_id":"CONFLICT_ID","revision_token":"TOKEN_FROM_EVENT","decision":"keep_both","scope":"item"}
```

The ID must be exactly `decision-` followed by the event's `conflict_id`.
`revision_token` must equal the opaque token from that prompt, binding the reply
to its observed native destination revision. `decision` is an offered action:
`replace`, `skip`, `keep_both` or `cancel`. A directory/directory replacement
merges selected contents. A nonempty destination directory protected by a
non-directory source does not offer replacement. Planned case/Unicode aliases
between selections also do not offer replacement. Unselected directory
children cannot be deleted by a decision.

`scope` defaults to `item`. `directory` applies that action to later conflicts
of the same kind in the exact destination parent directory; `job` applies it
throughout this job. Directory scopes do not include descendants. Policies are
job-local, bounded to 128, and are stored only after revision validation.
Different conflict kinds require their own decisions. Any observed revision
change forces a fresh prompt even when a matching policy exists.

For item-scoped keep-both, optional `destination_name:{"bytes_hex":"..."}`
chooses a literal 1–255 byte component with the same validation as selection
mappings. Otherwise the receiver picks `name (copy N)`, truncating the original
component safely to fit the byte limit and avoiding occupied names and other
selected names under destination case/Unicode rules. Root locks exclude
cooperating app writers while names are chosen and published. Regular files
publish with atomic no-replace rename; directories/symlinks create exclusively.
An external entry appearing at creation/publication triggers a fresh conflict.
No partial final-name placeholder is exposed.

`item_mapping` updates the actual `destination_path` while preserving the
original stable `item_id`. Descendant identities stay under the original
selected relative name; their destination paths follow the renamed directory.
The reference inventory consumes these mappings for retry requests.
`conflict_resolved` reports the validated decision and scope. Malformed,
wrong-token, stale, duplicate, disallowed or invalid-name replies produce
`conflict_response_rejected` without mutating the target. A revision change
while waiting rejects the old decision and emits a new prompt with a new token.
An unavailable explicit keep-both name likewise needs a new prompt.

Aggregate progress uses `waiting_conflict`. Optional
`conflict_timeout_seconds` is an exact decimal string from 1 through 3600,
default 120, independent of the transfer idle deadline. Prompt waiting pauses
operation-idle expiry, while event-consumer and stalled-writer bounds remain
active. Deadline expiry fails that item with a typed `conflict_timeout` error.
`cancel` or the ordinary job cancel command cancels the job, including its SSH
peer and owned staging files. EOF, parent death and closed event readers retain
the normal bounded supervision rules. Replaced roots/ancestors terminate safely
with a typed conflict and require choosing/restoring a destination before retry;
they cannot be rebound to another inode inside a pending job.

Optional `jobs` is a decimal string from 0 through 64 (0 selects the engine
budget). Optional bandwidth is an exact nonnegative decimal byte rate through
`INT64_MAX`; 0 is unlimited. Files are copied through native atomic staging;
clones and in-place writes are disabled. Retained partials are disabled by
default; local and SSH copies can opt into the private recovery contract below. Symlinks are copied
as links, recursion is enabled, and special files/devices are not copied.
Owner/group, ACL, xattr, creation-time and other preservation options are not
exposed by this prototype. Copy requests cannot enable mirroring/deletion, filters,
config merges, fallback, output formatting or logs through CLI defaults.

## Private recovery — G-11

The engine advertises `private_partials: "1"`, `recovery_entries: "1"` and
`recovery_conflicts: "1"`, plus
`recovery_bridge: "1"` when the native SSH extension is available, and `recovery_endpoint_kinds` containing the
supported local/SSH endpoints. A copy with
`options.retain_partials: true` stores incomplete regular files in an owned
`.xsync-app-partials/<recovery_id>/` directory under the existing destination.
This option accepts `replace`, `skip` and `ask`. Interactive private SSH copies
require exact `recovery_conflicts: "1"` peer support as well as the recovery
entry/bridge capabilities; missing or malformed support fails before sending
the transfer request or creating staging. Default copies keep
their existing cancellation cleanup behavior. Recoverable copies support the
public safe-pause contract below; cancellation remains a separate outcome.

`recovery_preparing` announces a 32-character lowercase hex ID before creating
the store. With exact local capability `copy_recovery_identity: "1"`, a private
`copy` may supply `recovery_id` at the request's top level. Save that identity
before submission to retain an inspection target if every initial receipt is
lost. Without it, the engine generates an ID. Supplying an ID requires
`retain_partials: true`; malformed IDs fail before mutation. A fresh copy refuses
any existing job directory with `recovery_job_exists` and never adopts or resumes
it. Only `resume` can reopen the original guarded binding. This uses the existing
private native SSH header; remote recovery/entry/conflict capability checks still
apply. An ID alone proves neither submission nor store creation.
`recovery_created` confirms initialization.
The vault/job directories have mode 0700, and new data/metadata files have
mode 0600. A private ownership marker distinguishes the managed vault from a
user-created directory with the same name; foreign directories remain visible
and are not adopted. App pane listings and recursive app scans hide a valid
managed vault. Ordinary CLI scans retain their normal behavior.

Staged data remains private after cancellation, disconnect, or worker failure;
it cannot replace the existing destination until the file completes. The
`partial_retained` and `partial_published` events contain `recovery_id`, source
and destination byte paths, and `bytes_retained`. Per-file metadata binds
the data inode and the destination revision observed before writing, or the
published destination revision after completion. Directory descriptors and
logical names are rechecked during staging and publication. A changed root,
replaced data inode, or edited recorded destination causes a typed failure.

To resume explicitly, send the original copy selection, destination and
semantic options with `op: "resume"`, a new request `id`, and the returned
`recovery_id`. Preserve conflict policy, time/permission choices and literal
destination-name mappings. `jobs`, bandwidth, and conflict timeout may change.
No credentials or resource settings are saved in the semantic binding. SSH
bindings include endpoint kinds and the parsed host/user/port, while excluding
identity, known-hosts, config, jump and helper paths.
Every stored regular-file, directory and symlink destination receipt is checked before the new scan
can write. The engine rescans the current source, hashes the candidate prefix
against the freshly opened source, and rechecks source stability before
publication. A changed or corrupt prefix is copied fresh; matching prefixes
are reflected in `reused_bytes`. A shortened or empty source truncates the
staged output to its current size. Candidate snapshots retain the full file
revision and prefix checksum without holding a descriptor for every file in
the directory. Reuse reopens the pinned private part or published destination,
checks its full revision and hashes the bytes again. A change between snapshot
and reuse fails without publishing over the good destination.
Restart queue policy remains part of the unfinished G-12 workflow.

Directory and symlink operations also write receipts, including unchanged links
and metadata-only paths. Records may include `entry_type` (`regular`, `directory`
or `symlink`); older regular-file records without that field remain supported.
`entry_prepared` binds the destination before mutation. `entry_owned` binds a
non-directory inode after the operation; `directory_active` binds a directory
while its children are being written. `entry_published` and `entry_checkpoint`
carry full `published_revision` observations. These states describe destination
observations, not successful source verification or completion of a whole tree;
the job and per-item results remain authoritative.

Active directory checks require the same inode, type, permissions, ownership and
flags. They permit timestamp, size and link-count changes caused by child work.
Finalization and confirmed pause freeze a full revision; subsequent resume checks
that revision before any new writes. A raw crash can leave an active directory
receipt, which requires its identity/access-attribute guard and all recorded child
guards to pass. Extra unselected children are preserved. Source type changes
revalidate the old target, discard only the recorded obsolete private prefix,
and replace its receipt with the new target's observation. Replacing a directory
with a file or link still requires an empty directory; resume never recursively
removes its children. A crash between destination mutation and receipt publication
can leave a changed/unknown receipt and requires reconciliation, not blind retry.
The current job's vault is reserved: a selection or mapping that would write
into it fails with `recovery_reserved_destination` before mutation. A foreign
source directory with the same name cannot replace its ownership marker or data.

With `on_conflict: "ask"`, a separate `conflict_choice` record binds each selected
source and original destination to its approved `replace`, `skip` or `keep_both`
decision and actual destination. Implicit copies to absent targets are recorded
as `copy`. Choices are saved before acknowledging an applied decision or writing
the destination. Records preserve byte paths and destination revisions; prompt
tokens and SSH credentials are never saved. Job/directory policies are bounded
to 128 entries and preserve the conflict kind and exact directory scope. An
inherited policy is recorded as an item decision, without expanding its scope.

Resume checks choices and destination receipts before any new writes, then
restores actual names before descending into renamed directories. It emits
`conflict_replayed` with `recovery_id`, `decision`, `item_id`, `endpoint`,
`source_path`, `original_destination_path` and `destination_path`. A new selection
collision or unsafe source type change requires a fresh decision. An unanswered
prompt has no approved choice and receives a new token on resume. Editing a
recorded destination before resume fails its guard; a scoped policy cannot
silently adopt that change. A skipped case alias may share another selected
source's destination only when that destination's owned receipt also validates.

Private data filenames are opaque identities, independent of destination names.
After a publication-time revision change, a fresh approved decision may rebind
the pending output to a new keep-both path while retaining its verified prefix.
Duplicate references to the same pending data file are rejected. Receipt,
choice and policy updates use individual atomic metadata replacements rather
than a multi-file transaction. A crash between mapping updates can leave unknown
work that fails validation and needs G-12 reconciliation; it cannot authorize
automatic publication or retry. Legacy regular-file records remain supported.

#### Regular-file publication intents — G-12

`recovery_publication: "1"` advertises regular-file publication intents. Before
renaming completed private data, the receiver atomically saves a `publishing`
record with the actual destination guard, `publication_identity` (the staging
inode's final revision) and `publication_digest` (32 lowercase hex characters
encoding XXH3-128 over the complete bytes). Saving this intent requires one
additional bounded-buffer read of the completed private file. Read errors,
cancellation, changed staging or failed metadata writes prevent publication.
Destination and staging guards are rechecked after this potentially blocking
work; a new conflict choice requires an intent for its actual output.

After a process crash, read-only verification can resolve two cases. If the
private name remains, its complete revision must still match the intent and the
original destination guard must pass; it is a retained prefix requiring fresh
source verification. If the private name has vanished, the actual destination
must be the same regular inode with exactly the intended link count, mode,
owner/group, flags, size and mtime. A stable full-file read must match the saved
digest. Missing data alone is insufficient. A replacement, extra hard link,
changed content or changed recorded attributes blocks recovery.

Rename changes ctime, so this exceptional unresolved-intent check cannot require
the staging ctime at the final name. It proves that the current inode, attributes
and bytes match the publication intent, not that no external edit ever occurred.
Read-only verification leaves records unchanged and still reports
`operation_completion_proven: false`. Resume (or a confirmed pause checkpoint)
saves the full observed post-rename revision only after the entire inventory and
conflict choices validate. Subsequent checks include ctime normally. The queue
still requires fresh helper-quiescence proofs and a new authoritative transfer
result; it cannot manufacture the lost outcome from a publication intent.

This handles regular-file rename/receipt gaps for replacement and exclusive
absent-name publication, including empty files. Legacy records without an intent
retain their original strict guards. Unreadable published files cannot pass the
digest check. Incomplete initial store creation, directory/symlink creation or
removal gaps, orphaned interrupted metadata writes and multi-record remapping
transactions remain unresolved and fail closed rather than authorizing writes.

`recovery_state` takes `endpoint` (the local or SSH destination root) and
`recovery_id`. After acquiring the destination job lock, it emits a
`recovery_state` event with `job_revision`, stored binding, state, helper lifetime
receipts in `actors`, saved `conflict_policies` (an empty array for older stores), and file
count, followed by `recovery_entry` events with exact names/revisions, available
records (including conflict choices), and `verification_required: true`. A store left `active` after a hard
worker crash is an observation requiring reconciliation. Store state alone
never proves transfer completion; require the authoritative operation result.
An active overlapping app job prevents inspection or cleanup.

### Read-only recovery verification — G-12

`recovery_verification: "1"` advertises `verify_recovery`. Submit the original
copy `sources`, `destination` and semantic `options`, plus `recovery_id`, a new
request `id`, `expected_job_revision` and `expected_inventory_token` from a fresh
`recovery_state` inspection. Inspection's `inventory_token` binds the sorted
names and full revisions of all private files, including the header and data.
It catches in-place metadata/data edits that do not change directory timestamps.
It is an observation token, not a source/content hash or completion receipt.

The engine derives the original binding from the copy request, takes its
destination lock, anchors the destination, and validates the entire store
without changing recovery metadata or destination contents. Validation covers
binding/selection scope, full observed inventory, destination guards, private
data ownership, unique pending-data references, saved choices and scoped
policies. Orphan data, pending metadata-publication gaps, unexpected private
files and malformed records fail explicitly and preserve their contents.
Destination paths cannot escape the root through dot/parent components. Active
directory guards retain their documented attribute/identity semantics; this
read-only operation does not freeze them into pause checkpoints.

After the inventory passes, `recovery_verified_entry` streams each guarded
destination record. `recovery_verified` reports the recovery ID, endpoint,
inventory token, job revision, observed store state, `records_total`,
`pending_records`, `published_records`, `prepared_records`, `choices_total` and
staged logical `bytes_retained` (file lengths, not allocated blocks or verified
matching bytes), all counts as decimal strings. Both events carry
`destination_guard_verified: true` and `source_verification_required: true`.
The aggregate explicitly carries `operation_completion_proven: false`.
Require its authoritative successful result; intermediate entries alone cannot
authorize continuation. The engine rechecks the inventory and destination
guards before emitting the aggregate. Filesystem observation/syscall windows
remain as documented for the other operations.

Verification does not compare staged/published bytes to the current source or
prove successful completion of the original selection. Resume rescans and
revalidates the source and hashes candidate prefixes before reuse/publication.
A completed store with a missing final result remains unconfirmed completed
work. For an SSH receiver, the frontend sends private `_verify_recovery` only
after negotiating exact `recovery_verification: "1"` and the corresponding
public/private operations. Old or malformed helpers fail before that request.
An SSH pull verifies its local destination store in the frontend. Checking old
helper lifetimes remains a separate `recovery_quiescence` operation; destination
verification alone does not prove that every SSH actor released its lease.

`cleanup_partials` requires the same endpoint/ID plus
`expected_job_revision` from a successful inspection. It inventories and
validates the whole private scope before removing anything. A stale directory
revision, unexpected directory/symlink, or multiply linked file rejects the
request. Cleanup removes only the selected job's regular files and then its
empty directory, emits `recovery_cleaned`, and leaves published destinations
and other jobs intact. Cleanup is explicit even after successful completion.
The reference client provides `resume_request` and `prepare_partial_cleanup`;
neither performs automatic retries or resumes destructive operations.

Metadata updates are atomic within pinned private directories. This contract
provides filesystem completion, not power-loss durability. The recovery
foundation is covered in `tests/app_partials_test.py` and the real-SSH recovery
cases in `tests/app_ssh_test.py`; G-11 remains open for interactive-conflict
recovery.

SSH recovery requires the helper's exact `private_partials: "1"`,
`recovery_entries: "1"` and `recovery_bridge: "1"` capabilities plus its public resume/inspection/cleanup
operations. The native channel separately negotiates `PF_APP_PARTIALS` (bit 39)
and the existing `PF_RESUME` before receiving data. Both helper roles validate
the private flag against their app request. Ordinary CLI and nonrecoverable app
copies mask this extension out. A missing, old or malformed capability rejects
the job before creating its destination store; local pull storage is deferred
until successful native negotiation. The frontend announces the recovery ID
before connection so a lost channel cannot hide an initialized remote store.
`recovery_entries` distinguishes helpers with file/directory/symlink receipts
from older helpers that recorded regular files only.

For a push, the helper's receiver owns the private store. For a pull, the local
receiver owns it. The native header carries the same recovery ID and sanitized
binding on resumed attempts, rather than creating a new job store. Recovery
events preserve literal paths and use the selected endpoint's attribution.
The receiver's completion acknowledgement includes errors from the final
recovery metadata update; publishing every file cannot conceal a failed update
behind a success result. Verified prefixes contribute to both item and job
reuse metrics. `recovery_state`/`cleanup_partials` use the ordinary authenticated
JSON app channel and the same destination locks and scope checks as local
recovery. After cancellation, an old helper may still be completing bounded
teardown; a busy observation is not proof of a safe pause.

### Confirmed pause

The engine advertises `safe_pause: "1"`; native SSH peers additionally need the
exact `pause_bridge: "1"` capability and its evidence operations. Send
`{"id":"pause-1","op":"pause","job_id":"copy-1"}` after
`recovery_created`/`recovery_resuming`. `pause_ack.accepted: true` means the
supervisor has begun stopping that worker. The acknowledgement alone does not
prove a pause. `accepted: false` leaves the job running and gives a reason:
`not_ready`, `unsupported_job`, `peer_pause_unavailable`, `already_stopping`, or
`already_finished`. Ordinary copies and moves cannot pause through this contract.
Old or malformed peer pause capabilities do not disable private recovery; they
disable pause and omit the lifetime extension from the native request.

The frontend sends TERM to its job group, escalates after the existing two-second
grace period, drains events and reaps its worker. Each participating helper
creates a private per-attempt lifetime lease before forking its native worker.
Both the parent and worker retain the same locked open-file description through
their native work. A `recovery_actor` event identifies its secure attempt ID,
role, byte-safe runtime path and exact lease revision. It contains no PID or
credential. The destination store persists that receipt, and resumed attempts
append a new one without changing the semantic binding.

After reaping the frontend worker, SSH pause uses a fresh authenticated JSON
request to acquire that exact lease inode exclusively. It checks private
directory ownership, regular-file ownership/link count, full revision and the
job/attempt/role contents. The exclusive acquisition proves the original helper
parent and native worker released the lease. Missing, replaced, stale or busy
evidence never proves this condition. Successful reconciliation removes only
that lease and its empty private directory; an unexpected child rejects cleanup
before unlink. Retries of busy evidence are bounded by a 30-second reconciliation
deadline. No copy, move or delete operation is retried during this check.

The receiver then takes its destination lock, validates the original binding,
all file/directory/symlink receipts and private data ownership, and atomically records a
`paused` checkpoint. It inventories the private directory scope; malformed metadata,
changed recorded destinations and checkpoint write failures reject the pause.
A confirmed checkpoint records the closed helper attempt's receipt as `cleaned`.
The `pause_checkpoint` event includes the observed job revision; `paused` includes
`receiver_quiescent: true`, `peer_quiescent: true` for SSH (null locally), and
`verification_required: true`. The terminal result has `status: "paused"`,
`code: "0"`, `cleanup: "finished"`, and the same `recovery_id`. This confirms
cessation and a private recovery checkpoint, not transfer completion. Resume is
explicit in a new process and still revalidates every source/destination guard
and any reused prefix.

If evidence or checkpointing fails, there is no `paused` event: the terminal
result is a failure with unknown cleanup and a typed error. A later explicit
cancel, frontend EOF or signal overrides a pending pause with cancellation.
Stored state remains an observation; it cannot substitute for the authoritative
paused result. Forced worker termination can produce a verified pause when the
worker has actually been reaped and every reconciliation check succeeds.

Helper runtime receipts remain available after ordinary completion or
cancellation for explicit cleanup. `recovery_quiescence` takes the selected
local/SSH endpoint with its actor path, `recovery_id`, `attempt_id`, `role`,
`expected_actor_revision`, and boolean `cleanup`. It emits `recovery_quiescent`
only after the exact lease is exclusively acquired and validated. With
`cleanup: false` it only observes; with true it removes the guarded private scope.
The reference client exposes `pause_request` and `recovery_actor_request`.
Keep authentication profiles outside saved recovery metadata; use the original
source profile for a sender receipt and destination profile for a receiver.
An inspection's historical `cleaned` receipt does not itself prove a currently
running attempt's state. Lifetime receipt inventory is bounded to 256 attempts
per recovery job; exceeding it fails before transfer writes.

The mode ignores `XSYNC_CONFIG`, `XSYNC_OPTS`, personal config files,
`XSYNC_PROGRESS`, `XSYNC_RSH`, `RSYNC_RSH` and `XSYNC_FALLBACK`. It uses the
launcher's normal filesystem credentials and umask. SSH browsing uses the
separate connection/authentication contract below. Copy endpoints can be local
or SSH in `copy_endpoint_kinds`. Copies can be local-to-local, local-to-SSH
(push), or SSH-to-local (pull). All sources must share one endpoint and SSH
selections must share one parsed connection profile. Mixed-source and
remote-to-remote copies fail before starting a job.

## SSH connections, copies and headless authentication

`probe`, `list`, `stat`, `lstat`, and `resolve` accept an SSH endpoint. The remote
helper must support schema 1 through `--app`; a CLI-only/old helper is rejected
without a transfer, installation or fallback. Paths travel as JSON bytes and
never appear in the SSH command. The helper runs its native local browsing
operation, and the local supervisor assigns public request IDs and sequences.

```json
{
  "kind":"ssh",
  "connection":{
    "host":"server-alias",
    "user":"alice",
    "port":"22",
    "helper_path":"/home/alice/.local/bin/xs",
    "identity_file":"/home/alice/.ssh/id_ed25519",
    "known_hosts_file":"/home/alice/.ssh/known_hosts",
    "host_key_policy":"ask",
    "connect_timeout_seconds":"30",
    "authentication_timeout_seconds":"60",
    "prompt_timeout_seconds":"120",
    "idle_timeout_seconds":"30"
  },
  "path":{"bytes_hex":"2f746d702f736f75726365"}
}
```

Only `host` is required in `connection`. It may be an SSH config alias or an
IPv4/IPv6 host, without embedded shell syntax. Optional `user`, `port`,
`identity_file`, `known_hosts_file`, `config_file` and `jump_host` are translated
into discrete OpenSSH arguments. File paths must be absolute and contain no
control bytes; spaces are supported. `helper_path` is an absolute executable
path, or `xs` (the default) to select an already installed PATH helper. The
helper path is shell-quoted as one executable; arbitrary remote commands and
custom `-e` shells are not accepted. Profiles contain connection details,
never passwords or passphrases.

The adapter invokes `/usr/bin/ssh`, preserves normal OpenSSH config, agent,
identity and jump-host support, and can reuse an existing configured control
master. It sets `ControlMaster=no` to avoid creating a background master owned
by a job; cancelling a job leaves an independently managed master running.
`SSH_ASKPASS_REQUIRE=force` gives authentication to the app even with no
controlling terminal. Incoming askpass/environment overrides are replaced with
a per-job private broker, in a directory with mode 0700 and a Unix socket with
mode 0600. Both ends verify the local peer UID.

Host verification is always enabled. `host_key_policy` is `strict` (the default)
or `ask`; disabling verification is not supported. First-use trust under `ask`
emits an `auth_prompt` of kind `host_key`, including OpenSSH's host identity and
key fingerprint. Changed keys remain blocked and return a `host_key` error.
Accepting first-use trust lets OpenSSH update the selected known-hosts file.

Credential challenges have kind `credential` and a `credential_kind` of
`key_passphrase`, `password`, or `interactive`. OpenSSH permission questions
can have kind `confirmation`. `prompt_id` identifies one challenge within the
job, `echo` tells the app whether the answer can be displayed, and
`timeout_seconds` describes its deadline. The app renders the prompt and sends:

```json
{"id":"answer-1","op":"auth_response","job_id":"browse-1","prompt_id":"auth-1","answer":"yes"}
```

For a credential, `answer` is the secret string, delivered only over stdin and
private IPC. Answers cannot contain NUL/CR/LF and are at most 4096 UTF-8 bytes.
They never enter command-line arguments, environment variables, diagnostic
messages or outgoing events. `auth_response_ack` confirms forwarding to the
matching prompt, without echoing the answer. A stale prompt ID produces
`auth_response_rejected`; it cannot answer a newly opened question. At most 16
challenges are accepted in a job. To cancel a prompt, omit `answer` and send
`cancelled: true`, or use the ordinary job cancellation command.

The connect deadline is enforced by OpenSSH (1–300 seconds). The authentication
deadline (1–600 seconds) is distinct from the open prompt deadline (1–3600
seconds): an unanswered prompt emits `waiting_authentication` and suspends the
authentication timer. After negotiation, the independent operation idle timer
applies (0–3600 seconds, 0 disables it). The default values are shown above.
Thus an open prompt cannot be reported as an idle transfer timeout.

Typed adapter errors include host_key, authentication, authentication_cancelled,
authentication_timeout, network, network_timeout, helper_missing,
incompatible_schema and protocol. OpenSSH exposes an untyped exit code; the
adapter translates its C-locale local prompts/failure messages internally.
Clients never match terminal text. Raw SSH stderr is bounded and withheld from
the public stream; unsupported or ambiguous failures do not become successful
operations. Remote browse filesystem errors retain native errno and exact
paths, attributed to the SSH endpoint.

The negotiated capabilities event has `backend: "native-ssh"` and
`peer_version`; negotiation precedes the remote operation. Its `operations`
contains only operations supported by both the peer and the adapter.
`peer_operations` reports the helper's underlying operations for inspection;
it does not itself enable SSH copy. Copies require the peer's
`transfer_bridge: "3"` and `typed_transfer_errors: true` (per-item events,
typed native failures, and destination/staging ownership checks). Bridges 1 and
2, and bridge 3 helpers without the typed-error guarantee, are refused before
copy operations. The native app-event, receiver-acknowledgement
and I/O-control features must also be negotiated. Older app helpers can still browse; a copy request
fails with `unsupported_feature` before mutation. A remote home/root
resolution returns its byte path and SSH kind. The app must retain and reuse
the original connection profile when navigating to this path.

Cancelling or losing the control/event pipe stops the job's own process group,
including its SSH/askpass descendants. Closing the SSH channel cancels the
remote app helper through its control-pipe contract. A remote cancellation
reports cleanup as unknown if the channel cannot deliver its final result;
stopping a client connection is not proof of remote filesystem cleanup.

Copy requests use the same public JSON schema shown above, with an SSH source
or destination endpoint. The two engines negotiate a private native-data
handoff on the authenticated channel. The helper checks its wire paths,
options, role, rate and timeout against the validated JSON request; it bypasses
CLI defaults and glob expansion, acquires the destination's advisory locks,
and uses native atomic outputs. Public clients continue to send and receive
NDJSON; bulk file data and the internal `transfer_ready` record never reach
the GUI event stream. No additional SSH login or rsync adapter is started.

The native receiver acknowledges writes and completed files separately. A
successful copy requires native receiver completion, requested metadata
completion, remote worker exit, and successful SSH exit. A lost connection is
an error with unknown cleanup, even if some bytes or files have completed.
After channel EOF, the remote supervisor allows two seconds for normal
teardown, sends SIGTERM, and forces termination after a further two seconds.
Normal EOF handling usually cleans up sooner. The bound is subject to OS
scheduling; forced termination cannot promise temporary-output cleanup.

## Lifecycle, completion and errors

`started` means the isolated child exists; it does not promise that destination
preflight passed. Progress is sampled at most ten times per second from native
counters: `logical_bytes_completed`, `logical_bytes_total`, `files_completed`,
`reused_bytes` (delta matched bytes) and `wire_bytes` (zero locally; native
protocol bytes sent plus received over SSH, excluding SSH encryption overhead).
Logical bytes count published regular-file work on local copies, pushes and
pulls. They stay at zero while a new file is staged, even when source reads
or receiver writes have advanced. These counters can lag publication briefly;
they never establish requested metadata success for an individual item.
On pushes, `receiver_bytes_written`
counts acknowledged staged writes while `logical_bytes_completed` and
`files_completed` count receiver-published files. `source_bytes_read` reports
logical source processing separately on local copies and pushes; these bytes
can still be waiting for publication. It is `null` on pulls, where a source
read counter is not available. It does not measure physical disk reads.
Current phase values include scanning, hashing, transferring, applying_metadata,
deleting and waiting_receiver, plus the SSH connection/authentication states.
Sampling continues during requested file metadata and deferred directory
metadata, after the file worker pool has joined. SSH receiver metadata phases
require the negotiated native progress-phase feature. Copy progress does not
start while connecting or waiting for credentials.
Delta basis signatures and reconstructed-output checksum verification expose
hashing work locally and at the SSH receiver. Remote phase sampling continues
through quiet signature reads and metadata operations, and stops before the
terminal receiver acknowledgement. Receiver hashing/metadata takes precedence
over the source's waiting-for-receiver state.

Copy inventory streams `item_discovered`, `item_stage`, `item_progress`,
`item_retry` and `item_result`. All use the same stable `item_id`: hexadecimal
bytes of the job-relative transfer path. An explicit selection mapping becomes
the top-level component of this path; the absolute `source_path` still names
the selected source object. The empty ID represents the destination
root when copying directory contents. An error uses this ID when a work item
is known; errors outside item work have `item_id: null`.

Common fields include the relative byte `path`, absolute byte `source_path`,
`destination_path`, `source_endpoint` and `destination_endpoint` (`local` or
`ssh`), `entry_type`, exact decimal `size`, `attempt`, `bytes_processed` and
`reused_bytes`. A source that cannot be examined has `entry_type: "unknown"`
and `size: null`; null never means zero bytes. Source preflight/scanning
failures and unsupported source types have a null `destination_path`, because
receiver planning has not produced a destination item. Unsupported nested
source types are discovered and skipped; an unsupported explicit selection
fails preflight. `side` distinguishes source
observations from receiver work. Source observations can precede discovery,
and source and receiver byte counts describe separate work: do not add them
together. Item progress is sampled at most ten times per second per side.
A retry resets that side's attempt counters; its reason is `source_changed`.

Item stages currently include `scanning`, `planning`, `reading_source`, `hashing`,
`waiting_source`, `waiting_receiver`, `transferring` and `applying_metadata`;
no stage is a completion guarantee. Reused bytes count verified basis blocks
copied into staging. They can be positive on a failed item whose content was
never published; they do not imply receiver-completed work.
Only one authoritative `item_result` follows each discovery during normally
completed work. Its status is `success`, `skipped`, `failure` or `cancellation`,
with a nullable machine-readable `reason`. `content_published` distinguishes
an installed regular file/link from failed staging. `metadata_complete` reports
whether the requested metadata operations succeeded; it is null for skips.
A metadata failure can therefore have published content and a failed outcome.
Directory outcomes follow deferred directory metadata and describe the directory
itself; a child's failure does not imply its parent's own metadata failed.
Skipped type-conflict descendants discovered over SSH use `ancestor_skipped`.

A forced stop, lost channel or fatal protocol error can interrupt the item
stream. Discovered items without a result then have **unknown** outcomes,
including unknown publication/metadata state. Never turn them into success.
The reference `TransferInventory` retains the current item view, ignores other
job IDs and late source observations after item completion, and can construct
explicit failed-item retries from byte paths and client-owned endpoint
profiles. `retry_requests(original_request)` groups failures by their original
destination parent, preserves copy options and SSH profiles, and assigns fresh
request IDs. Renamed entries retain their `destination_name` in the retry.
Use this for nested failures; `retry_selections()` only accepts
root-level selections and rejects retries that would flatten a nested path. A failed directory covers its failed descendants in a retry; unknown
items require an explicit opt-in. Cancelled items and a cancelled operation
never qualify, including when unknown items are opted in. Source listing failures identify the failed
directory and any observed failed child; they cannot enumerate children the
engine never observed. A child that failed stat/readlink has an owned failed
source outcome with its exact byte path. If any explicit selection fails
preflight, valid sibling selections are reported as `skipped` with reason
`preflight_failed`, and none are copied. Retry-failed selects only failed
sources; resubmit the skipped valid selections explicitly when they should
also be copied. Fatal native failures complete the known failed active item
after staging cleanup. Other interrupted items remain unknown.

`item_update` retains native itemization code, path, size and transferred bytes
for presentation. It is not authoritative completion and can precede item
discovery or final directory timestamps. The engine streams outcomes directly
through bounded pipes and does not retain an unbounded result history.

A copy `summary` is emitted after the native workers and requested metadata
finish; for SSH it also follows remote worker exit and SSH reaping. It includes
exact decimal `items_discovered` and `items_results` counters. Success is rejected
if item outcomes are incomplete. It is
followed by exactly one terminal `result` only
after the supervisor has drained events and reaped the child. The final status
is `success`, `partial_failure`, `failure`, `cancellation`, or `paused`. Only `success`
confirms that the native operation returned successfully. Completed bytes or
an item update never authorize source deletion. `durability` is
`filesystem-completion`: writes/renames and requested metadata operations have
finished, without a promise of fsync or survival after power loss.

Native browse, preflight, source scan/open/read/revalidation, output-IO and
metadata-helper failures emit `error`
with category, operation, local or SSH endpoint, path/item identity where available,
`native_code`, retryability and display message. Categories include permission,
disk_full, missing, vanished_source, not_directory, conflict, content and
filesystem. Source failures have `side: "source"`; metadata helpers have
`side: "destination"` and `stage: "metadata"`, so a metadata permission failure
can be distinguished from a content failure. `stage` also identifies source
scanning versus content work. Exact source paths and endpoint attribution can
drive explicit retries without matching diagnostic text. An observed source
identity/content change has `reason: "source_changed"` and a null native code;
an incomplete scan whose native cause is unavailable has
`reason: "incomplete_listing"` and a null native code. Synthetic conditions do
not pretend that a particular errno was returned by the operating system.
Structured
request errors use invalid_request, incompatible_schema and unsupported_feature.
Destination conflicts have `side:"destination"`,
`stage:"destination_revalidation"`, expected/observed revisions, and reason
`destination_changed`, `destination_ancestor_changed`, `destination_root_changed`
or `temporary_output_changed`. A kernel no-replace collision retains `EEXIST`;
an observed mismatch has a null native code. Item failures retain the publication
and metadata outcome independently of the typed conflict.
Human `diagnostic` records remain available for display. An engine failure
without an accompanying native error also emits a typed `error` with
`operation: "transfer"`, `stage: "engine_transfer"` and exact `engine_code`.
Its category comes from the engine status, including network, network_timeout,
protocol, unsupported_feature and vanished_source. Native errno, path, endpoint
and item may be null when the engine cannot attribute them. Native transport
read/configuration failures retain their available errno, have null path/side,
and `stage: "transport"`. Clients never reconstruct missing fields or retry
selections from diagnostic messages.

`retryable` is advice for automatic recovery of the current condition, not
a ban on a user-requested retry. For example, disk-full and permission errors
require external action; the reference inventory can still select their failed
items for an explicit retry after that action.

The G-05 contract covers the advertised copy options: entry/contents selection,
regular files/directories/symlinks, replace/skip, requested times/permissions,
worker counts and bandwidth limits, locally and over the negotiated SSH bridge.
The filesystem-action, safe-move and private-recovery contracts above extend
that initial scope. Ownership/ACL/xattr preservation, clone/in-place output and
filters remain unavailable; their CLI diagnostics do not advertise app support.

`result.code` is the native exit code as a string. The subprocess exit code
matches operation success/failure (signal cancellation is 20; a confirmed pause
is 0). A paused transfer need not have a completion summary. If the process
or pipe disappears without a final result, the client records an interrupted,
unknown outcome, never success. Results cannot be delivered to a closed or
permanently stalled event consumer.

## Cancellation, isolation and backpressure

Send `{"id":"cancel-1","op":"cancel","job_id":"copy-1"}` while the job runs.
The supervisor acknowledges the request and sends SIGTERM to that job only.
`cancel_ack.accepted` is false if the child was already reaped; the pending
authoritative result then keeps the completed operation's status.
The acknowledgement confirms receipt; the terminal result confirms cessation.
Repeated cancellation requests need distinct IDs. Closing stdin, SIGINT,
SIGTERM or SIGHUP also cancels the active job. The supervisor escalates after
2,000 ms to process termination; normal cleanup removes native temporary
outputs and preserves existing good files. `cleanup` is `finished` for graceful
exit or `unknown` after forced termination. Completed files and created
directories can remain after cancellation; there is no transaction rollback.

App regular-file staging records the inode created by that job and retains an
open descriptor through close/publication to prevent inode reuse. Publication
and cleanup verify that the temporary directory entry still names that inode.
A replaced temporary entry is neither published nor removed as owned output;
publication reports a typed conflict. Cleanup targets registered outputs only,
and does not sweep similarly named files. These identity checks still have a
check-to-filesystem-operation window against arbitrary external writers.

Events pass through bounded kernel pipes and bounded single-frame buffers.
Writers stop waiting after 2,000 ms without completing a frame. A stalled or
closed stdout consumer stops supervision and cancels the writer; allowing an
additional 2,000 ms for cleanup gives a normal bound of roughly four seconds,
subject to OS process scheduling. There is no unbounded event queue. The client
must drain output concurrently with sending control requests, and should drain
stderr independently if it needs human diagnostics. Stderr is never an API.

The child watches supervisor lifetime too; a hard supervisor crash stops its
writer within the same two-second grace period. Cleanup then has unknown status.
All global options/stats/sinks are private to each subprocess. Browsing can run
while another process copies; cancelling either cannot affect the other.

Cooperating app-mode copy processes acquire advisory shared locks on canonical
ancestor directory inodes and an exclusive lock on the existing destination.
Overlapping destinations, including directory aliases, fail preflight with a
retryable conflict rather than writing concurrently. Locks create no lockfiles
or destination content and release on exit. They do not coordinate with CLI
copies or external tools, and do not implement a transaction against arbitrary
concurrent filesystem changes. Native destination anchoring and source safety
checks still apply, including the destination observations described above.
These locks also serialize keep-both name choice and publication among
cooperating app jobs. A later job observes names published by the earlier job.

## Reference client and checks

### Persistent copy queue foundation — G-12 in progress

[tools/app_queue.py](../tools/app_queue.py) provides an app-owned `PersistentQueue`
and `execute_next` worker around `AppClient`. The journal uses private regular
files, a lifetime exclusive manager lock, bounded strict JSON, a flushed/synced
temporary file, atomic replacement and parent-directory sync. Keep its parent
directory in app-owned storage and keep the queue open until all workers return.
A claim is saved before launching the engine. A failed file sync does not admit
the job; a failed directory sync after replacement blocks further admission
until the journal is closed/reopened and its disk state reconciled. This journal
persistence contract does not add power-loss durability to engine destinations.

Enqueue an engine-shaped `copy` request. Local endpoints retain their literal
`path.bytes_hex`; SSH endpoints use `profile_id` instead of `connection`. Supply
a runtime `profile_resolver(profile_id)` when executing a job. Request/selection/
option allowlists reject saved connection objects, credentials, arbitrary CLI
options and destructive operations. Authentication answers, conflict responses
and prompt tokens are never written. The initial implementation accepts copy
jobs only; move/delete restart recovery needs a separate revision/outcome policy.

After the `AppClient` hello handshake and before sending a private copy, the
queue durably reserves a random ID when the local engine advertises exact
`copy_recovery_identity: "1"`. That commit must succeed before operation
submission; it survives restart even with no engine receipts. Older engines
retain their announced-ID behavior. Resume preserves the original ID, while a
proven unsubmitted fresh-copy retry reserves a new one. Missing or incompletely
created stores still fail reconciliation and cannot authorize an automatic copy.
Custom workers calling `claim` directly must call `record_engine_capabilities`
after hello and attach its non-null returned ID to the copy request before
submission; `execute_next` and `execute_queue` do this automatically.

The journal preserves queue order, semantic options, destination-name mappings,
engine recovery IDs and a bounded per-item outcome inventory. It supports
reordering all waiting jobs and cancelling a waiting job before launch. Its
`max_active` admission limit (1–64) counts engine jobs independently of each
request's `options.jobs` worker count. Concurrent `execute_next` callers share
that limit. Each engine process still runs exactly one job; this is a library
foundation, with no background scheduler or daemon.

Recovery creation, discoveries, item mappings, item results and the terminal
result, helper lifetime receipts and authoritative helper close proofs are
saved before `event_handler(event, client)` is notified. Progress
and prompt traffic do not rewrite the journal. Attempt IDs reject old events.
Completed and cancelled jobs remain terminal across restart. An attempt left
active becomes `needs_reconciliation`: known item results remain known, and
pending items become unknown. It cannot be dispatched without verified recovery. Losing a
worker/callback reaps its client and records that unknown outcome when possible.

An authoritative paused private copy can be explicitly continued with
`request_resume`, preserving the original selection/options and recovery ID.
It remains paused across manager restart until that call. Use `stop_active` to
save pause/cancel intent before sending the engine control; accepted control
acknowledgements are saved too. A lost acknowledgement/result cannot erase a
user's cancellation. Cancelled jobs are never selected for retry, including
verified unknown work with saved cancel intent. `reconciliation_request` prepares an engine
`recovery_state` inspection, and `record_reconciliation` records a complete
successful inspection as an observation only. Even a store reporting
`completed` cannot invent a missing authoritative result.

`reconcile_job` performs that inspection, checks every recorded uncleaned SSH
actor through a fresh authenticated `recovery_quiescence` request, then executes
`verify_recovery` with the original copy binding and inspected inventory token.
A header's `cleaned` marker is accepted only with the matching authoritative
helper-close proof already saved by this queue; a missing lease/receipt cannot
stand in for quiescence. SSH work without lifetime receipts remains unknown.
The reconciler streams and discards per-file inspection events while retaining
bounded aggregate summaries/proofs. Only a complete successful verification
with all helper proofs can mark the job `recoverable`. Its terminal result
remains absent; admission requires `request_resume` or the explicit automatic
recovery policy described below. Resume
still performs fresh source/prefix/destination validation before publishing.
Changed guards, malformed/unknown private work and missing/stale/busy helper
evidence leave work blocked when proof cannot be obtained.

Read-only reconciliation requests use bounded retry delays (by default 0.1,
0.25 and 0.5 seconds, at most eight delays of five seconds each). A fresh client
is reaped between attempts. Only typed retryable destination/actor locks and
network/network-timeout failures are retried. Credential/host-key failures,
changed guards, missing/stale evidence, protocol failures and cancellations
cannot be retried under a broad `retryable` flag. Lost transfer results are
never retried directly; continuation requires fresh reconciliation and verification.

For SSH copies that fail before any operation request is submitted, the local
engine advertises exact string `copy_reconnect: "1"` and can emit
`copy_not_submitted` with `operation: "copy"`, `endpoint: "ssh"`,
`remote_request_submitted: false` and `transfer_started: false`. It marks
submission before putting operation bytes in the outgoing SSH buffer, so a
partial or failed write cannot produce this receipt. A helper that dies after
receiving its request does not qualify, even if no item/actor event arrived.
This local transport receipt does not need a new remote capability; remote
copy/recovery capabilities still undergo their usual exact negotiation before
submission. Before submission, authentication/hello negotiation can create
temporary broker files and locks, but no copy destination/private recovery data.
An allocated `recovery_preparing` ID alone does not indicate a created store.
Missing receipts or missing terminal results prove nothing.

Opt in with `enqueue(request, reconnect_delays=(0.1, 0.25, 0.5))`, or call
`set_reconnect(job_id, delays)` while the job is queued before its first claim.
Defaults disable automatic reconnect. The journal bounds the policy to eight
delays, each at most five seconds (rounded up to milliseconds), and saves the
remaining budget, attempt history, exact engine capability flag and receipt,
sanitized network-error evidence and UTC deadline. Only a complete authoritative
`failure` plus the exact-capability receipt and typed retryable
`ssh_connect` network/network-timeout errors can enter `retry_waiting`. Other
errors, transfer/recovery activity, pause/cancel intent, cancelled results,
unknown results and exhausted budgets disqualify it. Authentication, host-key
and protocol failures cannot qualify through a broad retryable flag. Credentials,
runtime profiles, diagnostic text and prompt responses remain outside records.

Waiting jobs retain the failed attempt's authoritative result and consume no
active slot. Queue reorder includes them; admission skips them before their
deadline so ready jobs can proceed. After restart, an already durable waiting
failure retains its budget and can become ready; an active attempt becomes
unknown and cannot use a previously observed receipt without its terminal
result. Clock rollback clamps a remaining delay to its configured bound and
saves the adjusted deadline rather than producing an unbounded wait. A forward
clock change may make a waiting job immediately ready. `cancel_queued` also
cancels waiting reconnects and preserves that cancellation across restart.

`execute_queue(queue, binary, **options)` is an app-owned worker generator. It
yields every authoritative attempt result, waits in responsive intervals for
scheduled reconnects, and uses the shared active-job limit. A new, reaped client
and fresh runtime profile resolution are required for each attempt. The next
fresh copy discards its never-created recovery identity; an explicitly resumed
job keeps its existing whole-job recovery identity. A `stop_event` stops waiting
and future dispatch; active engine work uses the existing explicit pause/cancel
controls. Worker exceptions stop that attempt; unknown work can only continue
under the separate guarded recovery policy. Other workers/UI actions may cancel or reorder during
backoff. Selective failed-leaf child jobs do not inherit reconnect policy
implicitly; callers can choose it through `set_reconnect` before their launch.

For private SSH copies, `enqueue(..., reconnect_delays=(0.1, 0.25, 0.5),
recover_disconnected=True)` also opts into guarded whole-job recovery after
possible submission. `set_reconnect` accepts the same flag before the first
claim. This requires `retain_partials: true` and a nonempty bounded delay list;
the default remains manual recovery. Pre-submission retries and reconciliation
cycles share one saved budget. Typed retryable `ssh_connect`, `transfer` or
`read_transport` network failures can schedule recovery. Missing final results,
consumer loss and manager restart can also schedule it when the private ID is
known. Authentication, host-key, protocol and other known errors block this
policy, as does any pause/cancel intent. Missing IDs remain unknown.

Known item outcomes remain known. A failed transport's authoritative result is
retained in attempt history; the uncertain whole-job result becomes absent.
After its deadline, `claim_recovery` reserves a `reconciling` job under the shared
active-job limit and durably records a unique claim token. Fresh inspection,
helper-quiescence checks and original-binding/inventory/destination verification
must all succeed. Reaped read-only clients precede `finish_recovery`, which
durably admits a `resume` with the original recovery ID. Fresh source/prefix
checks still run in that mutating attempt. This resumes the whole selection and
can refresh changed source versions; it is distinct from failed-only retries.
Verification never proves a lost operation completed or manufactures success.

Read-only busy/network failures may consume another bounded cycle; permanent
errors, missing evidence and changed guards stop automatic admission. Request
IDs include the claim token, and stale proofs cannot authorize a later claim.
Restart during inspection or after verification discards that proof and requires
a new cycle within the remaining budget. An already admitted resume revalidates
guards in the engine. Manual reconciliation cannot steal an automatic claim.
`cancel_recovery` saves cancellation for uncertain work and retires the claim;
late proofs cannot resurrect it. It leaves the result unknown and does not
claim helper termination or completed cleanup. No destructive action is retried.

`retry_failed(job_id, item_ids=None)` atomically admits fresh copy jobs for
reported failed files/symlinks from an authoritative `failure` or
`partial_failure` attempt. It verifies each byte source path against the original
selection and each actual destination mapping against the original endpoint
scope, groups leaves by their mapped destination parent, and retains literal
renamed names and external profile references. Completed, skipped, cancelled
and unknown items cannot enter these jobs. A job with saved cancel intent or
without an authoritative result cannot qualify. Default selection includes all
failed items; a failed directory rejects that selection instead of recopying
its successful children or silently omitting the directory. The caller may
explicitly select supported failed leaves while directory work stays unresolved.

Each child saves `retry_of: {job_id, attempt, item_ids}` in the same durable
commit as admission. Original outcomes remain intact; the loader validates
lineage, request/mapping correspondence and duplicate admission, so repeating
retry-failed after restart cannot create another copy for those items. A failed
child can itself be retried through its own reported failures. Cancelling a
waiting child retains its admission record; creating another operation requires
an explicit new copy rather than bypassing that cancellation through its parent.
Original `replace` becomes `ask` so present targets receive a fresh revision-bound
decision; `ask` and `skip` retain their behavior. No prior conflict answer is
transferred to a new job.

These are fresh subset copies with independent recovery identities, fresh source
reads and destination guards, not prefix resumes of the original whole-job
binding. Original private stores remain available for guarded inspection/cleanup
and are never silently consumed or removed. A subset publication may make an
original store's old destination receipt stale; that store then cannot authorize
whole-job resume. Selective directory retries and failed-only prefix reuse need
additional engine support and remain open. Unknown attempts still require their
separate reconciliation contract before any continuation.

Limits are 1,024 jobs/selections, 100,000 observed items per job and a 16 MiB
journal. Invalid/unsupported existing files are preserved and rejected instead
of resetting to an empty queue. Reconciliation gaps, selective directory retries,
failed-only prefix reuse, incomplete store creation/publication reconciliation
and endpoint/global resource policy remain open in
G-12/G-16. The visual app remains responsible for queue rendering and profiles.

```python
from tools.app_client import endpoint
from tools.app_queue import PersistentQueue, execute_next

request = {
    'op': 'copy',
    'sources': [{'endpoint': endpoint('/tmp/source'), 'mode': 'contents'}],
    'destination': endpoint('/tmp/destination'),
    'options': {'on_conflict': 'replace', 'preserve_times': True,
                'preserve_permissions': True, 'retain_partials': True},
}

with PersistentQueue('/app-owned/queue.json', max_active=2) as queue:
    queue.enqueue(request, 'transfer')
    execute_next(queue, '/app-owned/xs')
```

The queue boundary tests are in `tests/app_queue_test.py`; the SSH suite includes
pause → manager restart → keep-both resume with external profiles in both
directions. G-12 remains open for the complete workflow.

### Reference client

[tools/app_client.py](../tools/app_client.py) demonstrates launching, negotiation,
live event consumption, paths, copying, acknowledged cancellation and final
result handling without parsing terminal text:

```sh
python3 tools/app_client.py probe
python3 tools/app_client.py list /tmp/source
python3 tools/app_client.py copy --contents --on-conflict replace \
  --preserve-times --preserve-permissions /tmp/source /tmp/destination
python3 tools/app_client.py --cancel-after 0.5 copy --contents \
  --on-conflict replace --bandwidth 1048576 /tmp/source /tmp/destination
python3 tests/app_test.py -v
python3 tests/app_retry_test.py -v
python3 tests/app_mapping_test.py -v
python3 tests/app_conflict_test.py -v
python3 tests/app_actions_test.py -v
python3 tests/app_move_test.py -v
python3 tests/app_queue_test.py -v
python3 tools/app_client.py move --on-conflict replace /tmp/source/file /tmp/destination
python3 tools/app_client.py --interactive-conflicts copy --contents --on-conflict ask /tmp/source /tmp/destination
./tests/ssh-rig.sh app_ssh_test.py
python3 tests/rig/app_host.py
python3 tools/app_client.py --ssh-profile profile.json --interactive-auth probe
python3 tools/app_client.py --ssh-profile profile.json --interactive-auth list /tmp/source
python3 tools/app_client.py --ssh-profile profile.json --interactive-auth copy \
  --direction push --contents --on-conflict replace /tmp/source /remote/destination
python3 tools/app_client.py --ssh-profile profile.json --interactive-auth copy \
  --direction pull --contents --on-conflict replace /remote/source /tmp/destination
```

Explicit selection mappings and interactive conflict decisions are implemented. Typed errors,
observed outcomes and destination-preserving retry requests have G-05 acceptance
coverage. The SSH browsing/authentication contract has real-SSH
acceptance coverage; the app still owns prompt rendering and credential storage.
The reference client's `AppClient.run` accepts `prompt_handler` and
`conflict_handler` callbacks for desktop integration. A conflict callback returns
a decision string or a dictionary containing `decision`, optional `scope`, and
optional `destination_name`; without a handler the client cancels the conflict.
Conflict callbacks run serially on a daemon client thread while the main loop
continues reading events and handling cancellation. GUI integrations should
marshal display work to their UI thread. The pending callback queue is bounded
to 64; an overflow cancels the job rather than blocking event consumption.
Its optional `--interactive-auth` and `--interactive-conflicts` are demonstration UIs;
the engine itself does not acquire a terminal or parse terminal input.
