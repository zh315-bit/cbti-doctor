# Step 9.23 Diary Semantic Status

只有契约投影有效时才建立日期/字段状态。逐条记录带日期、`record_status=PRESENT`，每个字段独立标记 `RECORD_PRESENT_FIELD_MISSING`、`RECORD_PRESENT_FIELD_VALID` 或 `RECORD_PRESENT_FIELD_INVALID`。有效且来源条数为零，才可标记整体 `RECORD_ABSENT`；未证明覆盖的日期不能擅自标记为不存在。投影 `unavailable` 映射 `RESOURCE_UNAVAILABLE`，`invalid` 映射 `INVALID`，两者都不证明“没有日记”。

Final Claim Guard 对能识别的日期特定“无记录”、有记录时的全局“没有记录”、资源不可用时的“没有日记”，以及 State 未支持的直接第二人称用户事实断言进行删除。若全句被删除，返回保守说明。字段缺失/无效可在回答中如实说明，但不得换成整条记录缺失。守卫是确定性、保守的冲突检测，不是完整中文语义解析器。
