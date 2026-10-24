# RW7-delta-breakdown-apollo

rsync is at least 5% faster than xs in some delta cell, and xs with --whole-file shows whether xs's delta path or its copy is the cause.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T172300Z-RW7-delta-breakdown-apollo.
- Valid blocks: 36. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | rsync-W | 2 | 1.974 [1.836, 2.122] | 1.974 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 1.308 [1.012, 1.692] | 1.308 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 1.009 [0.939, 1.085] | 1.009 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.127 [0.967, 1.313] | 1.127 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.940 [0.281, 3.144] | 0.940 | 1.0000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | rsync-W | 2 | 1.256 [0.066, 23.853] | 1.256 | 1.0000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.408 [0.000, 156077.573] | 1.408 | 1.0000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 0.793 [0.556, 1.131] | 0.793 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.063 [0.000, 1868252.016] | 1.063 | 1.0000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.420 [0.000, 397.689] | 0.420 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.690 [2.522, 2.868] | 2.690 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.969 [0.804, 1.168] | 0.969 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 1.112 [0.513, 2.410] | 1.112 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.113 [1.062, 1.166] | 1.113 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 1.009 [0.769, 1.323] | 1.009 | 1.0000 | too few blocks |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | rsync-W | 2 | 2.963 [0.001, 8346.365] | 2.963 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.577 [0.000, 343108.350] | 1.577 | 1.0000 | too few blocks |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 2.805 [0.100, 78.727] | 2.805 | 0.5000 | too few blocks |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.364 [0.000, 4154.882] | 1.364 | 1.0000 | too few blocks |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.824 [0.060, 11.327] | 0.824 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.010 [0.324, 12.474] | 2.010 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 1.217 [0.547, 2.709] | 1.217 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 1.042 [0.468, 2.320] | 1.042 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.092 [0.661, 1.804] | 1.092 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.982 [0.358, 2.690] | 0.982 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | rsync-W | 2 | 0.896 [0.000, 10728.785] | 0.896 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.077 [0.000, 14971790.327] | 1.077 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 0.848 [0.000, 24014527.652] | 0.848 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.572 [0.000, 932.165] | 0.572 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 1.821 [0.000, 16622.547] | 1.821 | 1.0000 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.600 [1.009, 6.700] | 2.600 | 0.5000 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.195 [0.996, 4.835] | 2.195 | 0.5000 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 0.877 [0.541, 1.420] | 0.877 | 0.5000 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.350 [0.284, 6.411] | 1.350 | 0.5000 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.920 [0.262, 3.230] | 0.920 | 1.0000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | rsync-W | 2 | 0.792 [0.010, 60.542] | 0.792 | 1.0000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.625 [0.002, 207.532] | 0.625 | 0.5000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 0.376 [0.000, 1592.357] | 0.376 | 0.5000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.657 [0.416, 1.037] | 0.657 | 0.5000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.672 [0.233, 1.943] | 0.672 | 0.5000 | too few blocks |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.866 [2.197, 3.739] | 2.866 | 0.5000 | too few blocks |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.383 [1.741, 3.261] | 2.383 | 0.5000 | too few blocks |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 0.967 [0.764, 1.223] | 0.967 | 0.5000 | too few blocks |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.271 [1.207, 1.338] | 1.271 | 0.5000 | too few blocks |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.938 [0.616, 1.428] | 0.938 | 0.5000 | too few blocks |
| `large-solo.update-10pct.mac-apollo.sender.warm` | rsync-W | 2 | 0.938 [0.565, 1.560] | 0.938 | 0.5000 | too few blocks |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.815 [0.056, 11.889] | 0.815 | 1.0000 | too few blocks |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 0.936 [0.008, 110.325] | 0.936 | 1.0000 | too few blocks |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.048 [0.536, 2.047] | 1.048 | 1.0000 | too few blocks |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.748 [0.001, 736.094] | 0.748 | 1.0000 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | rsync-W | 2 | 3.109 [3.051, 3.169] | 3.109 | 0.5000 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.353 [1.460, 3.791] | 2.353 | 0.5000 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 0.919 [0.647, 1.305] | 0.919 | 0.5000 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.231 [0.980, 1.546] | 1.231 | 0.5000 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.910 [0.573, 1.446] | 0.910 | 0.5000 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | rsync-W | 2 | 0.845 [0.002, 431.057] | 0.845 | 1.0000 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.727 [0.054, 9.751] | 0.727 | 0.5000 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 0.436 [0.000, 124763.622] | 0.436 | 1.0000 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.015 [0.010, 105.219] | 1.015 | 1.0000 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.940 [0.343, 2.573] | 0.940 | 1.0000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.702 [2.686, 2.718] | 2.702 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.401 [2.084, 2.766] | 2.401 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 1.014 [0.482, 2.136] | 1.014 | 1.0000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.174 [0.853, 1.617] | 1.174 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.910 [0.382, 2.171] | 0.910 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | rsync-W | 2 | 0.978 [0.632, 1.514] | 0.978 | 1.0000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.550 [0.104, 23.181] | 1.550 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 1.955 [0.389, 9.820] | 1.955 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.525 [0.000, 2012.685] | 0.525 | 1.0000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 1.227 [0.128, 11.735] | 1.227 | 0.5000 | too few blocks |
| `large-text.update-10pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.440 [1.064, 5.596] | 2.440 | 0.5000 | too few blocks |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.589 [1.981, 3.385] | 2.589 | 0.5000 | too few blocks |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 0.869 [0.386, 1.957] | 0.869 | 0.5000 | too few blocks |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.157 [0.960, 1.395] | 1.157 | 0.5000 | too few blocks |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.878 [0.424, 1.817] | 0.878 | 0.5000 | too few blocks |
| `large-text.update-10pct.mac-apollo.sender.warm` | rsync-W | 2 | 1.439 [0.013, 155.817] | 1.439 | 1.0000 | too few blocks |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.905 [0.000, 14908.785] | 1.905 | 1.0000 | too few blocks |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 1.036 [0.000, 22589740.741] | 1.036 | 1.0000 | too few blocks |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.692 [0.031, 91.568] | 1.692 | 0.5000 | too few blocks |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 1.642 [0.000, 7812.139] | 1.642 | 1.0000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | rsync-W | 2 | 2.908 [2.231, 3.789] | 2.908 | 0.5000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.631 [1.863, 3.718] | 2.631 | 0.5000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2 | 0.982 [0.163, 5.916] | 0.982 | 1.0000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.240 [0.989, 1.555] | 1.240 | 0.5000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 0.962 [0.715, 1.294] | 0.962 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | rsync-W | 2 | 1.595 [0.216, 11.802] | 1.595 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.321 [0.528, 3.306] | 1.321 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 2 | 0.548 [0.001, 520.361] | 0.548 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.502 [0.000, 3483.995] | 0.502 | 1.0000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.812 [0.758, 0.870] | 0.812 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | rsync-W | 2.958 [2.907, 3.009] | 13.523 [12.975, 14.094] | 2.103 [2.044, 2.165] |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.478 [1.234, 1.770] | 0.992 [0.914, 1.077] | 1.351 [1.135, 1.608] |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.751 [1.447, 2.119] | 9.409 [3.276, 27.020] | 1.006 [0.854, 1.184] |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.144 [0.974, 1.344] | 0.982 [0.975, 0.989] | 1.148 [0.963, 1.367] |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.711 [0.367, 1.380] | 5.586 [5.023, 6.213] | 0.913 [0.356, 2.339] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | rsync-W | 2.795 [2.646, 2.954] | 0.990 [0.920, 1.066] | 1.258 [0.067, 23.600] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.666 [1.133, 2.450] | 0.993 [0.783, 1.259] | 1.409 [0.000, 157816.212] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.667 [0.853, 3.258] | 7.804 [7.248, 8.403] | 0.792 [0.529, 1.186] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.200 [0.729, 1.975] | 0.991 [0.934, 1.052] | 1.065 [0.000, 1880642.447] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.768 [0.076, 7.791] | 7.586 [3.778, 15.231] | 0.419 [0.000, 389.376] |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | rsync-W | 3.237 [3.066, 3.417] | 13.756 [9.254, 20.450] | 2.861 [2.675, 3.059] |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.454 [0.936, 2.257] | 1.020 [0.777, 1.338] | 0.972 [0.755, 1.252] |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.795 [1.109, 2.906] | 9.368 [7.700, 11.396] | 1.133 [0.486, 2.640] |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-rs | 1.190 [1.131, 1.252] | 1.026 [0.746, 1.412] | 1.125 [1.017, 1.244] |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.737 [0.686, 0.793] | 6.222 [3.647, 10.615] | 1.011 [0.755, 1.352] |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | rsync-W | 3.022 [2.618, 3.489] | 0.996 [0.986, 1.006] | 2.965 [0.001, 8080.674] |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1.218 [1.069, 1.388] | 0.985 [0.938, 1.035] | 1.572 [0.000, 319254.438] |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 1.732 [1.694, 1.770] | 7.894 [6.749, 9.233] | 2.820 [0.098, 80.824] |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-rs | 1.093 [1.051, 1.136] | 1.002 [0.912, 1.100] | 1.326 [0.001, 2696.502] |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.727 [0.716, 0.739] | 7.070 [3.803, 13.141] | 0.826 [0.061, 11.124] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | rsync-W | 3.176 [0.841, 11.985] | 13.395 [9.182, 19.540] | 2.154 [0.292, 15.890] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.338 [0.987, 1.815] | 1.006 [0.865, 1.168] | 1.244 [0.512, 3.021] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.954 [1.914, 1.995] | 9.491 [7.446, 12.098] | 1.058 [0.438, 2.554] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.189 [1.060, 1.334] | 0.996 [0.935, 1.061] | 1.106 [0.617, 1.981] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.815 [0.677, 0.982] | 5.637 [5.398, 5.886] | 0.974 [0.319, 2.971] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | rsync-W | 2.508 [0.646, 9.734] | 0.982 [0.568, 1.696] | 0.900 [0.000, 10648.581] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.195 [0.648, 2.201] | 1.003 [0.710, 1.416] | 1.080 [0.000, 14776993.846] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.705 [0.279, 10.433] | 7.930 [5.999, 10.482] | 0.841 [0.000, 20349522.803] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.050 [0.955, 1.153] | 1.007 [0.816, 1.242] | 0.573 [0.000, 905.686] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.702 [0.335, 1.472] | 7.061 [4.209, 11.845] | 1.824 [0.000, 17349.280] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | rsync-W | 2.937 [1.184, 7.285] | 13.649 [12.800, 14.555] | 2.610 [1.045, 6.522] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.360 [0.922, 2.005] | 0.996 [0.937, 1.058] | 2.204 [0.967, 5.023] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.760 [1.505, 2.058] | 9.489 [9.223, 9.763] | 0.875 [0.536, 1.430] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.183 [0.315, 4.452] | 1.003 [0.861, 1.169] | 1.350 [0.281, 6.484] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.688 [0.231, 2.048] | 5.739 [5.724, 5.755] | 0.917 [0.254, 3.316] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | rsync-W | 3.149 [3.119, 3.179] | 0.993 [0.902, 1.092] | 0.792 [0.010, 60.346] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.537 [1.206, 1.957] | 0.995 [0.922, 1.075] | 0.625 [0.002, 205.714] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.704 [1.491, 1.949] | 7.803 [7.175, 8.486] | 0.376 [0.000, 1596.878] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.102 [0.846, 1.436] | 0.992 [0.865, 1.138] | 0.656 [0.410, 1.051] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.722 [0.263, 1.984] | 8.212 [6.059, 11.131] | 0.670 [0.242, 1.855] |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | rsync-W | 3.272 [2.894, 3.699] | 13.461 [13.019, 13.919] | 2.888 [2.123, 3.927] |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.243 [1.207, 1.281] | 1.000 [0.964, 1.039] | 2.398 [1.671, 3.442] |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.952 [1.748, 2.180] | 9.445 [8.869, 10.059] | 0.965 [0.761, 1.223] |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-rs | 1.136 [1.106, 1.167] | 1.010 [0.923, 1.105] | 1.275 [1.193, 1.362] |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.698 [0.518, 0.941] | 5.848 [5.718, 5.981] | 0.939 [0.613, 1.438] |
| `large-solo.update-10pct.mac-apollo.sender.warm` | rsync-W | 3.040 [1.899, 4.866] | 1.030 [0.802, 1.325] | 0.937 [0.549, 1.599] |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1.107 [0.822, 1.490] | 1.007 [0.921, 1.101] | 0.815 [0.056, 11.942] |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 1.697 [1.378, 2.091] | 7.911 [7.350, 8.515] | 0.937 [0.008, 110.602] |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-rs | 1.030 [0.624, 1.700] | 1.008 [0.949, 1.071] | 1.049 [0.537, 2.046] |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.715 [0.276, 1.854] | 8.114 [8.000, 8.230] | 0.749 [0.001, 731.053] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | rsync-W | 3.460 [3.445, 3.476] | 13.820 [10.528, 18.142] | 3.130 [2.925, 3.350] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.265 [1.024, 1.562] | 1.016 [0.971, 1.062] | 2.367 [1.410, 3.972] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.924 [1.406, 2.634] | 10.281 [6.262, 16.878] | 0.916 [0.649, 1.293] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.118 [0.991, 1.262] | 1.011 [0.965, 1.059] | 1.233 [0.976, 1.559] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.697 [0.619, 0.786] | 5.847 [5.804, 5.890] | 0.910 [0.579, 1.430] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | rsync-W | 3.265 [2.127, 5.011] | 0.997 [0.895, 1.111] | 0.845 [0.002, 428.325] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.114 [0.650, 1.909] | 0.996 [0.857, 1.157] | 0.727 [0.055, 9.638] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.685 [0.702, 4.043] | 7.880 [7.745, 8.017] | 0.435 [0.000, 119663.137] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.051 [0.638, 1.732] | 0.997 [0.906, 1.096] | 1.012 [0.010, 104.313] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.728 [0.388, 1.366] | 7.929 [5.739, 10.956] | 0.940 [0.345, 2.561] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | rsync-W | 3.276 [2.961, 3.625] | 13.559 [11.670, 15.753] | 2.781 [2.759, 2.803] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.661 [1.475, 1.871] | 1.033 [0.981, 1.087] | 2.458 [2.154, 2.805] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.921 [0.789, 4.676] | 9.498 [9.394, 9.602] | 1.007 [0.560, 1.810] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.109 [1.030, 1.194] | 1.024 [0.880, 1.191] | 1.190 [0.871, 1.625] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.694 [0.263, 1.832] | 5.852 [5.434, 6.302] | 0.908 [0.371, 2.224] |
| `large-text.append-1pct.mac-apollo.sender.warm` | rsync-W | 2.823 [0.932, 8.544] | 1.001 [0.699, 1.434] | 0.976 [0.646, 1.476] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.554 [0.282, 8.557] | 0.999 [0.814, 1.224] | 1.549 [0.102, 23.548] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.594 [0.516, 4.923] | 7.988 [6.487, 9.838] | 1.956 [0.386, 9.908] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.079 [0.276, 4.215] | 1.009 [0.900, 1.131] | 0.525 [0.000, 2012.774] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.669 [0.173, 2.588] | 9.140 [1.385, 60.305] | 1.226 [0.124, 12.121] |
| `large-text.update-10pct.apollo-mac.receiver.warm` | rsync-W | 3.123 [1.623, 6.012] | 13.340 [11.892, 14.964] | 2.510 [1.021, 6.171] |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.510 [1.260, 1.811] | 0.999 [0.977, 1.020] | 2.659 [1.911, 3.698] |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 1.867 [1.331, 2.619] | 8.736 [6.313, 12.090] | 0.868 [0.385, 1.959] |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs | 1.116 [0.888, 1.403] | 0.992 [0.864, 1.139] | 1.165 [0.959, 1.416] |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.701 [0.357, 1.376] | 5.594 [5.441, 5.752] | 0.876 [0.403, 1.905] |
| `large-text.update-10pct.mac-apollo.sender.warm` | rsync-W | 2.820 [1.465, 5.427] | 1.002 [0.981, 1.024] | 1.437 [0.015, 139.417] |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1.008 [0.264, 3.856] | 0.995 [0.776, 1.277] | 1.907 [0.000, 13895.867] |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 1.422 [0.337, 5.998] | 7.920 [7.268, 8.630] | 1.034 [0.000, 22369151.131] |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.955 [0.293, 3.108] | 0.996 [0.811, 1.223] | 1.690 [0.033, 87.257] |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.606 [0.097, 3.786] | 7.945 [1.151, 54.831] | 1.595 [0.000, 7900.463] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | rsync-W | 3.573 [3.348, 3.813] | 13.414 [12.002, 14.992] | 2.991 [2.355, 3.800] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.529 [1.529, 1.530] | 0.994 [0.915, 1.080] | 2.701 [1.880, 3.879] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 2.012 [1.075, 3.766] | 8.728 [2.093, 36.400] | 0.996 [0.180, 5.493] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.163 [1.024, 1.321] | 0.997 [0.920, 1.080] | 1.249 [0.990, 1.576] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.743 [0.551, 1.001] | 5.595 [4.306, 7.269] | 0.958 [0.693, 1.325] |
| `large-text.update-1pct.mac-apollo.sender.warm` | rsync-W | 2.963 [1.852, 4.739] | 1.024 [0.806, 1.300] | 1.597 [0.213, 11.991] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.142 [1.056, 1.236] | 1.014 [0.810, 1.268] | 1.320 [0.514, 3.395] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.830 [0.952, 3.519] | 8.088 [5.891, 11.104] | 0.549 [0.001, 525.994] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.061 [0.757, 1.486] | 1.025 [0.799, 1.316] | 0.503 [0.000, 3567.360] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.790 [0.357, 1.748] | 8.803 [1.273, 60.866] | 0.811 [0.786, 0.838] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-W | xs-cpp | xs-cpp-W | xs-rs | xs-rs-W |
|---|---|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | 0.557 | 1.100 | 0.729 | 0.562 | 0.628 | 0.524 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | 1.152 | 1.448 | 1.622 | 0.914 | 1.225 | 0.484 |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | 0.727 | 1.956 | 0.705 | 0.809 | 0.809 | 0.734 |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | 0.915 | 2.712 | 1.444 | 2.567 | 1.249 | 0.754 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | 0.548 | 1.102 | 0.667 | 0.571 | 0.599 | 0.538 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | 1.101 | 0.986 | 1.185 | 0.934 | 0.629 | 2.005 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | 4.807 | 12.499 | 10.551 | 4.215 | 6.489 | 4.424 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | 24.908 | 19.731 | 15.567 | 9.366 | 16.362 | 16.745 |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | 4.624 | 13.256 | 11.019 | 4.471 | 5.877 | 4.338 |
| `large-solo.update-10pct.mac-apollo.sender.warm` | 17.138 | 16.082 | 13.961 | 16.046 | 17.957 | 12.822 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | 4.793 | 14.902 | 11.276 | 4.404 | 5.900 | 4.362 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | 22.540 | 19.043 | 16.386 | 9.821 | 22.869 | 21.177 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | 1.475 | 3.985 | 3.541 | 1.496 | 1.732 | 1.342 |
| `large-text.append-1pct.mac-apollo.sender.warm` | 4.796 | 4.690 | 7.435 | 9.374 | 2.520 | 5.885 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | 1.428 | 3.485 | 3.697 | 1.241 | 1.652 | 1.254 |
| `large-text.update-10pct.mac-apollo.sender.warm` | 3.685 | 5.301 | 7.021 | 3.817 | 6.234 | 6.049 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | 1.414 | 4.111 | 3.721 | 1.388 | 1.754 | 1.361 |
| `large-text.update-1pct.mac-apollo.sender.warm` | 5.862 | 9.349 | 7.742 | 3.210 | 2.942 | 4.759 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | rsync-W | 0.0080 | 8 | 8 |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0286 | 10 | 12 |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0081 | 8 | 8 |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0170 | 8 | 8 |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.1344 | 164 | 220 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | rsync-W | 0.3276 | 966 | 1293 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.2929 | 15001 | 20105 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 0.0395 | 17 | 21 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.6004 | 22986 | 30807 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.7628 | 5223 | 7000 |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | rsync-W | 0.0071 | 8 | 8 |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.0208 | 8 | 8 |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0861 | 69 | 92 |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.0052 | 8 | 8 |
| `hs-16x256m.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0302 | 11 | 13 |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | rsync-W | 0.8841 | 7016 | 9403 |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1.3679 | 16793 | 22506 |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 0.3712 | 1239 | 1659 |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.8928 | 7154 | 9588 |
| `hs-16x256m.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.2917 | 766 | 1026 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | rsync-W | 0.2032 | 373 | 499 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0891 | 74 | 98 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0891 | 74 | 98 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0558 | 30 | 40 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.1122 | 115 | 154 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | rsync-W | 1.0452 | 9805 | 13140 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.8306 | 30074 | 40306 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.9098 | 32729 | 43865 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.8233 | 6084 | 8154 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 1.0150 | 9246 | 12391 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | rsync-W | 0.1054 | 102 | 136 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0879 | 72 | 95 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0537 | 28 | 37 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.1734 | 272 | 364 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.1398 | 178 | 237 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | rsync-W | 0.4826 | 2093 | 2804 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.6461 | 3749 | 5023 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 0.9295 | 7755 | 10392 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.0508 | 26 | 34 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.1181 | 128 | 170 |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | rsync-W | 0.0296 | 10 | 13 |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.0349 | 13 | 17 |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0261 | 9 | 11 |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.0057 | 8 | 8 |
| `large-solo.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0468 | 22 | 29 |
| `large-solo.update-10pct.mac-apollo.sender.warm` | rsync-W | 0.0566 | 31 | 41 |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.2984 | 801 | 1073 |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 0.5308 | 2531 | 3391 |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.0745 | 52 | 69 |
| `large-solo.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.7670 | 5282 | 7078 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | rsync-W | 0.0021 | 8 | 8 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0531 | 28 | 36 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0390 | 16 | 21 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0254 | 8 | 10 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0515 | 26 | 34 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | rsync-W | 0.6939 | 4324 | 5794 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.2890 | 752 | 1007 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 1.3985 | 17552 | 23523 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.5166 | 2397 | 3212 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.1122 | 115 | 154 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | rsync-W | 0.0007 | 8 | 8 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0158 | 8 | 8 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0829 | 64 | 85 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0356 | 14 | 18 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0967 | 86 | 115 |
| `large-text.append-1pct.mac-apollo.sender.warm` | rsync-W | 0.0487 | 24 | 31 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.3011 | 816 | 1093 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp-W | 0.1797 | 292 | 391 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.9183 | 7570 | 10144 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.2513 | 569 | 762 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | rsync-W | 0.0924 | 79 | 105 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.0298 | 10 | 13 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.0904 | 76 | 101 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.0208 | 8 | 8 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0810 | 61 | 81 |
| `large-text.update-10pct.mac-apollo.sender.warm` | rsync-W | 0.5214 | 2442 | 3272 |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.9978 | 8936 | 11976 |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-cpp-W | 1.8807 | 31741 | 42541 |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.4442 | 1773 | 2376 |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.9425 | 7973 | 10685 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | rsync-W | 0.0295 | 10 | 13 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0385 | 16 | 20 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp-W | 0.1999 | 361 | 483 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0251 | 8 | 10 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0330 | 12 | 16 |
| `large-text.update-1pct.mac-apollo.sender.warm` | rsync-W | 0.2228 | 448 | 599 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.1021 | 96 | 128 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp-W | 0.7631 | 5228 | 7007 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.9845 | 8700 | 11659 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.0077 | 8 | 8 |
