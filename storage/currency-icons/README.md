# Currency icons

`<code>.svg`, lower-case currency code. `currencies.icon` stores the key
`currency-icons/<code>.svg`; the API serves it at `/api/v1/storage/<key>`, or under
`STORAGE__PUBLIC_URL` when that points at a CDN or bucket.

- Fiat: the issuing country's square flag from [flag-icons](https://github.com/lipis/flag-icons)
  7.2.3 (MIT). EUR uses the EU flag, XAF/XOF/XCD/XPF a member state's.
- Crypto: [cryptocurrency-icons](https://github.com/spothq/cryptocurrency-icons) 0.18.1 (CC0),
  colour set.

Add a currency's icon here under its code and the seed picks it up.
