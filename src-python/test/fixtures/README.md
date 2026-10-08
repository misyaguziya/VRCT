# Legacy audio contract fixtures

legacy_audio_contracts.json was generated once from the pinned fork and synthetic inputs. Provenance contains the fork commit and source SHA256. No package code is vendored, devices opened, or requests sent. Energy cases retain PCM SHA256/length, per-chunk energy, read count, threshold and action; PCM and speaker cases retain exact bytes. Tests no longer import the old package. Input construction remains independently specified in test_audio_listener.py and test_pcm_audio.py.
