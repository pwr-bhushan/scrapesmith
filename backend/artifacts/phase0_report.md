# Heal Bench Report

## Summary

- **healed_rate**: 91.67% — anchor-correct **and** accepted by `post_check`. Headline: what would ship.
- **anchor_correct_rate**: 91.67% — the model got the right value.
- **resolve_but_wrong_rate**: 2.08% — guard: a rise here counts as a regression even if `healed_rate` also rises.
- **no_proposal_rate**: 0.00% (provider omitted or proposal rejected)

## Per-Provider

| | healed | anchor-correct | resolve-but-wrong | n |
|---|---|---|---|---|
| ollama/qwen2.5-coder:7b | 91.67% | 91.67% | 2.08% | 48 |

## Per Drift Type

| | healed | anchor-correct | resolve-but-wrong | n |
|---|---|---|---|---|
| attr_strip | 100.00% | 100.00% | 0.00% | 7 |
| class_rename | 100.00% | 100.00% | 0.00% | 12 |
| combo | 91.67% | 91.67% | 8.33% | 12 |
| tag_swap | 80.00% | 80.00% | 0.00% | 10 |
| unlabelled | 100.00% | 100.00% | 0.00% | 2 |
| wrapper_insert | 80.00% | 80.00% | 0.00% | 5 |

## Field Results

| Case | Field | Drift | Correct | Gate | DQ | Selector |
|---|---|---|---|---|---|---|
| amazon_product | price | unlabelled | YES | healed | ok | `css=.a-price-whole` |
| amazon_product | title | unlabelled | YES | healed | ok | `css=.pdp-product-name` |
| article__attr_strip | headline | attr_strip | YES | healed | ok | `css=article.story h1.headline` |
| article__class_rename | headline | class_rename | YES | healed | ok | `css=h1.cef98-headline` |
| article__class_rename | author | class_rename | YES | healed | ok | `css=.c473a-author[itemprop='author']` |
| article__class_rename | read_minutes | class_rename | YES | healed | ok | `css=span.c640f-minutes` |
| article__combo | headline | combo | YES | healed | ok | `css=.cef98-headline` |
| article__combo | author | combo | YES | healed | ok | `css=.c473a-author[itemprop='author']` |
| article__combo | read_minutes | combo | YES | healed | ok | `css=.c640f-minutes` |
| article__tag_swap | headline | tag_swap | YES | healed | ok | `css=h2.headline` |
| article__tag_swap | author | tag_swap | NO | still_broken | empty | `xpath=//span[@itemprop='author']` |
| article__tag_swap | read_minutes | tag_swap | YES | healed | ok | `xpath=//div[@class='minutes']` |
| article__wrapper_insert | headline | wrapper_insert | YES | healed | ok | `css=article#story .layout-slot > h1.headline` |
| article__wrapper_insert | read_minutes | wrapper_insert | YES | healed | ok | `css=div.read-time .layout-slot > span.minutes` |
| event__attr_strip | event_name | attr_strip | YES | healed | ok | `css=.event-detail h1.event-name` |
| event__attr_strip | ticket_price | attr_strip | YES | healed | ok | `css=.ticket-block .ticket-price` |
| event__class_rename | event_name | class_rename | YES | healed | ok | `css=.c6e59-name` |
| event__class_rename | venue | class_rename | YES | healed | ok | `css=.c8733-name` |
| event__class_rename | ticket_price | class_rename | YES | healed | ok | `css=.c53f1-price` |
| event__combo | event_name | combo | YES | healed | ok | `css=section.cf04a-hero h2.c6e59-name` |
| event__combo | venue | combo | YES | healed | ok | `css=section.c55ac-block div.c8733-name` |
| event__combo | ticket_price | combo | YES | healed | ok | `css=section.c2940-block section.ce928-slot div.c53f1-price` |
| event__tag_swap | event_name | tag_swap | YES | healed | ok | `css=h2.event-name` |
| event__tag_swap | venue | tag_swap | NO | still_broken | empty | `css=div.venue-block > div.venue-name` |
| event__wrapper_insert | venue | wrapper_insert | NO | still_broken | empty | `css=div.venue-block > span.venue-name` |
| job__attr_strip | job_title | attr_strip | YES | healed | ok | `css=.posting-title` |
| job__attr_strip | salary | attr_strip | YES | healed | ok | `xpath=//div[@class='compensation']//span[@class='salary-range']` |
| job__class_rename | job_title | class_rename | YES | healed | ok | `css=h1.cc382-title` |
| job__class_rename | company | class_rename | YES | healed | ok | `css=span.ce3ab-name` |
| job__class_rename | salary | class_rename | YES | healed | ok | `css=.c9d0f-range[data-salary-min]` |
| job__combo | job_title | combo | YES | healed | ok | `css=.cc382-title` |
| job__combo | company | combo | YES | healed | ok | `css=.ce3ab-name` |
| job__combo | salary | combo | YES | healed | ok | `css=.c9d0f-range` |
| job__tag_swap | job_title | tag_swap | YES | healed | ok | `css=section.posting h2.posting-title` |
| job__tag_swap | company | tag_swap | YES | healed | ok | `css=section.company-line .company-name` |
| job__wrapper_insert | company | wrapper_insert | YES | healed | ok | `css=div.company-line .company-name` |
| product__attr_strip | title | attr_strip | YES | healed | ok | `css=h1.product-title` |
| product__attr_strip | price | attr_strip | YES | healed | ok | `css=span.price-value` |
| product__class_rename | title | class_rename | YES | healed | ok | `css=.c7425-title` |
| product__class_rename | price | class_rename | YES | healed | ok | `css=.cb8af-value` |
| product__class_rename | rating | class_rename | YES | healed | ok | `css=.c48b1-value` |
| product__combo | title | combo | YES | healed | ok | `css=h2.c7425-title` |
| product__combo | price | combo | WRONG | suspect | ok | `css=div.c0929-price` |
| product__combo | rating | combo | YES | healed | ok | `css=div.c48b1-value` |
| product__tag_swap | title | tag_swap | YES | healed | ok | `css=h2.product-title` |
| product__tag_swap | price | tag_swap | YES | healed | ok | `css=.price-value[data-price-amount]` |
| product__tag_swap | rating | tag_swap | YES | healed | ok | `css=.rating-value` |
| product__wrapper_insert | rating | wrapper_insert | YES | healed | ok | `css=.rating-block > .layout-slot > span.rating-value` |
