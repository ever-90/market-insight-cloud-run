# Stripe Subscription Spec (Phase 3.6 — pre-implementation)

> Not yet implemented. Spec only.

## Plans

| Plan | Price (KRW/mo) | Searches/month | Brand mappings | Snapshots retention | API key |
|---|---|---|---|---|---|
| Free | 0 | 50 | 5 | 3 months | ❌ |
| Pro | 29,000 | 1,000 | 50 | 12 months | ✅ (1 key) |
| Team | 99,000 | 10,000 | 500 | 24 months | ✅ (5 keys) |
| Enterprise | contact | custom | unlimited | unlimited | ✅ unlimited |

## Stripe objects

- **Product** "Market Insight" with three Prices (free is gate-only, no Stripe Price needed).
- **Customer** ↔ Firestore `users/{user_id}.stripe_customer_id`.
- **Subscription** webhook → updates `users/{user_id}.plan` + `users/{user_id}.usage_quota`.

## Webhook events handled

- `checkout.session.completed` → activate plan
- `invoice.paid` → reset monthly usage counter
- `invoice.payment_failed` → notify user, downgrade after 7 days
- `customer.subscription.deleted` → revert to Free
- `customer.subscription.updated` → adjust quota

## Quota enforcement

Middleware reads `users/{user_id}.usage_quota.searches_this_month` before each
`/api/search` call. Exceeded → 429 with `Retry-After` set to month rollover.

## Endpoints to add

- `POST /api/billing/create-checkout-session` → returns Stripe Checkout URL
- `POST /api/billing/portal` → returns Stripe Customer Portal URL
- `POST /api/billing/webhook` → Stripe signature verification + event dispatch

## Tax & invoicing

- Korean VAT (10%) — Stripe Tax handles automatically when shipping address is set.
- Invoice PDF emailed via Stripe; archive copy uploaded to `gs://${PROJECT_ID}-invoices`.

## Out of scope

- Custom enterprise contracts (handled offline)
- Annual prepay discount (Phase 3.7)
- Usage-based overage billing (Phase 3.7)
