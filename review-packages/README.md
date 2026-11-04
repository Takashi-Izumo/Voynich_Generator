# M1 independent review bundle

This branch distributes a review snapshot. It is not a promotion or a request to merge into main.

Download `m1-independent-review-20261105.zip` and its `.sha256` file from this directory. The ZIP contains:

- the uncommitted M1 implementation snapshot under `payload/experiments/`;
- the original request specification and `REVIEW_REQUEST_JA.md`;
- a read-only bundle verifier and per-file SHA-256 manifest;
- the frozen CAL model whose model-set hash matches the specification.

ZIP SHA-256:

```text
94fb7b87687e2b40d04637c10fed672cf6bfeacc0c81f0f487c03e42e73a23c0
```

The implementation must be reviewed against repository commit:

```text
c610c2a81e733748e0fb246de89143d6ecda764e
```

Extract the ZIP into a new directory, read `REVIEW_REQUEST_JA.md` and `verify_bundle.py`, then verify the bundle before copying its payload into the baseline checkout. Do not assume the review branch contains the implementation as loose repository source files; the exact snapshot being reviewed is inside the ZIP.

Use new output directories and reproduce the tests and small generation runs independently. Treat implementation-side PASS reports as claims to verify. In particular, review the shared request-ID/side-RNG contract and its implications for branch isolation and attribution. Do not edit the implementation to make tests pass, push fixes, run the full statistical contest, or declare promotion as part of this initial review.

The two large parent source archives and raw generated answer keys are not in this bundle. Obtain verified parent archives from the published v22.3 release if the verification environment does not already have them.
