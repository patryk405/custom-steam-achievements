# Ocarina of Time — achievement set

66 objectives, 54 verified typed game-data signals, plus live walking, wallet and maximum health. Existing First Steps and Pocket Change IDs and progress are preserved.

The game schema is GameDataList.Product.110 from the installed v3.0.0 (source bd6a0cdd) build. Signal hashes, types and defaults are recorded in resources/oot-signals.json. Only zero-default Bool/Int signals present in that schema are watched. No game assets are distributed.

The adapter requests status and a 54-key read-only oot subscription on the same-user Unix socket. Missing or unreadable values cannot unlock achievements. Stored item-acquisition flags can unlock previously completed goals. Aggregate conditions use a single sample.

Not included pending reliable detection: final Ganon victory/credits, Epona ownership, four bottles, no-death/no-damage challenges. The catalog is a broad automatic set, not a claim to cover every possible task. Item acquisition, not boss death alone, awards the corresponding stones/medallions.

Validation: 18 Python tests and 6 frontend tests pass; every rule has positive and missing-signal coverage and transport is tested with a fake Unix server. The two starter objectives were verified in real play previously. The expanded set still requires real progression testing.

| Achievement | Requirement |
|---|---|
| First Steps | Walk 5 metres during gameplay. |
| Pocket Change | Have at least 1 Rupee in your wallet. |
| Kokiri Emerald | Obtain the Kokiri Emerald. |
| Goron Ruby | Obtain the Goron Ruby. |
| Zora Sapphire | Obtain the Zora Sapphire. |
| Light Medallion | Obtain the Light Medallion. |
| Forest Medallion | Obtain the Forest Medallion. |
| Fire Medallion | Obtain the Fire Medallion. |
| Water Medallion | Obtain the Water Medallion. |
| Shadow Medallion | Obtain the Shadow Medallion. |
| Spirit Medallion | Obtain the Spirit Medallion. |
| A Sword of Your Own | Obtain the Kokiri Sword. |
| Hero of Time | Obtain the Master Sword. |
| Forged by a Giant | Obtain the Biggoron’s Sword. |
| Ready for Adventure | Obtain the Deku Shield. |
| Reflect on This | Obtain the Mirror Shield. |
| Fairy Marksman | Obtain the Fairy Slingshot. |
| A Blast of Possibilities | Obtain the Bomb Bag. |
| Right Back at You | Obtain the Boomerang. |
| Fairy Archer | Obtain the Fairy Bow. |
| Reach for It | Obtain the Hookshot. |
| A Little Further | Obtain the Longshot. |
| Megaton Power | Obtain the Megaton Hammer. |
| Seeing Is Believing | Obtain the Lens of Truth. |
| Heavy Footsteps | Obtain the Iron Boots. |
| Walk on Air | Obtain the Hover Boots. |
| Too Hot to Handle | Obtain the Goron Tunic. |
| Under the Surface | Obtain the Zora Tunic. |
| Silver Strength | Obtain the Silver Gauntlets. |
| Golden Strength | Obtain the Golden Gauntlets. |
| Fire and Flight | Obtain the Fire Arrows. |
| Ice and Flight | Obtain the Ice Arrows. |
| Light Against Darkness | Obtain the Light Arrows. |
| An Instrument of Time | Obtain the Ocarina of Time. |
| Zelda’s Lullaby | Learn Zelda’s Lullaby. |
| Epona’s Song | Learn Epona’s Song. |
| Saria’s Song | Learn Saria’s Song. |
| Sun’s Song | Learn Sun’s Song. |
| Song of Time | Learn Song of Time. |
| Song of Storms | Learn Song of Storms. |
| Minuet of Forest | Learn Minuet of Forest. |
| Bolero of Fire | Learn Bolero of Fire. |
| Serenade of Water | Learn Serenade of Water. |
| Nocturne of Shadow | Learn Nocturne of Shadow. |
| Requiem of Spirit | Learn Requiem of Spirit. |
| Prelude of Light | Learn Prelude of Light. |
| A Fiery Gift | Obtain the Din’s Fire. |
| A Windy Escape | Obtain the Farore’s Wind. |
| Love Is a Shield | Obtain the Nayru’s Love. |
| A Touch of Magic | Obtain the magic meter. |
| More Magic | Obtain the double magic meter. |
| Blessed Protection | Obtain the double defense upgrade. |
| Behind the Mask | Obtain the Mask of Truth. |
| One of the Gerudo | Obtain the Gerudo Membership Card. |
| Room for Riches | Obtain the Giant’s Wallet. |
| Gold Hunter · 1 | Collect 1 Gold Skulltula token. |
| Gold Hunter · 10 | Collect 10 Gold Skulltula tokens. |
| Gold Hunter · 30 | Collect 30 Gold Skulltula tokens. |
| Gold Hunter · 50 | Collect 50 Gold Skulltula tokens. |
| Curse Breaker | Collect 100 Gold Skulltula tokens. |
| 10 Hearts Strong | Reach 10 heart containers of maximum health. |
| 20 Hearts Strong | Reach 20 heart containers of maximum health. |
| The Spiritual Stones | Obtain all three Spiritual Stones. |
| Awakening the Sages | Obtain all six medallions. |
| Hyrule’s Songbook | Learn all twelve main ocarina songs. |
| Gifts of the Goddesses | Obtain Din’s Fire, Farore’s Wind and Nayru’s Love. |
