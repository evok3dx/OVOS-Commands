# V4 weather correctness and timing check

The owner accepts the final music timing. This small follow-up corrects the
exact pinned weather skill's named-city forecast coordinates and the false
five-minute Media handler timeout. It adds stage/provider timing logs to find
the weather delay; a latency improvement has not yet been demonstrated.
The existing frozen runtime, models, owner preferences and native IP policy
are preserved. World-time routing and Wikipedia/WikiHow online answers are
deferred to a future release at the owner's request.

Source validation is recorded in [releases](releases.md). The published rc2
archive/tag is unchanged; this handover is for the existing patched, isolated
laptop only. It rejects unknown source hashes and running workers before any
mutation, backs up privately in Downloads, writes four reviewed source files
atomically and registers only Media 0.3.4 using existing local tooling with no
index/dependency resolution. Any registration failure restores prior source
and attempts original registration. The dispatcher version label stays as it is.

Stop Jarvis in the Control Centre, close the Control Centre, and run:

```bash
(
  set -e
  test "$(id -u)" -ne 0
  mkdir -p "$HOME/Downloads"
  jarvis_weather_dir="$(mktemp -d "$HOME/Downloads/jarvis-v4-weather.XXXXXX")"
  curl --fail --location --proto '=https' --proto-redir '=https' \
    'https://raw.githubusercontent.com/evok3dx/OVOS-Commands/b20302fa9d334f86ba9b366b47f5dbfa81b2406a/scripts/apply-v4-weather-fix.py' \
    -o "$jarvis_weather_dir/apply-v4-weather-fix.py"
  printf '%s  %s\n' \
    'c9e814e47f36e22adb1d8eff9a12288c19491bb656b78c679324aff31e5500c7' \
    "$jarvis_weather_dir/apply-v4-weather-fix.py" | sha256sum --check
  "$HOME/.venvs/ovos/bin/python" -I "$jarvis_weather_dir/apply-v4-weather-fix.py"
)
```

Reopen the Control Centre and choose Run Jarvis.

Ask for Sydney weather, then New York weather, and repeat one of those cities.
Collect only the relevant fixed-worker logs:

```bash
journalctl --system \
  -u "jarvis-v4-$(id -u)-weather.service" \
  -u "jarvis-v4-$(id -u)-core.service" \
  -u "jarvis-v4-$(id -u)-audio.service" \
  --since '10 minutes ago' --no-pager -o short-iso-precise |
  grep -E 'Weather .*stage:|Weather provider|Parsing utterance|handle_utterance.*match|Speak:|retrieving weather|Weather API failure'
```

The timings identify city lookup, forecast, display and speech submission
separately. The provider records name only the reviewed operation; they omit
queries and coordinates. Existing core/audio logs can contain spoken city
names, so keep collected logs private. A correct forecast need not differ from
another city's conditions by chance; use the coordinate regression and stage
logs, not an expectation that every answer must have different numbers.

Test one song as well. The acknowledgement remains queued before lookup,
without waiting for its full TTS playback. The accepted pacing is unchanged.
