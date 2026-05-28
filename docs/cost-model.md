# Cost model — owned hardware vs rented inference, 12 and 36 months

The choice is not really *cloud vs on-prem*; for an air-gapped brief
like Vantage's, the cloud option is foreclosed by the security review.
The real question is *which on-prem investment*. This page lays out
two operating shapes and the line each year falls on.

All numbers below are illustrative — they reflect the design targets
and order-of-magnitude inputs an enterprise procurement team would
expect, not a binding quote.

## Operating shape A — the brief's setup, one workstation per office hub

| Line item | Year 0 | Year 1 | Year 2 |
|---|---|---|---|
| RTX 3060 workstation (CapEx, amortised over 3 yr) | $1,800 / yr | $1,800 / yr | $1,800 / yr |
| Power (worst-case 350 W × 60 % duty × 24 × 365 × $0.18/kWh) | $330 | $330 | $330 |
| Operator time (1 FTE × 5 % effort × $150 k loaded) | $7,500 | $7,500 | $7,500 |
| Storage (NAS amortised; 4 TB delta @ $0.05/GB·yr) | $200 | $200 | $200 |
| Software (OSS only) | $0 | $0 | $0 |
| **Total per hub per year** | **≈ $9,830** | **≈ $9,830** | **≈ $9,830** |
| Per query (target 50 000 queries/yr/hub) | $0.20 | $0.20 | $0.20 |

This is the as-designed shape. Replicated across N hubs, the total
scales linearly.

## Operating shape B — central GPU server replaces the hubs

The procurement narrative says "buy one bigger server, route all
queries to it, retire the per-hub workstations." The math:

| Line item | Year 0 | Year 1 | Year 2 |
|---|---|---|---|
| L40S / A100-class server (CapEx, 3 yr) | $14,000 / yr | $14,000 / yr | $14,000 / yr |
| Server power (650 W × 80 % × 24 × 365 × $0.18) | $820 | $820 | $820 |
| Internal network upgrade (one-time, amortised) | $4,000 / 3 yr | — | — |
| Operator time (1 FTE × 25 % effort) | $37,500 | $37,500 | $37,500 |
| **Total** | **≈ $53,650** | **≈ $52,320** | **≈ $52,320** |

Server shape is cheaper than a hub fleet only when there are **5+
hubs**, and only if the network upgrade is not blocked by the
air-gap. For three hubs it is roughly cost-neutral and adds a
single-point-of-failure exposure the workstations avoid.

## What rented inference would have cost (had the air-gap allowed it)

Indicative API-priced equivalents — the numbers are here so the
"on-prem vs cloud" line can be drawn even though the policy already
chose for us:

| Service | $/1k tokens (Aug-25 reference rate) | $/year @ 50k queries/hub × 1.5k tokens |
|---|---|---|
| GPT-4o-mini | input $0.15 · output $0.60 | $560 / hub |
| Claude 3.5 Haiku | input $0.80 · output $4.00 | $3,000 / hub |
| Embedding (OpenAI text-embedding-3-small) | $0.02 / M | $5 / hub |

Pure inference is cheap; what makes the cloud option expensive isn't
the API meter, it's the compliance overhead (data-processing
agreements, transit auditing, vendor risk reviews) that an
air-gapped on-prem build sidesteps.

## Break-even reasoning

The owned-hardware shape A wins on two axes the spreadsheet alone
doesn't capture:

- **Air-gap compliance is built in.** No counterfactual to argue.
- **Tail latency is local.** The shape-A query never crosses an
  internal network; the shape-B query does (even within the firewall).

The CapEx shape A asks for is modest enough that *the right way to
read this table is not "which is cheapest"* but "which is
defensible to procurement, legal, and the operator on call at 02:00."
Shape A is defensible to all three; shape B requires a network
upgrade and a single-point-of-failure conversation neither legal
nor ops want to have.
