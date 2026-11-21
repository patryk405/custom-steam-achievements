# Steam account cloud sync

Connect Steam cloud in Millennium's Custom Achievements settings. Follow the browser link, sign in on steamcommunity.com and approve the named device. Repeat once on each device. The verified Steam account must match the account currently used by Steam on that device.

The tracker uploads automatically tracked progress every 30 seconds and merges downloads into its local account profile. It keeps the highest progress and earliest unlock date. It works offline and catches up when connectivity returns. Downloaded historical achievements do not replay notifications. Manual test progress is excluded. The six built-in catalogs are supported; downloaded third-party pack synchronization is not yet supported.

A Steam ID is an identifier, not authentication. The website verifies Steam OpenID assertions server-side, checks the return URL, signed fields, nonce and browser state, and stores only hashes of session/device tokens. Device tokens expire after 180 days and can be revoked under Steam Account on the website. This is this project's cloud storage, not Valve Steam Cloud or official profile achievements.

Local profiles live under `${XDG_DATA_HOME:-~/.local/share}/custom-achievements/accounts/<SteamID>/`. Tokens are mode 0600. Do not share this folder. The first detected Steam account adopts legacy local progress, which is backed up once before migration. Subsequent accounts start separately. Steam's current-user heartbeat takes precedence; the fallback accepts only a single unambiguous local Steam account. Ambiguous accounts pause tracking rather than guessing.

The tracker must run on each device. Linux and Steam Deck desktop mode use the same Python service and Millennium plugin. Big Picture/Decky UI integration and a physical Steam Deck installation still need testing. Game adapters and game files are configured separately on each device; cloud sync does not make an unsupported game adapter work.

The cloud endpoint must be reachable by devices without a ChatGPT access gate. Private Sites previews block device API calls; do not distribute a Sites bypass token. Public hosting does not make progress public: session checks protect account progress and device management. Online synchronization is unavailable until public access is enabled and each device is paired.

Local reset currently does not reset cloud progress: monotonic synchronization restores existing unlocks. Disconnect cloud before local-only reset tests. To remove a device's future access, revoke it on the website; disconnecting in the plugin removes only the local credential.

The production UI is hosted on GitHub Pages; the API and database are hosted on Supabase. Browser login uses a single-use Steam OpenID exchange bound to a SHA-256 verifier stored only in the initiating browser session. Browser sessions are kept in sessionStorage, not URL parameters. Device tokens are unchanged by the backend migration.
