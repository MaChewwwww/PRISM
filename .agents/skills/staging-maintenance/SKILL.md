---
name: staging-maintenance
description: Perform state-changing maintenance on the BGH staging server over SSH — recreate or restart Compose services, pull GHCR images, roll back to a previous image tag, prune Docker storage, refresh config-only clones, run project scripts or seeders, and perform root-level host administration via the admin key. Use when asked to fix, deploy, restart, roll back, seed, or clean up staging. For inspection only, use staging-diagnostics instead.
---

# Staging Maintenance

## Overview

Change the state of the BGH staging server deliberately and verifiably. This is
the write-capable counterpart to `staging-diagnostics`, which stays strictly
read-only — do not weaken that skill to perform actions; use this one.

Every action here is expected to alter the server. Say what you are about to run
before running it, run the smallest command that achieves the goal, and verify
afterwards with an explicit check rather than an assumption.

## Connection Setup

1. Read `docs/deployment/staging-server-maintenance-cheatsheet.md` before
   choosing commands, and `docs/deployment/single-azure-vm.md` for the runbook.
2. Read `.env.devops` only if it exists. Do not create, print, stage, or commit
   it. Keys used by this skill:

   | Key | Use |
   |---|---|
   | `STAGING_SSH_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_PORT` | Connection target for all routine work |
   | `STAGING_SSH_KEY_PATH` | Key for the `deploy` user — the default for everything in [Allowed Operations](#allowed-operations) |
   | `PEM_Location` | Key for the VM's **admin** user, used only for [Root-Level Operations](#root-level-operations) |

3. Do not source `.env.devops` as a shell script. Parse only simple `KEY=value`
   lines.
4. **Ignore `DEPLOY_USER_PASSWORD` if present.** Never read it, echo it, pass it
   to `sudo -S`, or embed it in a command — piping a password into `sudo`
   publishes it to the server's process list on every invocation. Root access
   goes through the admin key instead, which needs no password.
5. **Ignore `GITHUB_PAT` if present.** This skill does not call the GitHub API;
   branch and PR work belongs to the `github-pr` skill, and the `gh` CLI is
   already authenticated from its own credential store. Never read this value
   or pass it to `gh`, `git`, or `curl`.

```powershell
ssh -i <STAGING_SSH_KEY_PATH> <STAGING_SSH_USER>@<STAGING_SSH_HOST> "command_here"
```

Use `-o ServerAliveInterval=60 -o ServerAliveCountMax=3` for long operations.
Use an SSH agent for a key passphrase.

Nearly all maintenance needs no `sudo`: the `deploy` user is in the `docker`
group, so Compose, image, and volume operations work directly.

## Serialize With The Deploy Lock

The nine GHCR-backed repositories deploy automatically on a merge to their
`staging` branch, and those CI jobs hold `flock /tmp/bgh-staging-deploy.lock`.
Manual Compose work can otherwise race an in-flight automated deploy and leave a
service on an unexpected image. Take the same lock for any operation that
recreates, restarts, or pulls:

```bash
flock /tmp/bgh-staging-deploy.lock bash -lc '
  cd /opt/bgh/Capstone_BGH
  docker compose --env-file .env.compose up -d --no-deps --force-recreate <service>
'
```

Use a **login shell** (`bash -lc`). `COMPOSE_FILE` is exported from
`/etc/profile.d/bgh-compose.sh` and activates the `compose.staging.yaml` overlay
that supplies GHCR image references. A non-login shell does not source it, and
Compose silently falls back to building from source for the six services whose
build context exists on disk. Verify with `echo $COMPOSE_FILE` if a command
unexpectedly starts building.

## Allowed Operations

- Recreate, restart, stop, or start Compose services; `pull` GHCR images.
- Roll back by pinning a previous immutable tag, e.g.
  `AUTH_IMAGE_TAG=sha-<short-sha> docker compose --env-file .env.compose up -d
  --no-deps --force-recreate auth-api`.
- Prune Docker storage: `docker image prune -af`, `docker builder prune -af`.
  `-a` is required — images orphaned by a deploy are tagged, not dangling, so a
  plain prune reclaims almost nothing.
- Refresh the six config-only clones with `git pull --ff-only origin staging`.
  Check `git status --porcelain` first and skip any clone with local changes.
- Run project scripts under `/opt/bgh/Capstone_BGH/scripts/`, including
  `start-bgh-ecosystem.sh --use-ghcr` and the seeders.
- Write-capable `docker compose exec -T` commands: migrations, seeders,
  catalog refreshes.
- Edit `.env.*` files on the server when a configuration value must change.
  Show the diff and the affected services before applying.

## Root-Level Operations

Covers `systemctl`, `mount`/`umount`, `/etc/fstab`, `apt`, `useradd`, firewall
rules, and anything writing outside `/opt/bgh` or Docker's own storage. The
`deploy` user cannot do these; use the admin key at `PEM_Location`.

Azure's cloud-init normally grants the VM's admin user `NOPASSWD:ALL`, so this
is key-based access with no password anywhere. **Verify that before relying on
it** — do not assume, and never fall back to a password if the check fails:

```bash
ssh -i <PEM_Location> <ADMIN_USER>@<STAGING_SSH_HOST> \
  "whoami; sudo -n true && echo NOPASSWD_OK || echo NOPASSWD_ABSENT"
```

If it prints `NOPASSWD_OK`, run root work over that connection, prefixing each
privileged command with `sudo -n` so it fails loudly rather than hanging on a
password prompt. If it prints `NOPASSWD_ABSENT`, or the admin user or key is
unknown, stop: hand the user the exact command with a one-line note on what it
changes and the expected downtime. For anything longer than a couple of
commands, write a script, `scp` it over, check it with `bash -n`, and give the
user one `sudo bash ...` line.

Root-level changes are higher-risk than Compose work, so regardless of which
path is used:

- Confirm with the user before anything causing downtime (`systemctl stop
  docker`, reboots, disk migrations). State the expected duration.
- Back up any file before editing it in place — `cp -a /etc/fstab
  /etc/fstab.bak.$(date +%Y%m%d-%H%M%S)` — and say where the backup is.
- After **any** `/etc/fstab` or mount change, run `findmnt --verify` and confirm
  `mountpoint /mnt/bgh-data` and `mountpoint /var/lib/containerd`. That disk
  carries every Docker volume and containerd's image store, and its entry uses
  `nofail`, so a malformed entry fails silently at boot and the stack returns
  with empty databases. Never leave a `findmnt --verify` warning outstanding,
  and never reboot with one.
- Prefer a root-owned script at a fixed path over ad-hoc privileged one-liners,
  so the change is reviewable and repeatable.

## Provisioning A New Server

Two scripts cover the parts that are easy to get wrong. Both are idempotent and
support `--status`, so run that first to see what a host already has.

**1. Disk layout — before Docker accumulates images.**

```bash
sudo bash ./scripts/bootstrap-server-disk.sh --device /dev/sdc   # confirm with lsblk
```

Formats and mounts the data disk with a correctly prefixed `UUID=` fstab entry,
bind-mounts containerd's store onto it, and verifies with `findmnt --verify`.
Doing this first avoids a later migration: with the containerd snapshotter,
image layers land in `/var/lib/containerd`, so a `/var/lib/docker` symlink does
**not** keep them off the OS disk. After the stack is up and verified, reclaim
the old store with `--cleanup`.

**2. GitHub access — no PAT on the server.**

```bash
# on the server
bash ./scripts/bootstrap-server-git-access.sh          # prints a PUBLIC key
```

Then register that public key from the local machine, where `gh` is
authenticated — a public key is not a secret, so it is safe to pass through:

```bash
gh ssh-key add - --title "bgh-<hostname>" <<'EOF'
<paste the printed public key>
EOF
```

Finish on the server:

```bash
bash ./scripts/bootstrap-server-git-access.sh --set-remotes
```

The private key is generated on the server and never leaves it. Prefer this over
writing a PAT into `~/.git-credentials`: nothing expires, so no server-side pull
can break on a lapsed token, and revocation is a single key deletion. Use
`gh repo deploy-key add` instead if per-repo read-only scoping is wanted —
GitHub rejects one deploy key across multiple repositories, so that needs one
key per repo.

Remaining steps are covered by the runbook: clone the workspace, run
`bootstrap-root-env.sh`, populate `.env.*`, harden ports, and start the stack
with `start-bgh-ecosystem.sh --use-ghcr`. See
`docs/deployment/single-azure-vm.md`.

## Destructive Operations

Confirm with the user before any of these, even when the request implies them:

- `docker compose down` (stops the whole stack), or `down -v` / `docker volume
  rm` / `docker system prune --volumes`, which **delete databases**.
- Deleting or reinitialising any volume, or dropping/truncating database tables.
- Anything targeting the observability stack's retention data.

Postgres and ClickHouse run their init scripts only on an empty volume, so a
deleted volume does not simply rebuild itself — it comes back schemaless.

Never point these commands at anything other than the confirmed staging host.

## Verification

After every change, prove it worked rather than assuming:

1. `docker compose --env-file .env.compose ps` — confirm the service is running
   and, where a healthcheck exists, healthy.
2. Confirm the **image actually in use** is the one intended:
   `docker compose --env-file .env.compose ps --format "{{.Service}}|{{.Image}}"`.
   A successful `up -d` does not prove the right tag was pulled.
3. Hit the service's health endpoint from the cheatsheet's table.
4. For a Gateway change, additionally check a proxied route (`/media/<service>/...`)
   rather than only `/health`.

Report what changed, the evidence it worked, and anything that did not.

## Rollback

Every GHCR-backed service can be rolled back without a checkout, because what
runs is the image:

```bash
flock /tmp/bgh-staging-deploy.lock bash -lc '
  cd /opt/bgh/Capstone_BGH
  <SERVICE>_IMAGE_TAG=sha-<known-good> docker compose --env-file .env.compose \
    up -d --no-deps --force-recreate <service>
'
```

Find a known-good tag from the repository's Actions history or `docker images`.
Note that a rolled-back tag survives only until that repo's next `staging` merge,
which will deploy over it — fix forward rather than relying on the pin.
