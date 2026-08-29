# Security Policy

HyprConfig edits desktop configuration with the current user's privileges. It
does not require root. Malformed writes, unsafe command construction, broad
process control, and untrusted paths are therefore security concerns.

## Supported versions

Until the first stable release, security fixes are applied to the latest tagged
pre-release and the default branch. There are no long-term support branches.

## Reporting a vulnerability

Do not open a public issue or pull request for a vulnerability. Use GitHub's
[private vulnerability report](https://github.com/ghreprimand/hyprconfig/security/advisories/new).
Private reporting becomes available when the public repository is launched and
the feature is enabled.

Include the affected version or commit, the smallest safe reproduction, impact,
and any suggested mitigation. Remove real credentials, private configuration,
and identifying paths.

This is a best-effort, solo-maintained project. Reports will be acknowledged and
addressed as promptly as practical, without a guaranteed response time.

## In scope

- Writes outside explicitly configured Hyprland, Waybar, XDG, or wallpaper paths
- Command or configuration injection
- Symlink or path traversal that overwrites unintended files
- Destructive configuration replacement without the documented backup
- Process management that terminates unrelated user processes
- Unsafe handling of filenames, logs, or imported configuration

## Out of scope

- Missing optional integrations reported as ordinary compatibility bugs
- Problems requiring the user to run HyprConfig as root
- Visual defects without a confidentiality, integrity, or availability impact
- Vulnerabilities in Hyprland, Waybar, GTK, or other upstream projects that
  HyprConfig does not introduce
