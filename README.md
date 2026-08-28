# ha-sharp-cocoro

Homeassistant integration for Sharp Cocoro Air (Sharp Aircon)

![aircon](./aircon.png)

Super WIP

> **This is a fork.** It tracks [dvcrn/ha-sharp-cocoro](https://github.com/dvcrn/ha-sharp-cocoro)
> and adds three things on top of it: commands that no longer block Home
> Assistant for ten seconds, recovery when the cloud token expires mid-command,
> and entities for the ion and eco properties. Everything in
> [CHANGELOG.md](./CHANGELOG.md) under *Fork changes* is not in upstream.
> The changes are on the `local-changes` branch, rebased on upstream `main`.

## What's working

Will try to load supported devices from Sharp Cocoro Air API and configure them

Currently supported device types:

- Aircon

Entities this fork adds, per device, and only when the device actually reports
the underlying property:

| Entity | Property | Why this platform |
| --- | --- | --- |
| `switch.<device>_ion` | `CF` (空気清浄モード設定) | Honoured in both directions, so a real switch |
| `binary_sensor.<device>_eco` | `8F` (節電動作設定) | Read-only: writing 41 to engage it returns HTTP 200 and is then ignored |
| `button.<device>_cancel_eco` | `8F` | Cancelling is the one direction the unit does apply |

Half the properties a unit advertises as settable read `null` and silently
discard writes, so these entities are created from a *reported value* rather
than from the descriptor's `set: true` flag.

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dvcrn&repository=ha-sharp-cocoro&category=integration)

You can also install manually by copying the `custom_components` from this repository into your Home Assistant installation.


## Authentication

Check README of https://github.com/dvcrn/sharp-cocoro

**Sharp appliances sold in Egypt (El Araby) are a different service** —
`serviceName` is `sharp-egy`, and the account login is El Araby's own Azure AD
B2C tenant rather than Sharp's. None of that is documented anywhere else, and
several of its failure responses mean something other than what they say, so it
has its own guide:

- **[Connecting a Sharp air conditioner in Egypt (El Araby)](./docs/egypt-el-araby.md)**

The short version, if you only read one thing: `app_key` is not a secret to go
and find, it is minted per installation — and **binding a freshly minted one does
not pair it to your appliances**, so a new key can authenticate perfectly and
still stop the integration from loading. If you already have a key that works,
keep it.

## Ignoring devices you do not want polled

Every device refresh is a **write** -- it commands the device to report itself.
An account that holds a unit at another address, whose entities are all disabled
in Home Assistant, still gets a control sent to it on every cycle, and those
failures dominated this integration's error rate before the list existed.

Give it a list of device ids to leave alone, either as `ignored_device_ids` in
the config entry's options, or as a JSON array in
`<config>/sharp_cocoro_ignored_devices.json`:

```json
["1234567", "2345678"]
```

The default is to ignore nothing, so an installation that needs none behaves
exactly as upstream. The symptom that tells you a device belongs on the list is
a log line reading `Failed to request refresh for device <id>` repeating every
cycle.

## Timings this fork changes

| | Upstream | Here | Why |
| --- | --- | --- | --- |
| Control confirmation | awaited in the service call | background task | Six timed calls blocked 9.0-11.7 s each; the optimistic state is already written |
| Confirmation timeout | 5 s | 30 s | The unit answers through the cloud and regularly needs longer, so 5 s reported failure on commands that worked |
| Device refresh | 60 s | 180 s | Each refresh is a control command; at 60 s per device roughly half failed. Room temperature moves a degree over several minutes |
| Token refresh | 30 min | 5 min | On some tenants the account token lives only minutes, and one expiring mid-command looks exactly like a command the unit ignored |
