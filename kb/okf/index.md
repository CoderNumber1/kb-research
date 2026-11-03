# Open Knowledge Format

The Open Knowledge Format v0.2 specification — knowledge bundles, concepts, YAML frontmatter, provenance/trust/lifecycle families, reserved files, cross-linking, and conformance.

See [domain.md](domain.md) for scope and conventions.

# Concepts

* [Bundle structure and frontmatter](bundle-and-frontmatter.md) - How an OKF v0.2 knowledge bundle is laid out and what frontmatter each concept carries.
* [OKF conformance and versioning](conformance.md) - The three rules a bundle must satisfy to be OKF v0.2 conformant, what consumers must tolerate, and how versions and the v0.1→v0.2 changes work.
* [Cross-linking in OKF](cross-linking.md) - How OKF concepts link to each other, which fields hold paths, and how consumers treat those links.
* [Provenance, trust, and lifecycle (OKF v0.2)](provenance-trust-lifecycle.md) - The optional v0.2 frontmatter families — sources with footnote attribution, generated/verified trust, status and stale_after lifecycle — and the actor and datetime conventions they use.
