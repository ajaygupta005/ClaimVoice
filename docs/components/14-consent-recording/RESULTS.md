# Component 14 - State-Aware Consent + Encrypted Recording - Results

## Checklist

- [ ] `getStateFromPhone('+12125551234')` returns `NY`.
- [ ] `requiresTwoPartyConsent('+14155550100')` returns `true`.
- [ ] Crypto round trip recovers plaintext.
- [ ] Wrong key fails decryption (auth tag check).

## Commit

```
git add services/telephony/src/recording/ \
        services/telephony/package.json \
        services/telephony/tests/unit/state_lookup.test.ts \
        services/telephony/tests/unit/crypto.test.ts \
        docs/components/14-consent-recording/

git commit -m "feat(telephony): state-aware consent and encrypted recording"
```

## Notes
-

