<%*
const domain = await tp.system.suggester(["consulting", "venture"], ["consulting", "venture"])
let client = ""
if (domain === "consulting") {
  const clients = app.vault.getMarkdownFiles()
    .map(f => app.metadataCache.getFileCache(f)?.frontmatter?.client)
    .filter(c => c)
  const uniqueClients = [...new Set(clients)]
  client = await tp.system.suggester(
    [...uniqueClients, "+ 新規クライアント"],
    [...uniqueClients, ""]
  )
}
-%>
---
domain: <% domain %>
client: <% client %>
project:
status: active
started: <% tp.date.now("YYYY-MM-DD") %>
last-updated: <% tp.date.now("YYYY-MM-DD") %>
tags: []
---

## 概要

## 現在のステータス

## 次のアクション
- [ ]

## 関連リンク
-
