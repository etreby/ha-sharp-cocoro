# Changelog

Notable changes to this fork. Upstream releases are listed for context, so it is
clear what this fork is based on and what it adds.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Upstream is [dvcrn/ha-sharp-cocoro](https://github.com/dvcrn/ha-sharp-cocoro).

## Fork changes — `local-changes`, rebased on upstream `main` (1.3.3)

Everything in this section is in this fork only.

### Added

- `switch.<device>_ion` for property `CF` (空気清浄モード設定). A real switch:
  `CF` is honoured in both directions, verified by writing both values and
  watching the unit's indicator go out and come back, then through the entity
  itself — off in 8 s, on in 16 s, with the service call returning in 2.9 s.
- `binary_sensor.<device>_eco` for property `8F` (節電動作設定), read-only on
  purpose. Writing `41` to engage eco returns HTTP 200 with a control id and a
  null `errorCode`, then does nothing — five times over — so a switch here would
  silently fail to turn on.
- `button.<device>_cancel_eco`, because cancelling is the one direction the unit
  does apply. It checks the current value first rather than sending a write the
  unit may refuse.
- An optional device ignore list, read from the config entry's
  `ignored_device_ids` option or from `<config>/sharp_cocoro_ignored_devices.json`.
  A device refresh is a **write**, so a unit whose entities are all disabled in
  Home Assistant was still being sent a control on every cycle. Defaults to
  ignoring nothing, so behaviour is unchanged where it is not configured.

### Changed

- **Commands no longer block Home Assistant.** `execute_and_refresh` awaited the
  cloud confirmation and the follow-up refresh inside the service call, so every
  command blocked for as long as the cloud took to answer — six timed calls
  measured at 11.7, 10.1, 9.9, 9.7, 9.5 and 9.0 s. The optimistic state is
  already written before that point, so the confirmation now runs as a background
  task and the frontend reacts immediately.
- Control confirmation timeout 5 s → 30 s, poll 0.5 s → 1 s. The unit answers
  through the cloud and regularly needs longer than five seconds, so the old
  timeout reported failure on commands that had in fact worked.
- Device refresh interval 60 s → 180 s. Every refresh is a control command; at
  60 s per device roughly half of them failed. Room temperature moves a degree
  over several minutes, so nothing readable is lost.
- `TOKEN_REFRESH_INTERVAL` 30 min → 5 min. On some tenants the account token
  lives only minutes, and a token expiring mid-command is indistinguishable from
  a command the unit ignored.
- Entity naming: `_attr_name` on the new entities is the bare noun. With
  `has_entity_name`, Home Assistant prefixes the device name itself, so passing
  the device name again — as the existing platform files do — produces a doubled
  name like `Living Room AC Living room Eco`.

### Fixed

- A `401` raised while waiting for a control confirmation now triggers a
  re-login. The existing recovery covered `execute_queued_updates` only, so a
  token expiring between a command and its confirmation left the command
  unconfirmed, which looks exactly like a command the unit ignored.

### Notes for anyone reading this fork

- Entities are created from a property's *reported value*, never from the
  descriptor's `set: true` flag. On the unit tested, twelve of nineteen
  advertised-settable properties read `null` and discard writes.
- A `terminalAppId` (the `app_key`) can only read the boxes it is **paired** to.
  `setting/boxInfo/` returns every box on the account regardless of pairing, so
  an unpaired box appears in the list and then answers `400` with an empty body
  to everything — an authorisation failure wearing the wrong status code. Since
  device enumeration raises on the first unreadable box, a key paired to only
  some boxes makes the whole integration fail to load. Use a key paired to all
  of them, or put the others on the ignore list above.

## Upstream releases

### 1.3.3 — 2026-08-26

- Fixed a `KeyError` for config entries missing `service_name`, which now falls
  back to `iClub`.

### Unreleased upstream work included in 1.3.3

- Multiple-device support and a reworked configuration flow.
- Humidity and power sensors; stricter temperature and humidity validation.
- `special_status` returns `Normal` for a null code.
- Device refresh reworked to use `execute_queued_updates`.
- Discovery fix (upstream PR #3).

### 1.3.2 / 1.3.1 / 1.3 — 2025-06-27

- Property value caching fix; dependency bump to `sharp-cocoro>=0.2.3`; waiting
  for state change on resolve.
