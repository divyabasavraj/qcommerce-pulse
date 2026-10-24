# Theme labels vs hand labels: `llm_labels_qwen2.5-7b-v2.csv`

_Generated 2026-10-24 on 300 hand-labelled reviews._

**Macro-F1:** 0.66 (95% CI 0.59–0.71) · **Exact match (all themes right):** 72% · **At least one theme right:** 85%

| theme | support | precision | recall | f1 |
|---|---|---|---|---|
| delivery_delay | 45 | 0.88 | 0.62 | 0.73 |
| missing_wrong_item | 9 | 0.50 | 0.67 | 0.57 |
| quality_expiry | 37 | 0.92 | 0.59 | 0.72 |
| refund_support | 36 | 0.63 | 0.86 | 0.73 |
| pricing_fees | 36 | 0.74 | 0.81 | 0.77 |
| app_payment_bug | 12 | 0.33 | 0.33 | 0.33 |
| partner_behaviour | 11 | 0.46 | 0.55 | 0.50 |
| availability_stock | 15 | 0.70 | 0.47 | 0.56 |
| positive | 113 | 0.96 | 0.96 | 0.96 |
| other | 42 | 0.71 | 0.69 | 0.70 |

## Disagreements (first 15)

| text | hand | model |
|---|---|---|
| koi mat lo bhai online saman ye log kharab saman deke vapas bhi nhi lete hai or na ki apke | quality_expiry, refund_support | refund_support |
| not customer care support | other | refund_support |
| worldest worst app worst experience ... sabse bekar hai enki ghatiyaa delivery wale log ji | delivery_delay, app_payment_bug | delivery_delay, refund_support |
| sevice is good but handling charges not good | pricing_fees, positive | pricing_fees |
| Everything is awesome and I like the regular flat off coupons which are given to the custo | positive | pricing_fees |
| I ordered a product from Blinkit, but due to an address mistake, I canceled the order shor | delivery_delay, refund_support | refund_support |
| WORST PACKING | quality_expiry | other |
| received a damaged product, NO one taking the responsibility, my first order became the la | quality_expiry | quality_expiry, refund_support |
| worst packaging and worst customer support ever. AI support is completely useless and take | quality_expiry, refund_support | refund_support, app_payment_bug |
| worst experience many times I have faced even my friends also some products wht they issui | quality_expiry, refund_support | quality_expiry |
| zepto punish customer for the order, not delivered from zepto side, by disabling cash on d | delivery_delay | delivery_delay, pricing_fees |
| pathetic customer service, no one to listen to, it's there wishlist when to deliver the or | delivery_delay, refund_support | refund_support |
| Hey, just a heads-up, your order will be canceled even if it says you have 5 minutes to or | delivery_delay, pricing_fees | delivery_delay |
| fake messages of money in your wallet 🙄 | pricing_fees | other |
| worst app and worst experience | delivery_delay, refund_support, availability_stock | other |
