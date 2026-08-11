---
tags: []
---

## 稼働中のコンサル案件

```dataview
TABLE client, status, last-updated
FROM "01_projects/consulting"
WHERE status = "active"
SORT last-updated DESC
```

## 最近のインサイト

```dataview
TABLE topic, last-updated
FROM "03_resources/insights"
SORT last-updated DESC
LIMIT 10
```

## ショートカット
- [[00_inbox]]
- [[03_resources/insights]]
- [[04_archives/consulting]]
