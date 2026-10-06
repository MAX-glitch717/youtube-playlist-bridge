# Publish the repository

Suggested name: `playlistbridge`

Suggested description: A Mac playlist-to-MP3 helper with automatic folder sync, a local browser dashboard, and optional BPM tagging for DJ libraries.

1. Unzip this archive and open Terminal in its `PlaylistBridge` folder.
2. Create an empty repository on GitHub. For the commercial source version, start with a private repository. Do not initialize the remote with another README, license or gitignore.
3. Run the following, replacing YOUR-USERNAME with your GitHub username:

```bash
git init -b main
git add .
git update-index --chmod=+x -- '*.command'
git commit -m "Prepare PlaylistBridge 1.1.0 for GitHub"
git remote add origin https://github.com/YOUR-USERNAME/playlistbridge.git
git push -u origin main
```

Authenticate using your usual GitHub credential manager or SSH setup; do not put access tokens in project files.

The archive includes `.github`, `.gitignore` and `.gitattributes`. Finder may hide these; Git includes them with `git add .`. There is no pre-existing `.git` directory, account information or remote.

## Automated checks

The Checks workflow runs on pushes, pull requests and manual dispatch. It verifies core behavior on Ubuntu with Python 3.12 and FFmpeg. It does not claim Mac installer coverage or download real YouTube music. GitHub-hosted execution has not been run as part of preparing this archive. See TEST-RESULTS.md for local evidence and the manual Mac test checklist.

## Build a customer download

```bash
python3 scripts/package_release.py
```

Output: `dist/PlaylistBridge-Mac.zip`. The builder uses an explicit allowlist and includes executable permissions for command files. It excludes repository metadata, runtime environments, logs, local settings and downloaded audio. Keep the source ZIP for development and distribute the generated customer ZIP separately.

After checks pass, create a GitHub release tagged `v1.1.0` and attach that generated ZIP if you want to distribute it through GitHub. A release in a private repository is available only to people with repository access. For selling downloads, distribute the customer ZIP through your chosen storefront instead.

## Licensing

No open-source license or customer sales agreement has been selected or added. This packaging step does not grant an MIT/GPL license to your project. Choose your intended source and customer license before public distribution. Third-party component information is in THIRD-PARTY.md.
