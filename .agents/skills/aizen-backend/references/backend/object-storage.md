# Object storage — S3 and S3-compatible (MinIO, R2, GCS interop)

Files live in object storage, their metadata in the database. Decide in schema fork 7
(`references/db/schema-design.md`) whether the file record exists before its parent record.

## Rules

1. **The application never proxies large files.** Uploads and downloads go browser ↔ bucket with **presigned
   URLs**: short expiry (minutes), exact `Content-Type`, and a size limit (presigned POST with
   `content-length-range`, or validate after upload and delete what fails).
2. **Upload is two-phase**: issue URL + create a `pending` file row → client uploads → confirm endpoint checks
   the object exists (HEAD: size, type, checksum) → `ready`. A lifecycle rule or job deletes objects whose row
   never reached `ready`.
3. **Keys are opaque and scoped**: `tenant/<id>/<entity>/<uuid>` — never the user's filename (keep it as
   metadata), never guessable sequential ids. Authorization is checked before a download URL is issued.
4. **Buckets are private**: Block Public Access on; public assets go through a CDN with origin access control,
   not a public bucket. Bucket policy denies non-TLS requests. Server-side encryption on (SSE-S3 or KMS when the
   owner chose it).
5. **CORS** on the bucket allows only the app's origins and the methods it uses.
6. **Lifecycle** rules for temporary and old objects, versioning where accidental overwrite or delete must be
   recoverable — both stated in the infrastructure doc with their cost.
7. **Large objects**: multipart upload above ~100 MB; abort-incomplete-multipart lifecycle rule always.
8. Credentials: the workload's IAM role / instance profile, never long-lived keys in env files; IAM changes are A4,
   bucket creation and policy changes are A3 (`references/infra/authority.md`).
9. Local and test: MinIO or LocalStack in compose with the same client code (endpoint + path-style switch in
   config).

For AWS specifics, check the official docs (`references/core/decisions.md` §7): S3 behaviour, limits and prices
change, and claims without a dated source are `[unverified]`.
