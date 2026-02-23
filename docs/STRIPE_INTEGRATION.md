# Stripe Connect & Invoicing – Requirements and Implementation

This document describes the Stripe requirements and how the Stripe Connect + Invoicing integration is implemented so that each user can generate shareable invoice payment links and receive payments to their own Stripe account.

---

## 1. Stripe requirements

### 1.1 What you need from Stripe

| Requirement | Description |
|-------------|-------------|
| **Stripe account** | A single **platform** Stripe account (yours). All API calls use this account’s secret key. |
| **Stripe Connect** | Connect must be enabled so you can create **connected accounts** (one per app user). |
| **Secret key** | From Dashboard → Developers → API keys. Used for creating Connect accounts, AccountLinks, and creating invoices on connected accounts. |
| **Webhook signing secret** | From Dashboard → Developers → Webhooks. Used to verify that incoming webhook events are from Stripe. |

### 1.2 Stripe Connect model

- **Platform account**: Your Stripe account (holds the API keys).
- **Connected accounts**: One **Express** account per app user. Created via `Account.create(type="express", ...)`. Users complete onboarding via Stripe’s hosted flow (AccountLink).
- **Payments**: Invoices are created on the **connected account** (Direct Charges). Money goes to the user’s connected account, not the platform.

### 1.3 Supported flows

- **Connect onboarding**: Express account + AccountLink; user is redirected to Stripe to complete identity/bank details.
- **Invoicing**: Create Customer and Invoice on the connected account, finalize, return `hosted_invoice_url` so the user can share a link; customer pays on Stripe’s hosted invoice page.
- **Webhooks**: `invoice.paid` (and optionally `invoice.payment_failed`) to update app invoice status.

---

## 2. Environment variables

Set these in `.env` (or your deployment config):

```bash
# Required for Stripe Connect and Invoicing
STRIPE_SECRET_KEY=sk_live_...   # or sk_test_... for test mode
STRIPE_WEBHOOK_SECRET=whsec_... # from the webhook endpoint in Dashboard

# Used for Connect return/refresh URLs (optional; defaults to http://localhost:3000)
FRONTEND_URL=https://your-app.com
```

- **STRIPE_SECRET_KEY**: Secret key from Developers → API keys. Never expose this to the frontend.
- **STRIPE_WEBHOOK_SECRET**: Signing secret for the webhook endpoint that receives `invoice.paid` (and optionally other events). Create the endpoint in Developers → Webhooks and copy the “Signing secret”.
- **FRONTEND_URL**: Base URL of your frontend. Used to build `return_url` and `refresh_url` for Connect AccountLinks (e.g. `{FRONTEND_URL}/invoices`).

---

## 3. Stripe Dashboard setup

### 3.1 Enable Connect

1. Log in to [Stripe Dashboard](https://dashboard.stripe.com).
2. Go to **Connect → Settings** (or **Settings → Connect**).
3. Enable **Connect** and complete any required configuration.
4. Choose **Express** (or Standard) as the connected account type; the code uses **Express** and AccountLinks.

### 3.2 Create webhook endpoint

1. Go to **Developers → Webhooks**.
2. **Add endpoint**.
3. **Endpoint URL**: `https://your-api-domain.com/api/v1/revenue/webhooks/stripe` (must be HTTPS in production).
4. **Events to send**: at minimum select **invoice.paid**. Optionally add **invoice.payment_failed** and Connect events (e.g. **account.updated**) if you want to sync more state.
5. After creating the endpoint, open it and reveal the **Signing secret** (`whsec_...`). Set it as `STRIPE_WEBHOOK_SECRET`.

### 3.3 Test mode

Use **Test mode** (toggle in Dashboard) and test keys (`sk_test_...`, `whsec_...` from a test webhook) for development. Use test cards (e.g. `4242 4242 4242 4242`) to trigger `invoice.paid` without moving real money.

---

## 4. Implementation overview

### 4.1 Data model

| Location | Field | Purpose |
|----------|--------|---------|
| **User** | `stripe_connect_account_id` | Stripe Connect account id (`acct_...`) for this user. |
| **User** | `stripe_connect_onboarding_complete` | Whether the user has completed Connect onboarding (`details_submitted`). |
| **Invoice** | `stripe_invoice_id` | Stripe Invoice id when the invoice has been “published” for payment. |
| **Invoice** | `stripe_hosted_url` | Shareable URL of the Stripe hosted invoice page. |

Migration: `alembic/versions/026_stripe_connect_and_invoice_stripe_fields.py`.

### 4.2 Backend modules

| File | Role |
|------|------|
| `app/core/config.py` | `stripe_secret_key`, `stripe_webhook_secret` (and `frontend_url` for Connect URLs). |
| `app/modules/revenue/stripe_connect.py` | Create Connect Express account, create AccountLink, retrieve account details for onboarding status. |
| `app/modules/revenue/stripe_invoice.py` | Create Stripe Customer and Invoice on a connected account (Direct Charges), finalize, return `hosted_invoice_url`. |
| `app/modules/revenue/routes.py` | Connect endpoints, publish-invoice endpoint, webhook endpoint. |

### 4.3 API endpoints

All under prefix `/api/v1/revenue`. Authenticated endpoints use the usual auth (e.g. JWT); the webhook does not.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/connect/onboarding-link` | Yes | Returns `{ url }` to redirect the user to Stripe Connect onboarding. Creates an Express account if the user doesn’t have one. |
| `GET`  | `/connect/status` | Yes | Returns `{ connected, onboarding_complete }`. Refreshes from Stripe and updates `stripe_connect_onboarding_complete` when `details_submitted` is true. |
| `POST` | `/invoices/{invoice_id}/publish` | Yes | Creates Stripe invoice on the **invoice owner’s** connected account (pack owner). Returns `{ payment_link, stripe_invoice_id }`. Saves `stripe_invoice_id` and `stripe_hosted_url` on the app Invoice and sets status to `sent`. |
| `POST` | `/webhooks/stripe` | No (signature only) | Receives Stripe events. Verifies `Stripe-Signature` with `STRIPE_WEBHOOK_SECRET`. On `invoice.paid`, finds the app Invoice by `stripe_invoice_id` and sets status to `paid`. |

### 4.4 Flow: user gets a payment link

1. **User connects Stripe**  
   Frontend calls `POST /connect/onboarding-link`, gets `url`, redirects the user to it. User completes Stripe’s onboarding. On return, frontend can call `GET /connect/status` to confirm `onboarding_complete`.

2. **User creates an invoice (draft)**  
   Existing flow: create an Invoice in the app (pack, amount, currency, due date, optional client).

3. **User publishes the invoice**  
   Frontend calls `POST /invoices/{invoice_id}/publish`:
   - Backend resolves invoice → pack → pack owner (User).
   - Ensures that user has `stripe_connect_account_id` and `stripe_connect_onboarding_complete`; otherwise returns an error (e.g. “Connect your Stripe account in Settings”).
   - If the invoice already has `stripe_hosted_url`, returns it (no duplicate Stripe invoice).
   - Otherwise calls `create_invoice_on_connected_account(owner.stripe_connect_account_id, invoice, client_email, client_name)` which:
     - Creates a Stripe Customer on the connected account.
     - Creates an InvoiceItem and Invoice, optionally sets due date, finalizes the invoice.
     - Returns Stripe’s `hosted_invoice_url`.
   - Backend saves `stripe_invoice_id` and `stripe_hosted_url` on the app Invoice and sets status to `sent`.
   - Response includes `payment_link` (and `stripe_invoice_id`).

4. **User shares the link**  
   User copies/opens `payment_link`. Customer pays on Stripe’s hosted page. Money goes to the **connected account** (the pack owner).

5. **Status update when paid**  
   Stripe sends `invoice.paid` to `POST /webhooks/stripe`. Backend finds the app Invoice by `stripe_invoice_id` and sets status to `paid`.

### 4.5 Frontend usage

- **Settings**: “Stripe Connect” card calls `getConnectStatus()` and, if not connected, “Connect Stripe” calls `createConnectOnboardingLink()` and redirects to the returned URL. After return, “Connect Stripe” in Settings shows connected/onboarding status.
- **Invoices**: For each invoice, “Manage” opens a dialog. If the user has completed Connect onboarding, “Get payment link” calls `publishInvoice(invoiceId)` and then shows “Copy link” / “Open link”. If the invoice already has a payment link, the dialog shows “Copy link” / “Open link” only. If Connect is not complete, the dialog shows a message with a link to Settings to connect Stripe.

---

## 5. Security and idempotency

- **Webhook**: The webhook handler does not use session/JWT auth. It relies on `Stripe-Signature` and `STRIPE_WEBHOOK_SECRET` via `stripe.Webhook.construct_event(body, signature, secret)`. Invalid or missing signature should return 4xx.
- **Publish**: Only the invoice owner (pack owner) can have a payment link created; the backend resolves the owner and uses their `stripe_connect_account_id`. If the caller does not have access to the invoice (via pack access), they get 404 before any Stripe call.
- **Idempotency**: If the app Invoice already has `stripe_hosted_url`, the publish endpoint returns that URL without creating a new Stripe invoice.

---

## 6. Testing checklist

- [ ] Set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` (test keys and test webhook).
- [ ] Run migration: `alembic upgrade head`.
- [ ] Connect onboarding: Click “Connect Stripe” in Settings, complete Stripe’s flow, return to app; confirm “Stripe connected” and `GET /connect/status` returns `onboarding_complete: true`.
- [ ] Create a draft invoice (existing flow), then “Get payment link”. Confirm a Stripe hosted URL is returned and saved.
- [ ] Open the payment link in a new tab, pay with test card `4242 4242 4242 4242`. Confirm webhook fires and the app invoice status becomes `paid` (may need to refresh or re-fetch invoices).
- [ ] (Optional) Use Stripe CLI to forward webhooks locally: `stripe listen --forward-to localhost:8000/api/v1/revenue/webhooks/stripe` and use the printed `whsec_...` as `STRIPE_WEBHOOK_SECRET` for local testing.

---

## 7. References

- [Stripe Connect – Connect Express](https://docs.stripe.com/connect/express-accounts)
- [Stripe Connect – AccountLinks](https://docs.stripe.com/api/account_links)
- [Stripe Invoicing – Create and finalize](https://docs.stripe.com/invoicing/integration/create-invoice)
- [Stripe Connect – Making requests on behalf of connected accounts](https://docs.stripe.com/connect/authentication#direct-charges) (Direct Charges via `stripe_account=...`)
- [Stripe Webhooks – Receiving events](https://docs.stripe.com/webhooks)
