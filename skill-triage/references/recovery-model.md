# Recovery Model

Version 1 stores original snapshots but does not apply changes. Use 恢复, 回退, and 找回原始版本 in user-facing text. If backup is off, clearly say recovery from this run is limited.

## Manual Recovery Text

When backup is targeted or full, name the snapshot path and original hash. When backup is off, say: "这次没有保存原始快照；如果你手动采用了草案，恢复需要依赖你自己的 git、备份或原始来源。"
