# F-08 bounded parent capability comparison

Clean candidate `9f260833c926` versus production-equivalent reference `027e14d8b03f`, explicit one worker, clones/progress/fallback disabled. Six rotated samples per tool and three excluded warmups: all 18 timed copies and warmups passed independent checksum/metadata verification.

| Tool | Median wall seconds | Median CPU seconds | Peak RSS bytes |
|---|---:|---:|---:|
| Reference | 4.461870 | 3.646457 | 31555584 |
| Parent capabilities | 3.822005 | 2.821935 | 31080448 |
| rsync | 2.182016 | 2.911598 | 27344896 |

Candidate CPU improves 22.6% and wall improves 14.3%. CPU remains above one second; F-08 stays open. This does not qualify a manifest strategy or the later descriptor-limit policy.

The Mac was busy (load [33.57861328125, 38.63916015625, 35.33837890625] to [56.21826171875, 44.62109375, 39.09619140625]) and physical storage was 99% full. Preserve all samples; these results do not establish quiet-host throughput.

Correctness: 231 macOS and 227 Linux differential cases, eleven destination-scope, nine lifetime, fifteen protocol and thirteen P0 cases per platform, with existing skips. Subtree/macOS cases and three large staged-list cases pass as recorded in the linked logs.

Raw [results](20261010-f08-parent-noop.json), [validation state](20261010-f08-parent-state.json), [comparison log](20261010-f08-parent-comparison.log), and [Linux correctness log](20261010-f08-parent-linux.log).
