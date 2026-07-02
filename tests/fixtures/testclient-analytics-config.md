# Test Client — Analytics Config (schema 1.0)

> Synthetic config used only by the pytest harness. Not a real client. Kept minimal but
> structurally valid: an Identity yaml block and §6 metric lines, parsed by `parse_config`.

## 1. Identity

```yaml
client_name: Test Client
client_slug: testclient
brand_accent_hex: 2A4A44
output_filename: TestClient_[MonthYear]_Performance.xlsx
platforms_active: [instagram, facebook, youtube]
```

## 6. Metrics to score

**Instagram (score these):** Likes, Saves, Reach
**Facebook (score these):** Reactions, Total clicks
**YouTube Shorts (score these):** Views, Watch time (hours), Subscribers
**YouTube Long-form (score these):** Views, Watch time (hours), Subscribers
