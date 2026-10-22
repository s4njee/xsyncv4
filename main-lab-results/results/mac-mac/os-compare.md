# mac-mac against Linux in the mix

xs time / rsync time per cell (below 1: xs faster), geometric means of durable_s. Written by os_compare.py.

| Source | Other end | Cells |
|---|---|---|
| mac-mac MM1 (xs-e6b) | macOS | 16 |
| mac-mac MM1 (xs-cpp -j4) | macOS | 16 |
| mac-mac MM0 sentinel | macOS | 8 |
| mars on Linux E6b | Linux | 20 |
| mars on Linux S3 sentinel | Linux | 8 |
| freya on Linux G0 | Linux | 8 |

## Discrepancies (ratio moved more than 10%, or the winner changed)

| Cell | Mac | mac-mac | ratio | Linux in the mix | ratio | change |
|---|---|---|---|---|---|---|
| mixed-bimodal fresh | Mac receives | mac-mac MM1 (xs-e6b) | 0.445 | freya on Linux G0 | 0.496 | -10% |
| mixed-bimodal fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.419 | mars on Linux E6b | 0.488 | -14% |
| mixed-bimodal fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.419 | freya on Linux G0 | 0.496 | -16% |
| mixed-bimodal fresh | Mac receives | mac-mac MM0 sentinel | 0.401 | mars on Linux E6b | 0.488 | -18% |
| mixed-bimodal fresh | Mac receives | mac-mac MM0 sentinel | 0.401 | freya on Linux G0 | 0.496 | -19% |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.584 | mars on Linux E6b | 0.362 | +61% |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.584 | mars on Linux S3 sentinel | 0.342 | +71% |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.584 | freya on Linux G0 | 0.304 | +92% |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.538 | mars on Linux E6b | 0.362 | +49% |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.538 | mars on Linux S3 sentinel | 0.342 | +57% |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.538 | freya on Linux G0 | 0.304 | +77% |
| mixed-bimodal fresh | Mac sends | mac-mac MM0 sentinel | 0.498 | mars on Linux E6b | 0.362 | +38% |
| mixed-bimodal fresh | Mac sends | mac-mac MM0 sentinel | 0.498 | mars on Linux S3 sentinel | 0.342 | +46% |
| mixed-bimodal fresh | Mac sends | mac-mac MM0 sentinel | 0.498 | freya on Linux G0 | 0.304 | +64% |
| mixed-bimodal noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.738 | mars on Linux E6b | 0.888 | -17% |
| mixed-bimodal noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.738 | mars on Linux S3 sentinel | 0.894 | -17% |
| mixed-bimodal noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.701 | mars on Linux S3 sentinel | 0.792 | -12% |
| real-congress fresh | Mac receives | mac-mac MM1 (xs-e6b) | 0.578 | mars on Linux E6b | 0.723 | -20% |
| real-congress fresh | Mac receives | mac-mac MM1 (xs-e6b) | 0.578 | freya on Linux G0 | 0.899 | -36% |
| real-congress fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.54 | mars on Linux E6b | 0.723 | -25% |
| real-congress fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.54 | freya on Linux G0 | 0.899 | -40% |
| real-congress fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.734 | mars on Linux E6b | 0.235 | +212% |
| real-congress fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.734 | freya on Linux G0 | 0.233 | +215% |
| real-congress fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.714 | mars on Linux E6b | 0.235 | +204% |
| real-congress fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.714 | freya on Linux G0 | 0.233 | +206% |
| real-congress noop | Mac receives | mac-mac MM1 (xs-e6b) | 0.573 | mars on Linux E6b | 0.717 | -20% |
| real-congress noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.437 | mars on Linux E6b | 0.717 | -39% |
| real-congress noop | Mac sends | mac-mac MM1 (xs-e6b) | 0.383 | mars on Linux E6b | 0.251 | +53% |
| real-congress noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.297 | mars on Linux E6b | 0.251 | +18% |
| small-deep fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 1.026 | mars on Linux E6b | 0.859 | +19% (winner changed) |
| small-deep fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.851 | mars on Linux E6b | 0.284 | +200% |
| small-deep fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.828 | mars on Linux E6b | 0.284 | +192% |
| small-deep noop | Mac receives | mac-mac MM1 (xs-e6b) | 1.012 | mars on Linux E6b | 1.853 | -45% |
| small-deep noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 1.051 | mars on Linux E6b | 1.853 | -43% |
| small-deep noop | Mac sends | mac-mac MM1 (xs-e6b) | 0.335 | mars on Linux E6b | 0.222 | +51% |
| small-deep noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.313 | mars on Linux E6b | 0.222 | +41% |
| small-flat fresh | Mac receives | mac-mac MM1 (xs-e6b) | 0.647 | freya on Linux G0 | 0.767 | -16% |
| small-flat fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.662 | freya on Linux G0 | 0.767 | -14% |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.79 | mars on Linux E6b | 0.404 | +96% |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.79 | mars on Linux S3 sentinel | 0.408 | +94% |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-e6b) | 0.79 | freya on Linux G0 | 0.584 | +35% |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.791 | mars on Linux E6b | 0.404 | +96% |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.791 | mars on Linux S3 sentinel | 0.408 | +94% |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.791 | freya on Linux G0 | 0.584 | +35% |
| small-flat fresh | Mac sends | mac-mac MM0 sentinel | 0.748 | mars on Linux E6b | 0.404 | +85% |
| small-flat fresh | Mac sends | mac-mac MM0 sentinel | 0.748 | mars on Linux S3 sentinel | 0.408 | +83% |
| small-flat fresh | Mac sends | mac-mac MM0 sentinel | 0.748 | freya on Linux G0 | 0.584 | +28% |
| small-flat noop | Mac receives | mac-mac MM1 (xs-e6b) | 0.564 | mars on Linux E6b | 0.664 | -15% |
| small-flat noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.349 | mars on Linux E6b | 0.664 | -47% |
| small-flat noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.349 | mars on Linux S3 sentinel | 0.589 | -41% |
| small-flat noop | Mac receives | mac-mac MM0 sentinel | 0.57 | mars on Linux E6b | 0.664 | -14% |
| small-flat noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.288 | mars on Linux E6b | 0.447 | -36% |
| small-flat noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.288 | mars on Linux S3 sentinel | 0.474 | -39% |
| small-flat noop | Mac sends | mac-mac MM0 sentinel | 0.499 | mars on Linux E6b | 0.447 | +12% |

## Every cell

| Cell | Mac | Source | xs s | rsync s | xs/rsync | blocks |
|---|---|---|---|---|---|---|
| large-text fresh | Mac receives | freya on Linux G0 | 10.919 | 31.623 | 0.345 | 8 |
| large-text fresh | Mac sends | freya on Linux G0 | 10.55 | 25.782 | 0.409 | 8 |
| mixed-bimodal fresh | Mac receives | mac-mac MM1 (xs-e6b) | 4.462 | 10.016 | 0.445 | 6 |
| mixed-bimodal fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 4.192 | 10.016 | 0.419 | 6 |
| mixed-bimodal fresh | Mac receives | mac-mac MM0 sentinel | 4.595 | 11.458 | 0.401 | 4 |
| mixed-bimodal fresh | Mac receives | mars on Linux E6b | 5.309 | 10.872 | 0.488 | 12 |
| mixed-bimodal fresh | Mac receives | mars on Linux S3 sentinel | 3.868 | 8.705 | 0.444 | 8 |
| mixed-bimodal fresh | Mac receives | freya on Linux G0 | 5.248 | 10.573 | 0.496 | 8 |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-e6b) | 5.809 | 9.945 | 0.584 | 7 |
| mixed-bimodal fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 5.346 | 9.945 | 0.538 | 7 |
| mixed-bimodal fresh | Mac sends | mac-mac MM0 sentinel | 4.04 | 8.117 | 0.498 | 4 |
| mixed-bimodal fresh | Mac sends | mars on Linux E6b | 2.368 | 6.543 | 0.362 | 12 |
| mixed-bimodal fresh | Mac sends | mars on Linux S3 sentinel | 1.994 | 5.83 | 0.342 | 10 |
| mixed-bimodal fresh | Mac sends | freya on Linux G0 | 2.064 | 6.78 | 0.304 | 8 |
| mixed-bimodal noop | Mac receives | mac-mac MM1 (xs-e6b) | 0.43 | 0.455 | 0.945 | 7 |
| mixed-bimodal noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.335 | 0.455 | 0.738 | 7 |
| mixed-bimodal noop | Mac receives | mac-mac MM0 sentinel | 0.371 | 0.453 | 0.818 | 4 |
| mixed-bimodal noop | Mac receives | mars on Linux E6b | 0.456 | 0.513 | 0.888 | 12 |
| mixed-bimodal noop | Mac receives | mars on Linux S3 sentinel | 0.407 | 0.456 | 0.894 | 8 |
| mixed-bimodal noop | Mac sends | mac-mac MM1 (xs-e6b) | 0.419 | 0.539 | 0.778 | 6 |
| mixed-bimodal noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.378 | 0.539 | 0.701 | 6 |
| mixed-bimodal noop | Mac sends | mac-mac MM0 sentinel | 0.383 | 0.505 | 0.758 | 4 |
| mixed-bimodal noop | Mac sends | mars on Linux E6b | 0.266 | 0.365 | 0.73 | 12 |
| mixed-bimodal noop | Mac sends | mars on Linux S3 sentinel | 0.297 | 0.375 | 0.792 | 10 |
| real-congress fresh | Mac receives | mac-mac MM1 (xs-e6b) | 49.034 | 84.859 | 0.578 | 6 |
| real-congress fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 45.783 | 84.859 | 0.54 | 6 |
| real-congress fresh | Mac receives | mars on Linux E6b | 67.8 | 93.747 | 0.723 | 12 |
| real-congress fresh | Mac receives | freya on Linux G0 | 54.255 | 60.351 | 0.899 | 8 |
| real-congress fresh | Mac sends | mac-mac MM1 (xs-e6b) | 32.388 | 44.129 | 0.734 | 6 |
| real-congress fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 31.487 | 44.129 | 0.714 | 6 |
| real-congress fresh | Mac sends | mars on Linux E6b | 9.869 | 42.023 | 0.235 | 12 |
| real-congress fresh | Mac sends | freya on Linux G0 | 9.743 | 41.813 | 0.233 | 8 |
| real-congress noop | Mac receives | mac-mac MM1 (xs-e6b) | 3.268 | 5.699 | 0.573 | 6 |
| real-congress noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 2.489 | 5.699 | 0.437 | 6 |
| real-congress noop | Mac receives | mars on Linux E6b | 4.069 | 5.673 | 0.717 | 12 |
| real-congress noop | Mac sends | mac-mac MM1 (xs-e6b) | 2.589 | 6.763 | 0.383 | 6 |
| real-congress noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 2.007 | 6.763 | 0.297 | 6 |
| real-congress noop | Mac sends | mars on Linux E6b | 1.913 | 7.623 | 0.251 | 12 |
| small-deep fresh | Mac receives | mac-mac MM1 (xs-e6b) | 43.954 | 47.248 | 0.93 | 6 |
| small-deep fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 48.496 | 47.248 | 1.026 | 6 |
| small-deep fresh | Mac receives | mars on Linux E6b | 53.921 | 62.787 | 0.859 | 12 |
| small-deep fresh | Mac sends | mac-mac MM1 (xs-e6b) | 24.612 | 28.934 | 0.851 | 6 |
| small-deep fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 23.962 | 28.934 | 0.828 | 6 |
| small-deep fresh | Mac sends | mars on Linux E6b | 8.921 | 31.459 | 0.284 | 12 |
| small-deep noop | Mac receives | mac-mac MM1 (xs-e6b) | 9.046 | 8.94 | 1.012 | 7 |
| small-deep noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 9.394 | 8.94 | 1.051 | 7 |
| small-deep noop | Mac receives | mars on Linux E6b | 10.694 | 5.77 | 1.853 | 12 |
| small-deep noop | Mac sends | mac-mac MM1 (xs-e6b) | 3.967 | 11.855 | 0.335 | 6 |
| small-deep noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 3.711 | 11.855 | 0.313 | 6 |
| small-deep noop | Mac sends | mars on Linux E6b | 3.098 | 13.979 | 0.222 | 12 |
| small-flat fresh | Mac receives | mac-mac MM1 (xs-e6b) | 18.479 | 28.582 | 0.647 | 6 |
| small-flat fresh | Mac receives | mac-mac MM1 (xs-cpp -j4) | 18.926 | 28.582 | 0.662 | 6 |
| small-flat fresh | Mac receives | mac-mac MM0 sentinel | 18.452 | 26.627 | 0.693 | 4 |
| small-flat fresh | Mac receives | mars on Linux E6b | 20.858 | 30.304 | 0.688 | 12 |
| small-flat fresh | Mac receives | mars on Linux S3 sentinel | 16.745 | 26.476 | 0.632 | 8 |
| small-flat fresh | Mac receives | freya on Linux G0 | 19.636 | 25.606 | 0.767 | 8 |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-e6b) | 13.763 | 17.416 | 0.79 | 6 |
| small-flat fresh | Mac sends | mac-mac MM1 (xs-cpp -j4) | 13.77 | 17.416 | 0.791 | 6 |
| small-flat fresh | Mac sends | mac-mac MM0 sentinel | 13.714 | 18.338 | 0.748 | 4 |
| small-flat fresh | Mac sends | mars on Linux E6b | 4.37 | 10.83 | 0.404 | 12 |
| small-flat fresh | Mac sends | mars on Linux S3 sentinel | 4.385 | 10.744 | 0.408 | 10 |
| small-flat fresh | Mac sends | freya on Linux G0 | 3.86 | 6.61 | 0.584 | 8 |
| small-flat noop | Mac receives | mac-mac MM1 (xs-e6b) | 0.824 | 1.46 | 0.564 | 7 |
| small-flat noop | Mac receives | mac-mac MM1 (xs-cpp -j4) | 0.51 | 1.46 | 0.349 | 7 |
| small-flat noop | Mac receives | mac-mac MM0 sentinel | 0.829 | 1.455 | 0.57 | 4 |
| small-flat noop | Mac receives | mars on Linux E6b | 0.938 | 1.412 | 0.664 | 12 |
| small-flat noop | Mac receives | mars on Linux S3 sentinel | 0.67 | 1.137 | 0.589 | 8 |
| small-flat noop | Mac sends | mac-mac MM1 (xs-e6b) | 0.782 | 1.715 | 0.456 | 6 |
| small-flat noop | Mac sends | mac-mac MM1 (xs-cpp -j4) | 0.495 | 1.715 | 0.288 | 6 |
| small-flat noop | Mac sends | mac-mac MM0 sentinel | 0.681 | 1.365 | 0.499 | 4 |
| small-flat noop | Mac sends | mars on Linux E6b | 0.376 | 0.84 | 0.447 | 12 |
| small-flat noop | Mac sends | mars on Linux S3 sentinel | 0.351 | 0.741 | 0.474 | 10 |
| tiny-one fresh | Mac receives | mars on Linux E6b | 0.301 | 0.385 | 0.781 | 12 |
| tiny-one fresh | Mac sends | mars on Linux E6b | 0.223 | 0.245 | 0.908 | 12 |
| tiny-one noop | Mac receives | mars on Linux E6b | 0.317 | 0.312 | 1.014 | 12 |
| tiny-one noop | Mac sends | mars on Linux E6b | 0.228 | 0.262 | 0.87 | 12 |
