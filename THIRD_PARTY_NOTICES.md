# Third-Party Notices

This repository bundles content from third-party projects. Each entry below is
redistributed under its own license, which is retained alongside the bundled
files. This file is a convenience index — the authoritative license text travels
with each bundled component.

## obsidian skill

- **Source:** [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (the `obsidian-markdown` and `obsidian-bases` skills)
- **Copyright:** © 2026 Steph Ango (@kepano)
- **License:** MIT
- **Bundled at:** [`.apm/skills/obsidian/`](.apm/skills/obsidian/)
- **License text:** [`.apm/skills/obsidian/LICENSE`](.apm/skills/obsidian/LICENSE)

The `obsidian` skill (`SKILL.md` and its `references/`, including `BASES.md` and
`FUNCTIONS_REFERENCE.md`) is adapted from the upstream `obsidian-markdown` and
`obsidian-bases` skills and redistributed under the MIT License.

## tripit-exporter skill

- **Source:** [caseyg's "TripIt Export" skill](https://lobehub.com/skills/caseyg-caseys-claude-tripit-export)
- **Copyright:** © Casey Grippi (@caseyg)
- **License:** Personal use (see below)
- **Bundled at:** [`.apm/skills/tripit-exporter/`](.apm/skills/tripit-exporter/)
- **License text:** [`.apm/skills/tripit-exporter/LICENSE`](.apm/skills/tripit-exporter/LICENSE)

The `tripit-exporter` skill (`SKILL.md`) is adapted from Casey Grippi's upstream
`tripit-export` skill and redistributed for personal use. As the upstream author
notes: "Personal use. Skills contain hardcoded assumptions (locations, accounts,
preferences) that you'd need to adapt for your own use."

## security-audit skill

- **Source:** [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) (`skills/security-audit/`, pinned in [`apm.yml`](apm.yml))
- **Copyright:** © 2025-2026 Cloudflare, Inc.
- **License:** MIT
- **Bundled at:** [`.agents/skills/security-audit/`](.agents/skills/security-audit/)
- **License text:** reproduced below, because the upstream `LICENSE` sits at the repository root and is not part of the installed skill folder.

The `security-audit` skill is an APM dependency, not authored here: `apm install`
materializes it unmodified, and the committed copy is the reviewable snapshot.

```text
MIT License

Copyright (c) 2025-2026 Cloudflare, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
