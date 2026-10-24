# Theme labels vs hand labels: `llm_labels_qwen2.5-7b.csv`

_Generated 2026-10-24 on 300 hand-labelled reviews._

**Macro-F1:** 0.62 (95% CI 0.56–0.67) · **Exact match (all themes right):** 67% · **At least one theme right:** 82%

| theme | support | precision | recall | f1 |
|---|---|---|---|---|
| delivery_delay | 53 | 0.87 | 0.49 | 0.63 |
| missing_wrong_item | 8 | 0.33 | 0.62 | 0.43 |
| quality_expiry | 37 | 0.92 | 0.62 | 0.74 |
| refund_support | 36 | 0.59 | 0.83 | 0.69 |
| pricing_fees | 37 | 0.92 | 0.65 | 0.76 |
| app_payment_bug | 12 | 0.23 | 0.42 | 0.29 |
| partner_behaviour | 11 | 0.40 | 0.73 | 0.52 |
| availability_stock | 15 | 0.54 | 0.47 | 0.50 |
| positive | 113 | 0.96 | 0.92 | 0.94 |
| other | 42 | 0.62 | 0.71 | 0.67 |

## Disagreements (first 15)

| text | hand | model |
|---|---|---|
| koi mat lo bhai online saman ye log kharab saman deke vapas bhi nhi lete hai or na ki apke | delivery_delay, quality_expiry, refund_support | missing_wrong_item, refund_support |
| not customer care support | other | refund_support |
| plz apply COD 4 all customers | pricing_fees | app_payment_bug |
| worldest worst app worst experience ... sabse bekar hai enki ghatiyaa delivery wale log ji | delivery_delay, app_payment_bug | delivery_delay, refund_support, partner_behaviour |
| sevice is good but handling charges not good | pricing_fees, positive | pricing_fees |
| Everything is awesome and I like the regular flat off coupons which are given to the custo | positive | pricing_fees |
| I ordered a product from Blinkit, but due to an address mistake, I canceled the order shor | delivery_delay, refund_support | refund_support |
| WORST PACKING | quality_expiry | other |
| received a damaged product, NO one taking the responsibility, my first order became the la | quality_expiry | quality_expiry, refund_support |
| worst packaging and worst customer support ever. AI support is completely useless and take | quality_expiry, refund_support | refund_support, app_payment_bug |
| worst experience many times I have faced even my friends also some products wht they issui | quality_expiry, refund_support | missing_wrong_item, quality_expiry |
| sabse ghatiya customer service 2 hours me deliver karte hai 4 min bolke. | delivery_delay | delivery_delay, refund_support |
| zepto punish customer for the order, not delivered from zepto side, by disabling cash on d | delivery_delay | delivery_delay, app_payment_bug |
| pathetic customer service, no one to listen to, it's there wishlist when to deliver the or | delivery_delay, refund_support | refund_support |
| Hey, just a heads-up, your order will be canceled even if it says you have 5 minutes to or | delivery_delay, pricing_fees | availability_stock |
